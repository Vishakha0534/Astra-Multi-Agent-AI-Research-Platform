from typing import List, Optional
from .models import ReliabilityReport, EvidenceNode, Contradiction, HallucinationAnalysis
from .credibility import SourceCredibilityAnalyzer
from .confidence_score import ConfidenceScoreEngine
from .contradiction import ContradictionDetector
from .hallucination import HallucinationDetector
from .evidence_graph import EvidenceGraphBuilder

class TrustScoreEngine:
    def __init__(self):
        self.credibility_analyzer = SourceCredibilityAnalyzer()
        self.confidence_engine = ConfidenceScoreEngine()
        self.contradiction_detector = ContradictionDetector()
        self.hallucination_detector = HallucinationDetector()
        self.graph_builder = EvidenceGraphBuilder()

    async def evaluate_response(
        self, 
        response_text: str, 
        claims: List[str], 
        citations: List[dict],
        facts: List[str],
        logprobs: Optional[List[float]] = None
    ) -> ReliabilityReport:
        """
        Main entry point to evaluate an AI response.
        """
        # 1. Build Evidence Graph
        evidence_nodes = await self.graph_builder.build(citations)
        
        # 2. Detect Contradictions
        contradiction_result = await self.contradiction_detector.detect(claims, facts)
        
        # 3. Analyze Hallucinations
        # Simple support mapping: a claim is supported if its corresponding citation has high relevance
        supports = [cite.get("relevance", 0.0) > 0.7 for cite in citations]
        hallucination_result = await self.hallucination_detector.analyze(claims, supports)
        
        # 4. Calculate Confidence
        semantic_variance = 0.2 if contradiction_result.is_contradictory else 0.0
        confidence = await self.confidence_engine.calculate(logprobs, semantic_variance)
        
        # 5. Calculate Final Trust Score
        # Trust = Weighted(Credibility of sources + Confidence - Penalties)
        avg_credibility = sum(node.credibility_score for node in evidence_nodes) / max(len(evidence_nodes), 1)
        base_trust = (avg_credibility * 0.4) + (confidence * 0.6)
        
        penalty = 0.0
        if contradiction_result.is_contradictory:
            penalty += 0.3
        if hallucination_result.is_hallucination:
            penalty += 0.2
            
        trust_score = max(base_trust - penalty, 0.0)
        
        return ReliabilityReport(
            trust_score=round(trust_score, 2),
            confidence_score=round(confidence, 2),
            evidence_sources=evidence_nodes,
            contradiction_analysis=contradiction_result,
            hallucination_analysis=hallucination_result,
            metadata={"response_length": len(response_text)}
        )

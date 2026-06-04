from .models import HallucinationAnalysis
from typing import List

class HallucinationDetector:
    async def analyze(self, claims: List[str], evidence_supports: List[bool]) -> HallucinationAnalysis:
        """
        Analyzes if claims are likely to be hallucinations based on evidence overlap.
        """
        unverifiable = []
        for claim, supported in zip(claims, evidence_supports):
            if not supported:
                unverifiable.append(claim)
                
        is_hallucination = len(unverifiable) > 0
        reasoning = (
            f"Found {len(unverifiable)} claims without direct attribution to evidence."
            if is_hallucination else "All claims are supported by provided evidence nodes."
        )
        
        return HallucinationAnalysis(
            is_hallucination=is_hallucination,
            unverifiable_claims=unverifiable,
            reasoning=reasoning
        )

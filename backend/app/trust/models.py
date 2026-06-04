from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class EvidenceNode(BaseModel):
    id: str
    claim: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_type: str  # 'peer_reviewed', 'news', 'blog', 'social_media', 'official_doc'
    credibility_score: float = Field(..., ge=0.0, le=1.0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)

class Contradiction(BaseModel):
    is_contradictory: bool
    description: Optional[str] = None
    conflicting_claims: List[str] = []

class HallucinationAnalysis(BaseModel):
    is_hallucination: bool
    unverifiable_claims: List[str] = []
    reasoning: str

class ReliabilityReport(BaseModel):
    trust_score: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_sources: List[EvidenceNode]
    contradiction_analysis: Contradiction
    hallucination_analysis: HallucinationAnalysis
    metadata: Dict = {}

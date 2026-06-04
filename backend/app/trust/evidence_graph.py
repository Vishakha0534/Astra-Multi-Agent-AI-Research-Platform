from .models import EvidenceNode
from typing import List

class EvidenceGraphBuilder:
    def __init__(self):
        self.nodes: List[EvidenceNode] = []
        
    async def build(self, citations: List[dict]) -> List[EvidenceNode]:
        """
        Builds a structured list of evidence nodes from raw citations.
        """
        for i, cite in enumerate(citations):
            node = EvidenceNode(
                id=f"EV-{i}",
                claim=cite.get("claim", ""),
                source_url=cite.get("url"),
                source_title=cite.get("title"),
                source_type=cite.get("type", "official_doc"),
                credibility_score=cite.get("credibility", 0.8),
                relevance_score=cite.get("relevance", 0.9)
            )
            self.nodes.append(node)
            
        return self.nodes

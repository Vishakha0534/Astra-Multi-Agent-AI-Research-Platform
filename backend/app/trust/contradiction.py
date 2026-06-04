from .models import Contradiction
from typing import List

class ContradictionDetector:
    async def detect(self, claims: List[str], referenced_facts: List[str]) -> Contradiction:
        """
        Detects contradictions between generated claims and retrieved facts.
        """
        conflicting = []
        # Simplified string-based negation detection for demonstration
        # In a real scenario, this would use a cross-encoder model (NLI)
        for claim in claims:
            for fact in referenced_facts:
                # Mock logic: find keywords that indicate disagreement
                if any(word in claim.lower() and word in fact.lower() for word in ["not", "never", "unlike"]):
                    # If common entities are mentioned but with negation keywords...
                    conflicting.append(f"Claim: {claim} | Fact: {fact}")
        
        return Contradiction(
            is_contradictory=len(conflicting) > 0,
            description=f"Found {len(conflicting)} potential contradictions." if conflicting else "No contradictions found.",
            conflicting_claims=conflicting
        )

from typing import List, Optional
import numpy as np

class ConfidenceScoreEngine:
    async def calculate(self, logprobs: Optional[List[float]] = None, semantic_variance: float = 0.0) -> float:
        """
        Calculates confidence based on model output probabilities and cross-agent consistency.
        """
        if logprobs:
            # Basic average of probabilities from logprobs
            avg_prob = np.exp(np.mean(logprobs))
        else:
            avg_prob = 0.85  # Assumption for high-quality models if no logprobs
            
        # Penalize confidence based on semantic variance (contradictions between agents)
        score = avg_prob * (1 - semantic_variance)
        return float(np.clip(score, 0.0, 1.0))

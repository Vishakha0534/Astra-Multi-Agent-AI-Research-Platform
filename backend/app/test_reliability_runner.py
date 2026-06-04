import asyncio
from trust import TrustScoreEngine

async def main():
    engine = TrustScoreEngine()
    
    # Mock data
    response = "The sky is green according to science."
    claims = ["The sky is green"]
    citations = [
        {"claim": "The sky is green", "url": "http://fake-blog.com/post", "title": "My Green Sky Blog", "type": "blog", "credibility": 0.3, "relevance": 0.4}
    ]
    facts = ["The sky is actually blue."]
    
    report = await engine.evaluate_response(response, claims, citations, facts)
    
    print("--- Reliability Report ---")
    print(f"Trust Score: {report.trust_score}")
    print(f"Confidence Score: {report.confidence_score}")
    print(f"Contradiction Found: {report.contradiction_analysis.is_contradictory}")
    print(f"Hallucination Found: {report.hallucination_analysis.is_hallucination}")
    print(f"Evidence Source: {report.evidence_sources[0].source_title}")

if __name__ == "__main__":
    asyncio.run(main())

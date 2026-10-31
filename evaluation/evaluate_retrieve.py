
import json
from pathlib import Path

from retrieve import search_knowledge


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_FILE = PROJECT_ROOT / "data" / "evaluation.json"


def evaluate_retrieval(top_k: int = 3):
    with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
        test_cases = json.load(file)

    hits = 0
    reciprocal_ranks = []
    total = len(test_cases)

    for case in test_cases:
        question = case["question"]
        expected_source = case["expected_source"]

        results = search_knowledge(question, top_k=top_k)

        expected_fact = case["expected_fact"]

        # Tìm thứ hạng đầu tiên có source đúng.
        matching_ranks = [
            rank
            for rank, result in enumerate(results, start=1)
            if result["source"] == expected_source
        ]

        hit = len(matching_ranks) > 0
        if hit:
            hits += 1
            reciprocal_ranks.append(1 / matching_ranks[0])
        else:
            reciprocal_ranks.append(0)

        print(f"\nQuestion: {question}")
        print(f"Expected source: {expected_source}")
        print(f"Hit@{top_k}: {hit}")

        for rank, result in enumerate(results, start=1):
            print(
                f"  {rank}. {result['source']} "
                f"(distance={result['distance']:.4f})"
            )
            print(f"     Content: {result['text'][:250]}...")

    hit_rate = hits / total if total else 0
    mrr = sum(reciprocal_ranks) / total if total else 0

    print("\n========== EVALUATION SUMMARY ==========")
    print(f"Total questions: {total}")
    print(f"Hit@{top_k}: {hit_rate:.2%} ({hits}/{total})")
    print(f"MRR@{top_k}: {mrr:.4f}")


if __name__ == "__main__":
    evaluate_retrieval(top_k=3)

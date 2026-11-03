
import json
from pathlib import Path

from app.rag.retriever import search_knowledge


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_FILE = PROJECT_ROOT / "data" / "evaluation.json"


def evaluate_retrieval(top_k: int = 3):
    with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
        test_cases = json.load(file)

    chunk_hits = 0
    source_hits = 0
    reciprocal_ranks = []
    category_results = {}
    answerable_cases = [case for case in test_cases if case.get("expected_chunk")]

    for case in test_cases:
        question = case["question"]
        expected_source = case["expected_source"]
        expected_chunks = case.get("expected_chunks") or (
            [case["expected_chunk"]] if case.get("expected_chunk") else []
        )
        expected_chunk = expected_chunks[0] if expected_chunks else None
        category = case.get("category", "uncategorized")

        results = search_knowledge(question, top_k=top_k)

        # Tìm thứ hạng đầu tiên có source đúng.
        matching_ranks = [
            rank
            for rank, result in enumerate(results, start=1)
            if result["source"] == expected_source
        ]

        chunk_rank = next(
            (rank for rank, result in enumerate(results, start=1)
             if result["id"] == expected_chunk),
            None,
        )
        source_hit = bool(matching_ranks)
        chunk_hits_for_case = sum(
            result["id"] in expected_chunks
            for result in results
        )
        chunk_hit = bool(expected_chunks) and chunk_hits_for_case == len(expected_chunks)
        source_hits += int(source_hit)
        chunk_hits += int(chunk_hit)
        reciprocal_ranks.append(1 / chunk_rank if chunk_rank else 0)

        category_results.setdefault(category, {"total": 0, "hits": 0})
        if expected_chunk:
            category_results[category]["total"] += 1
            category_results[category]["hits"] += int(chunk_hit)

        print(f"\nQuestion: {question}")
        print(f"Expected source: {expected_source}")
        print(f"Expected chunk: {expected_chunk or 'N/A (abstention)'}")
        print(f"Source hit@{top_k}: {source_hit}")
        print(f"Chunk hit@{top_k}: {chunk_hit}")

        for rank, result in enumerate(results, start=1):
            print(
                f"  {rank}. {result['source']} "
                f"(distance={result['distance']:.4f})"
            )
            print(f"     Content: {result['text'][:250]}...")

    answerable_count = len(answerable_cases)
    recall = chunk_hits / answerable_count if answerable_count else 0
    source_recall = source_hits / answerable_count if answerable_count else 0
    mrr = sum(reciprocal_ranks) / answerable_count if answerable_count else 0

    print("\n========== EVALUATION SUMMARY ==========")
    print(f"Total questions: {len(test_cases)}")
    print(f"Answerable questions: {answerable_count}")
    print(f"Recall@{top_k} by chunk: {recall:.2%} ({chunk_hits}/{answerable_count})")
    print(f"Recall@{top_k} by source: {source_recall:.2%} ({source_hits}/{answerable_count})")
    print(f"MRR@{top_k}: {mrr:.4f}")
    print("\nCategory recall:")
    for category, result in category_results.items():
        rate = result["hits"] / result["total"] if result["total"] else 0
        print(f"- {category}: {rate:.2%} ({result['hits']}/{result['total']})")


if __name__ == "__main__":
    evaluate_retrieval(top_k=3)

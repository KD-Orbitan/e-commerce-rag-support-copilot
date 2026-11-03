import json
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_FILE = PROJECT_ROOT / "data" / "evaluation.json"
OUTPUT_FILE = PROJECT_ROOT / "evaluation" / "results" / "live_chat.json"
API_URL = "http://127.0.0.1:8000/chat"


def run_live_evaluation() -> None:
    with EVALUATION_FILE.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    results = []
    for index, case in enumerate(cases, start=1):
        response = requests.post(
            API_URL,
            json={"question": case["question"], "top_k": 3},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        results.append({
            "index": index,
            "question": case["question"],
            "expected_fact": case["expected_fact"],
            "category": case["category"],
            "expected_chunks": case.get("expected_chunks")
            or ([case["expected_chunk"]] if case.get("expected_chunk") else []),
            "answer": payload["answer"],
            "sources": payload["sources"],
            "abstained": payload["abstained"],
        })
        print(f"{index:02d}/30 completed")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print(f"Saved live results to {OUTPUT_FILE}")


if __name__ == "__main__":
    run_live_evaluation()

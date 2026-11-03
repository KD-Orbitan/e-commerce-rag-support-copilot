# Day 3 Evaluation Summary

## Dataset

- Total cases: 30
- Answerable cases: 20
- Abstention/out-of-scope cases: 10
- Answerable distribution:
  - Direct: 10
  - Multi-hop: 5
  - Paraphrase: 5

## Baseline and experiment

The controlled experiment changed only `top_k`, keeping the embedding model,
documents, chunking, and collection unchanged.

| Configuration | Recall@k by chunk | Recall@k by source | MRR@k |
|---|---:|---:|---:|
| Baseline, top_k=3 | 100% (20/20) | 100% (20/20) | 0.8167 |
| Experiment, top_k=5 | 100% (20/20) | 100% (20/20) | 0.8167 |

Recall@k by chunk is the primary retrieval metric. Source-level recall is
reported separately to distinguish a correct document from a correct chunk.

## Answerable recall by category

| Category | top_k=3 | top_k=5 |
|---|---:|---:|
| Direct | 100% (10/10) | 100% (10/10) |
| Multi-hop | 100% (5/5) | 100% (5/5) |
| Paraphrase | 100% (5/5) | 100% (5/5) |

## Manual answer quality rubric

For every generated answer, score each criterion as 0 or 1:

- **Correctness:** All factual claims match the expected fact.
- **Groundedness:** Every factual claim is supported by the retrieved context.
- **Citation accuracy:** Cited sources support the answer content.
- **Abstention:** The answer declines when an answerable fact is absent.

Manual live output và API structure đã được ghi vào `live_evaluation.md`.
Case 13 và case 30 sai ở bản đầu đã được rerun sau khi sửa pipeline.

## Observed error risks

1. `Bitcoin` paraphrases can retrieve the FAQ chunk even when the answer should
   distinguish the unsupported payment method from the store payment policy.
2. The multi-hop shipping example can retrieve both shipping fee chunks; the
   answer may need two facts and can be incomplete if only one chunk is used.
3. Out-of-scope order-status questions can still retrieve `shipping_004` or
   `faq_005`, so retrieval relevance alone does not guarantee safe abstention.

## Conclusion

Increasing `top_k` from 3 to 5 did not improve Recall@k or MRR@k in this
dataset. For this small collection, the baseline configuration is preferable
because it returns less context and avoids unrelated chunks without reducing
retrieval quality. This result should be treated as a retrieval-only finding.

## Dataset limitations

- The evaluation contains 30 cases but only 20 answerable facts.
- Product coverage represents 10 products and policy coverage represents five
  Markdown files.
- Live rerun đã ghi chính xác API `abstained`; câu trả lời thủ công vẫn nên
  được đối chiếu lại khi thay đổi model hoặc prompt.
- Results were produced with the current OpenAI embedding configuration, so
  future model or data changes require rerunning the same dataset.

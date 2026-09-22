# Cost, accuracy, and review workload

## Decision

Use local embeddings for category classification, send uncertain tickets to human review, and use Claude only as an optional urgency second opinion. Automatic Claude replacement increased category errors in the flagged queues. This decision is supported by the measured validation results; it is not a claim that local compute is free or that LLMs are universally worse.

## Matched category comparison

The second pilot used the same 30 requests for all four methods. Do not present this small sample as a production benchmark or compare its percentages against full-validation results without their denominators.

| Model / prompt | Correct / same 30 requests | Accuracy | API token cost for the 30 | Projected API cost / 1,000 similar requests | Mean request latency |
| --- | ---: | ---: | ---: | ---: | --- |
| TF-IDF + logistic regression | 30/30 | 100.00% | $0 external API | $0 external API | Not measured comparably |
| MiniLM + five nearest neighbors | 30/30 | 100.00% | $0 external API | $0 external API | Not measured comparably |
| Claude Haiku 4.5 v1 | 27/30 | 90.00% | $0.006766 estimated | $0.2255 estimated | 0.78 seconds |
| Claude Haiku 4.5 v2 | 26/30 | 86.67% | $0.013071 estimated | $0.4357 estimated | 0.68 seconds |

Zero external API cost excludes CPU, RAM, model storage, setup and maintenance. Claude latency includes gateway/network effects; timing was not controlled or randomized. The v2 prompt did not demonstrate an accuracy or reliable latency advantage. Both v1 pilots combined scored 54/60, but v2 was tested on only the second pilot.

## Pricing assumptions and reproducible calculation

Anthropic's published Claude Haiku 4.5 standard rates, checked 21 September 2026: **$1 per million input tokens and $5 per million output tokens**. Source: [Anthropic Haiku pricing](https://www.anthropic.com/claude/haiku).

Estimated request-batch cost = (input tokens × input rate + output tokens × output rate) / 1,000,000.

Second category pilot: v1 used 6,046 input and 144 output tokens; v2 used 12,346 and 145. Projected per-1,000 cost scales the observed average token lengths, not accuracy. No discount for prompt caching or batch processing, no retry charge, no gateway markup, no tax, and no university-specific subsidy is modeled. Actual Portkey billing is unverified. These are list-price estimates, not charges or savings demonstrated by this project.

Run `python scripts/calculate_costs.py` to regenerate `analysis/cost_comparison.csv`. Override rates with `--input-per-million` and `--output-per-million` when pricing changes. No API is called.

## Full validation: would automatic replacement help?

| Local classifier | Standalone errors / 3,641 | Reviewed by Claude | Errors corrected | New errors introduced | Errors after automatic replacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Embeddings | 4 | 154 | 2 | 9 | 11 |
| TF-IDF | 9 | 154 | 8 | 11 | 12 |

The queues overlap on 54 tickets; their union is 254. This is a targeted fallback experiment, not a standalone-LLM random test. Exact fallback token totals are not available in the retained summaries, so the report does not multiply pilot token costs into a claimed measured queue cost. The deployed category review process is human-led; these automatic replacements were simulated offline.

## Urgency prompt tradeoff

Both prompts correctly classified all 12 round-two policy scenarios, including three Critical cases. V1 consumed 3,781 input and 1,061 output tokens, for an estimated $0.009086 batch cost. V2 consumed 6,229 and 1,028, for $0.011369. Equivalent per-1,000 projections are $0.7572 and $0.9474, respectively. Twelve targeted examples are insufficient to establish safe automatic urgency decisions.

## Human review belongs in the cost model

On the held-out embedding test, 160/3,642 tickets required review (4.39%); five errors were captured and 155 already-correct predictions also required review. This is 32 reviewed tickets per captured error in that test. It does not mean each future group of 32 reviews will catch an error.

Illustrative assumptions, not measured: one minute per review and $30 per reviewer-hour. At the observed review rate, review labor would be about **$21.97 per 1,000 submitted tickets** (1,000 × 160/3,642 × 1/60 × $30). This covers category review only; it excludes human urgency assessment, fixed overhead, and consequences of mistakes. A fully manual one-minute category triage process would cost $500 per 1,000 under the same hypothetical assumptions, but the project has not established that baseline or a realized saving.

The comparison suggests measuring reviewer time and routing mistakes before optimizing pennies of API cost. Measure local latency and CPU/memory use on the same tickets before claiming a complete cost/performance advantage.

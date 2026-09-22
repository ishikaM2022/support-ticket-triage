# Evaluation report

Evidence: uploaded development notebook and recovered cache summaries, plus the user's final held-out test output on 21 September 2026. The final test was run in the user's environment; it was not independently rerun during documentation. Figures below describe specific evaluation populations.

## Data preparation

The inspected Bitext v11 file has 26,872 rows and five fields: flags, instruction, category, intent, response. No missing fields were observed. It contains 27 intents and 11 categories. There were 2,237 exact repeated instructions and 2,598 repeated instructions after normalizing case and whitespace. No category/intent conflicts were found within normalized duplicate groups.

After normalized deduplication, 24,274 requests were split using random_state=42 and intent stratification: 70% training, then equal validation/test halves of the remaining 30%. Counts: 16,991 / 3,641 / 3,642. Only instruction text is a model input; supplied responses and flags are excluded. Normalized text is used for duplicate detection, while original text is classified.

Near-duplicate paraphrases and generated templates were not fully grouped across splits. For example, an address-edit validation error had a nearly identical correctly labeled training neighbor. High scores must be interpreted with this limitation.

## Category models

- TF-IDF: word unigrams/bigrams, min_df=2, sublinear_tf=True, logistic regression with max_iter=1000 and random_state=42.
- Embeddings: all-MiniLM-L6-v2, normalized vectors, five cosine nearest neighbors, uniform voting.
- LLM: Claude Haiku 4.5 via Portkey; category names and definitions supplied in a prompt, temperature=0. V2 added policy clarifications and examples derived during development.

### Full validation: local models and simulated replacement

| Approach | Errors / 3,641 | Accuracy |
| --- | ---: | ---: |
| Embeddings alone | 4 | 99.89% |
| TF-IDF alone | 9 | 99.75% |
| Embeddings with Claude replacement on flagged tickets | 11 | 99.70% |
| TF-IDF with Claude replacement on flagged tickets | 12 | 99.67% |

Embedding validation macro-F1: 0.9989. TF-IDF validation macro-F1: 0.9979.

| Flagged subset | Tickets | Original errors captured | Claude correct | Errors corrected | New errors introduced |
| --- | ---: | ---: | ---: | ---: | ---: |
| Embedding threshold queue | 154 | 4 | 143 | 2 | 9 |
| Lowest TF-IDF top probabilities | 154 | 9 | 142 | 8 | 11 |

Both local models had zero original errors outside their respective queues on validation. The queues overlap on 54 tickets; their union is 254. TF-IDF's bottom-154 selection is an offline equal-workload comparison, not a calibrated deployment threshold. All 154 Claude responses in each subset were valid category labels.

Replacement was a simulation: operationally, tickets still require human review. Net errors increased by seven for embeddings and three for TF-IDF. The experiment supports retaining local predictions with human review rather than automatically replacing uncertain predictions with Claude.

### Standalone LLM pilots: matched samples

| Model | First 30 | Fresh second 30 | Combined where applicable |
| --- | ---: | ---: | ---: |
| TF-IDF | 30/30 | 30/30 | 60/60 |
| Embeddings | 30/30 | 30/30 | 60/60 |
| Claude v1 | 27/30 | 27/30 | 54/60 |
| Claude v2 | Not tested | 26/30 | 26/30 |

Do not compare 90% on 60 samples directly against full-validation percentages as if the denominators matched. V2 was developed after first-pilot inspection, then evaluated on the second sample. Both category pilots had valid labels on every response.

The dataset convention between ORDER tracking/ETA and DELIVERY arrival time is ambiguous. Requests about “withdrawal charges” and “earning an article” also allow interpretations different from their dataset labels. These count as dataset-label mismatches, with the ambiguity documented rather than retrospectively relabeled.

### Token usage and latency

| Experiment | Input tokens | Output tokens | Reported mean latency |
| --- | ---: | ---: | ---: |
| First 30, Claude v1 | 6,043 | 146 | Not retained in shared summary |
| Second 30, Claude v1 | 6,046 | 144 | 0.78 s |
| Second 30, Claude v2 | 12,346 | 145 | 0.68 s |

These timings were not randomized or controlled for gateway caching/network conditions. The shorter v2 timing does not establish a speed advantage. Local inference latency was not measured with the same protocol. Local models incur compute costs even though they do not use per-request API tokens. Exact dollar charges remain unverified; no financial savings are claimed. Published-rate estimates and matched accuracy comparisons are now included in [COST_COMPARISON.md](COST_COMPARISON.md).

## Final held-out category test

Artifact reported by user: `experiment_exports/test_20260921T175207760564Z/category_test_summary.json`. Model and acceptance thresholds remained fixed after validation selection.

| Metric | Result |
| --- | ---: |
| Test requests | 3,642 |
| Accuracy | 0.9986271279516749 (99.86%) |
| Macro-F1 | 0.9986518270216387 |
| Total category errors | 5 |
| Requests sent to review | 160 (4.3932%) |
| Automatically accepted | 3,482 (95.6068%) |
| Errors sent to review | 5 |
| Errors accepted automatically | 0 observed |
| Accuracy among accepted requests | 100% observed |
| Minimum similarity / agreement | 0.80 / 0.80 |

Of the 160 reviews, 155 involved predictions already matching the labels. Human review cost must therefore be weighed against catching the five errors. No post-review human accuracy was measured. This final test covers embeddings and its review rule, not standalone Claude, TF-IDF, or urgency. Do not retune based on the test errors and continue calling this an untouched benchmark.

## Urgency experiments

The Bitext dataset has no urgency ground truth. Separate fictional cases were labeled against the project's policy before requests were sent; only ticket text went to the model.

| Development experiment | Correct | Critical flagged | False Critical | Invalid after parsing |
| --- | ---: | ---: | ---: | ---: |
| Round 1, v1 | 9/12 | 3/3 | 1 | 0 |
| Fresh targeted round 2, v1 | 12/12 | 3/3 | 0 | 0 |
| Fresh targeted round 2, v2 | 12/12 | 3/3 | 0 | 0 |

Round one initially had 12 strict-JSON parsing failures because responses included Markdown fences. Saved responses were reparsed without paid calls. This was a parser change, not model improvement. Round-one errors were one High-to-Critical escalation and two Medium-to-Low assignments for functional issues with workarounds.

Round-two v1 used 3,781 input and 1,061 output tokens; v2 used 6,229 input and 1,028 output tokens. V2 used about 65% more input tokens with no observed accuracy gain. V1 remained the provisional baseline. These targeted development cases cannot establish broad safety or robustness; urgency still requires human confirmation.

## Persistence and reproducibility

Recovered caches contain 254 category responses and 24 round-two urgency responses. They were matched to original validation ticket text and saved scenario labels. Recovered hybrid counts matched the prior results. Some pilot and first-round urgency records existed only in memory; retained notebook outputs support their summaries but do not recreate every raw response.

The safe notebook loads results by default and preserves historical code/output in an inert appendix. Experimental reruns are isolated and explicit. The final category-test function was added locally; leave its call commented after running it.

## What remains unproven

Real-world classification accuracy, calibrated urgency confidence, reviewer effectiveness, business-time savings, reduced escalations, total operating costs, multi-user reliability, and predictive resolution times have not been established. Future independent evaluation should include template-separated or real tickets, ambiguous/multiple issues, out-of-scope inputs, and adversarial instructions.

## Subsequent packaging verification

The builder reported successful Docker startup and confirmed a test ticket persisted through container removal/recreation. Documentation preparation did not rerun the full application or held-out model test. The read-only operations exporter was checked on a temporary fixture for event grouping, duration calculations, historical urgency and invalid-date exclusion; it still needs to be run on the builder's private database.

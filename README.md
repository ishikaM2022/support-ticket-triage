# Support Ticket Triage
https://support-ticket-triage-ds2y.onrender.com/

## 1. Problem and user

Support agents need to route routine requests quickly while inspecting ambiguous tickets and recognizing urgent impact. Support leads also need to see whether a routed ticket has received a response or been resolved. This local portfolio prototype brings those decisions into one auditable workflow.

The business hypothesis is less hands-on triage effort without more harmful mistakes. No real-team productivity improvement has yet been measured. The [PRD](docs/PRD.md) defines proposed discovery, success criteria, guardrails and a pilot plan.

## 2. Architecture and key technical decision

The app uses local MiniLM embeddings with five-neighbor category classification, a human review queue, SQLite persistence, and optional Claude Haiku 4.5 urgency advice through Portkey. A reviewer confirms final urgency. Docker packages the app; a host-mounted database retains tickets through container recreation.

**Key decision:** do not automatically replace uncertain category predictions with Claude. On 3,641 validation requests, simulated Claude replacement increased embedding errors from **4 to 11**, correcting two but introducing nine. Human review remains the fallback. Similarity and vote agreement are uncertainty signals, not calibrated correctness probabilities.

### Components

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit interface |
| `classifier.py` | Local all-MiniLM-L6-v2 embeddings, cosine five-neighbor voting, review thresholds |
| `database.py` | SQLite persistence, routing, human decisions, audit events, recovery, SLA and resolution logic |
| `urgency.py` | Portkey call to Claude Haiku 4.5 and response validation |
| `artifacts/` | Saved embedding model, fitted classifier, training labels, routing configuration, urgency prompt |
| `triage.db` / `data/triage.db` | Local / Docker ticket records and review-event history |
| `01_data_audit_and_baseline_safe.ipynb` | Saved-result viewer and explicitly invoked experiment reruns |

Submission commits a pending ticket first. Classification then updates it. A failed classification leaves a recoverable pending record. Recovery is invoked manually from the dashboard; there is no background worker or RabbitMQ service. Related ticket updates and audit events are committed in a database transaction.

## 3. Measured insight

On **3,642 held-out synthetic requests**, embeddings achieved **99.86% category accuracy and 0.9987 macro-F1**. Fixed review thresholds captured all five observed errors while sending **160 tickets (4.39%)** to review. The other 3,482 requests contained no observed errors; this is a sample outcome, not a production guarantee. Of reviewed predictions, 155 were already correct, making review workload part of the tradeoff.

On the same second 30-ticket pilot, local models each scored 30/30, Claude v1 scored 27/30, and v2 scored 26/30. Published-rate API estimates are about **$0.23 versus $0.44 per 1,000 similarly sized category requests** for v1/v2. These are token-based projections, not university invoices or total operating cost. Local CPU and reviewer labor are not free. See [cost and accuracy](docs/COST_COMPARISON.md).

A separate audit of the uploaded 8,469-ticket support sample found **49.3% of closed tickets had resolution timestamps before first response**, and no ticket-created field existed. The analyst decision was to withhold misleading resolution-time and arrival-trend claims and request corrected event data. [Case study and chart guide](docs/ANALYST_CASE_STUDY.md).

## 4. Failure and fix

Urgency evaluation initially marked every response invalid: Claude wrapped valid JSON in Markdown fences. Inspection of saved raw responses identified a parser mismatch. The parser now accepts a complete outer fence while keeping schema and field-consistency checks. Reprocessing saved outputs avoided repeat API calls. This fixed parsing, not classification accuracy: first-round policy accuracy remained 9/12.

A separate failure was that additional prompt detail and automatic LLM corrections did not consistently improve category accuracy. We retained the simpler baseline and explicit human control rather than hiding the negative result. See [evaluation evidence](docs/EVALUATION.md) for matched populations and limitations.

## App screens

| Screen | Purpose |
| --- | --- |
| Submit ticket | Persist a request before classification; route its category or flag it for review |
| Human review | Correct or confirm categories while retaining the original prediction |
| Urgency assessment | Assign urgency, defer for information, or request an optional Claude suggestion |
| Response SLAs | Display first-response deadlines and record a response already sent |
| Resolution | Record issue resolution and elapsed calendar hours |
| Dashboard | Show ticket volume, categories, open backlog, response SLA outcomes, and observed resolution time |

No email is sent by these actions. A routed ticket is not necessarily resolved. Dashboard records are demo activity, not evidence of improved business performance.

## Run with Docker

From the project root, with Docker Desktop running in Linux-container mode:

```powershell
docker compose up --build -d
```

Open http://localhost:8501. Docker Desktop must be running in Linux-container mode. The database mount is `data/triage.db`; local execution defaults to the separate root `triage.db` unless `TRIAGE_DB_PATH` is set. The builder verified a newly submitted ticket survived `docker compose down` followed by `docker compose up -d`. See [Docker instructions](DOCKER.md) for first-time database migration.

## Reproduce reports without API calls

These scripts use only Python's standard library and do not change the app database:

```powershell
.\.venv\Scripts\python.exe scripts/calculate_costs.py
.\.venv\Scripts\python.exe scripts/analyze_public_sample.py --input customer_support_tickets.csv
.\.venv\Scripts\python.exe scripts/export_operations.py --db data/triage.db
```

Open `analysis/public_sample/report.html` for the included audit. After the last command, open `analysis/operations/report.html` for your own recorded activity. Aggregate CSVs support Power BI/Tableau import; no Power BI/Tableau workbook is claimed as built. Current app activity includes demo tickets, so these charts cannot demonstrate real business improvements. No resolution forecast is implemented.

## Run locally on Windows

The working project uses a Python 3.11 virtual environment. From the project directory:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.fileWatcherType none
```

Open the local URL printed in the terminal. File watching is disabled to avoid optional Transformers image-module imports triggered by Streamlit's watcher. Restart the server after source changes.

The app requires your existing artifacts:

- `artifacts/embedding_model/`
- `artifacts/knn.joblib`
- `artifacts/train_categories.npy`
- `artifacts/config.json`
- `artifacts/urgency_prompt_v1.txt`

The runtime uses Streamlit, pandas, NumPy, scikit-learn, sentence-transformers, PyTorch, joblib, and portkey-ai. SQLite is included with Python. The supplied requirements-local.txt records the local environment; requirements-docker.txt pins selected runtime packages. The user successfully built and ran the Docker image, but it is not a complete transitive Linux lockfile or an independently repeated clean-install benchmark. Only load trusted joblib artifacts, using compatible dependency versions.

No API key is needed for local category classification, manual review, or operational tracking. For an AI urgency suggestion, enter the Portkey key in the app's password field. The current provider configuration is course-specific (`@30800-fall26-anthropic`) and must be replaced for another deployment. Use course access within its permitted scope. The application does not persist the key to ticket records; valid AI suggestions do store request-derived explanations, raw responses, prompt text, and token counts.

## Notebook usage

Normal **Run All** in the safe notebook loads saved exports and caches without model training, paid calls, or database writes. Keep `experiment_exports/`, `claude_v1_review_cache.json`, and `urgency_round2_cache.json` beside it. Historical cells are an inert appendix.

If you added `evaluate_category_test()` locally, leave its invocation commented after the final test. Do not retune against the held-out results. Optional experiment reruns require explicit calls; paid runs also require opt-in and a request budget.

## Data and interpretation

The supplied Bitext v11 CSV contains 26,872 requests, 27 intents, and **11 observed categories**. Removing 2,598 duplicates after case/whitespace normalization leaves 24,274 requests. Splits are 16,991 training, 3,641 validation, and 3,642 test requests.

Source: [Bitext Customer Support dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset). It is hybrid synthetic data. Consult the dataset's license before redistributing it. This documentation package does not include the dataset or model weights.

The dataset has no urgency labels or operational timestamps. Urgency was evaluated on separately authored development scenarios. Operational durations come from locally recorded demo activity. There is no validated resolution-time prediction model.

## Scope and remaining limitations

This is a local portfolio prototype. It has no authentication, reviewer identity management, customer-message integration, background priority worker, or tested multi-user deployment. API/schema failures do not automatically assign urgency. Unknown urgency remains unassigned rather than becoming Low.

Category template overlap can inflate evaluation scores. Urgency has not passed a large independent evaluation. The UI displays saved clarification requests, but there is no dedicated customer-reply ingestion workflow feeding new information into the AI. A reviewer can record a manual assessment once information is available.

The code preserves key audit events, but request failures and invalid model responses are not yet comprehensively persisted for production monitoring. Published-rate token estimates are documented, while actual gateway charges, local compute cost and a controlled end-to-end latency benchmark remain unmeasured.

## Documentation

- [Cost and accuracy comparison](docs/COST_COMPARISON.md)
- [Analyst case study](docs/ANALYST_CASE_STUDY.md)
- [Portfolio narrative](docs/PORTFOLIO.md)
- [Docker run instructions](DOCKER.md)

- [Product requirements](docs/PRD.md)
- [Evaluation report](docs/EVALUATION.md)
- [Demo and verification guide](docs/DEMO.md)


# Analyst case study: reject a misleading service-speed KPI

## Business question

Where should a support lead focus review capacity, and can the available data reliably measure service speed?

Three sources answer different questions. Bitext supports a classifier evaluation, the uploaded customer-support CSV supports a descriptive sample audit, and the app's own event history supports observed demo-operation metrics. They must not be joined as though their tickets or taxonomies refer to the same customers.

## Source audit: uploaded customer_support_tickets.csv

The supplied file has 8,469 unique ticket IDs, five Ticket Type categories, and four source priority labels. It has no ticket-created timestamp. Date of Purchase records a purchase, not a support arrival. “Time to Resolution” contains timestamps, despite its duration-like name.

| Finding | Count | Interpretation |
| --- | ---: | --- |
| Closed tickets | 2,769 | Source status only |
| Open tickets | 2,819 | No backlog age can be derived |
| Pending Customer Response | 2,881 | Separate dependency from internally actionable work |
| All unresolved | 5,700 | Open + pending; 67.30% of sample |
| Closed records with both response and resolution timestamps | 2,769 | Parseable does not mean valid |
| Resolution earlier than first response | 1,365 | 49.30% of closed records |
| Unresolved tickets labeled Critical | 1,403 | Source labels; not verified against the app's urgency rubric |

Missing Time to Resolution on unresolved records is expected, not a reason to fill missing durations with zero. Conversely, reversed event order on closed tickets is an inconsistency to investigate. Do not take absolute values, add 24 hours, substitute purchase date, or silently drop half the closed records to create a credible-looking resolution KPI.

**Stakeholder action:** withhold resolution-time and daily-arrival claims from this source. Ask the data owner for event definitions, timezone, ticket creation time, and corrected chronological timestamps. Separate the pending-customer queue from the internal-action queue before sizing staffing needs.

Category counts are comparatively even: Refund request 1,752; Technical issue 1,747; Cancellation request 1,695; Product inquiry 1,641; Billing inquiry 1,634. This does not support a claim that one category dominates. Even a concentration would require further investigation before attributing it to a documentation gap.

### Provenance boundary

The uploaded filename/schema corresponds to a widely shared [Customer Support Ticket Dataset](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset). The publisher page's metadata could not be fully read during this review, so provenance, generation method, and redistribution license are not independently verified. Treat the upload as sample data, not authenticated company history. No customer names, emails, descriptions or raw rows are included in this package.

See `analysis/public_sample/report.html` for the visual audit and aggregate CSVs beside it for Power BI/Tableau import. `audit_summary.json` records the source SHA-256. The calculations come directly from the uploaded file and can be reproduced:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_public_sample.py --input customer_support_tickets.csv
```

## Model-operations insight

Held-out embeddings sent 160 of 3,642 requests to review, capturing all five observed category errors. Thus 155 reviewed predictions were already correct. This quantifies the tradeoff between the workload of conservative review and mistakes escaping automation. It does not quantify human reviewer accuracy or actual prevented incidents.

On full validation, automatic Claude replacement increased embedding errors from four to eleven, despite correcting two. The action is to keep the human review queue and use AI suggestions as evidence, not automatic overrides. This is an actionable model-governance insight that the project has actually demonstrated.

## Operational trends from your app

Use the app's actual recorded events to produce daily arrivals, category mix, open workload, and mean/median creation-to-resolution hours by urgency:

```powershell
.\.venv\Scripts\python.exe scripts/export_operations.py --db data/triage.db
```

Open `analysis/operations/report.html`. The script is read-only, uses no API, and exports aggregates without customer text or IDs. For a non-Docker run using the original database, pass `--db triage.db` instead.

Definitions:

- Daily arrivals: count by created_at in UTC; zero days filled only within the observed date range.
- Category: final human-confirmed category when available, otherwise original prediction.
- Resolution duration: resolved_at minus created_at, calendar hours, resolved records only.
- Urgency grouping: urgency_at_resolution, preserving the historical snapshot. Missing snapshots remain unassigned, not backfilled from current urgency.
- Open workload: records without resolved_at, grouped by current confirmed urgency.
- Invalid, missing, future or reversed timestamps are reported as exclusions, not silently treated as zero.

The current database contains demonstration activity, not a real customer pilot. Never call its trend a business improvement. Resolved-only means also exclude unresolved long-running work and can understate service burden. Report sample sizes, medians, open workload, and date range alongside means. The script was checked on a temporary fixture; your private Windows database is not available here and must be read locally by you.

## What would close the original historical-analysis gap?

A consented, de-identified helpdesk export with ticket-created, first-response, resolved and reopen events; timezone; independently defined urgency; category; and collection coverage. Use the same metric definitions and audit event order before measuring changes. Without that source, the portfolio should claim a rigorous data-quality audit and instrumented demo analytics—not authentic historical customer-service trends or predictive resolution estimates.

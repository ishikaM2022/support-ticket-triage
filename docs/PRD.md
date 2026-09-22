# Product requirements: Support Ticket Triage v1

Owner: Ishika Wadagbalkar. Status: local portfolio prototype, Docker workflow and ticket persistence verified by the builder. Updated 22 September 2026. This is a retrospective PRD for a working prototype; proposed discovery and pilot work below have not been conducted.

## 1. Problem, user, and desired outcome

Primary user: a support agent deciding which team should handle a ticket and whether it needs urgent attention. Secondary user: a support lead monitoring pending reviews, workload, response deadlines and unresolved requests.

Problem hypothesis: repetitive category assignment consumes agent time, while ambiguous and high-impact requests require contextual judgment. Simply routing a ticket does not ensure a response or resolution. The desired outcome is less manual triage effort without increasing harmful routing mistakes or missed urgent incidents.

No customer interviews, real-team time study, willingness-to-pay test or production impact study has been performed. This project validates a workflow and several model choices, not product-market fit.

### Discovery plan

Interview 3–5 agents and 1–2 support leads; observe recent anonymized triage sessions with permission. Ask how routing mistakes are detected, what makes urgency ambiguous, who handles pending-customer cases, what evidence agents need to trust suggestions, and where elapsed time differs from hands-on time. Review examples of workarounds, incidents and duplicate tickets. Test whether the proposed review queue reduces effort or simply moves it elsewhere. Record disconfirming observations as well as supporting ones.

### Jobs to be done

- Agent: when a ticket arrives, identify the likely owning team and uncertainty so I can route routine work and inspect exceptions.
- Reviewer: when a suggestion is doubtful, see why and record my decision without losing the original prediction.
- Lead: when work remains open, distinguish high urgency, pending information, missed response deadlines and actual resolutions.

## 2. Scope and user journey

Persist ticket → propose category → route or human review → assess urgency or request clarification → track first response → record resolution → review workload and outcomes.

Category routing and urgency assessment are separate decisions. “Critical” is not a category. “Needs assessment” and “Awaiting information” are workflow states, not severity levels. Routing does not resolve a ticket, and recording a response does not send one.

| Must-have | Acceptance criterion | Evidence / limitation |
| --- | --- | --- |
| Durable intake | Save pending classification before inference; failed work remains recoverable | Recovery demonstrated; manual retry, no worker |
| Category routing | Use an allowed category and map it to an owning team | 11 categories; embedding classifier |
| Human review | Low similarity or weak neighbor votes enter review; retain original prediction and reviewer note | Review and correction demonstrated |
| Urgency | Allow Critical/High/Medium/Low, or leave unassigned; require human confirmation | Claude is optional advice, not an autonomous decision |
| Clarification | Save reason and follow-up question without inventing impact | No outgoing message or reply-ingestion integration |
| First response | Track target; record actual/demo response once and freeze its evaluated deadline | Calendar-time policy; not a resolution promise |
| Resolution | Require category routing and first response; retain timestamp, note and urgency snapshot | Observed duration only, no prediction |
| Closed-ticket protection | Exclude resolved tickets from urgency actions and reject changes after closure | Guard included in database module |
| Dashboard | Show category mix, backlog, review needs, SLA results and observed durations | Current records are demo activity |
| Persistence | Preserve tickets through container recreation | User verified Docker down/up persistence |

Should-have for a pilot: reviewer identity, correction reason codes, explicit demo-data exclusion, failure logging and reliable human-time instrumentation. These are not claimed as implemented.

## 3. Urgency and response targets

These service targets are proposed demo policy, not contractual SLAs or industry standards.

| Urgency | Policy | First-response target from creation |
| --- | --- | --- |
| Critical | Active security compromise, ongoing data loss, widespread service outage | 15 calendar minutes |
| High | Significant blocked core task with no workaround | 1 calendar hour |
| Medium | Current functional failure with limited impact or a usable workaround | 8 calendar hours |
| Low | Routine information/nonblocking change without current functional failure | 24 calendar hours |

A customer writing “urgent” alone does not establish severity. A single team's lockout does not automatically prove a platform-wide outage. Unknown impact stays unassigned with a question. Unknown urgency has no severity-based deadline in v1, which creates a monitoring gap: a pilot should introduce an independently tracked assessment-age target so unassigned work cannot disappear indefinitely.

Before first response, reassessment recalculates the target from original creation. After response, the saved deadline and SLA outcome remain fixed. A response without prior urgency is marked unassessed; assigning urgency later does not fabricate a historical SLA result. Resolving a ticket does not erase a missed first-response target. No resolution SLA or predicted completion date is promised.

## 4. Success criteria and measurement plan

Separate observed offline results from proposed pilot targets.

**Observed:** embeddings achieved 99.86% category accuracy on 3,642 held-out synthetic requests. Review captured five of five observed errors with 4.39% of tickets queued. No accepted errors were observed. These are sample outcomes, not guaranteed deployment thresholds. Urgency development sets are too small for autonomous triage.

**Proposed pilot:** one week of workflow instrumentation/baseline, followed by two weeks of an assisted workflow on comparable eligible tickets. Extend the pilot if volume is too low; calendar duration alone is not sufficient evidence. Keep human confirmation of urgency throughout. Compare category/urgency mix and staffing coverage; exclude declared test tickets. For stronger causal evidence, use balanced assignment between manual and assisted flows if the team's workload supports it.

| Metric | Proposed target / guardrail | Definition and collection |
| --- | --- | --- |
| Primary: hands-on triage time | At least 20% lower median than measured manual baseline | Start/finish active-work timer or observed task timing; exclude waiting time; report n, median and upper tail |
| Routing quality | No observed deterioration against independently reviewed manual baseline | Blind reviewer adjudicates a sample of both accepted and flagged tickets; report errors and uncertainty |
| Category review load | Investigate if above 10%; never loosen safety rules merely to hit a workload target | Flagged category tickets / eligible classified tickets; separate urgency-review labor |
| Critical miss guardrail | Any confirmed harmful missed Critical case triggers immediate review and pauses expansion | Independent policy-based adjudication; one incident matters even when aggregate accuracy is high |
| First response | Proposed 95% within target among eligible assessed/responded tickets | Report unresolved/awaiting-response overdue backlog and unassessed tickets separately to avoid denominator bias |
| Unnecessary escalation | Proposed 10% relative reduction, if sufficient baseline events exist | Adjudicated avoidable escalations / eligible tickets; do not count necessary Critical escalation as failure |
| Resolution time | Exploratory outcome, no promised reduction in v1 | Median and mean calendar duration by urgency-at-resolution; report open-ticket aging and sample sizes |

Zero baseline escalations make relative reduction undefined; report counts instead. Low samples or imbalanced cohorts mean “inconclusive,” not success. Instrumentation for hands-on time and independent review is pilot work, not currently available from ticket timestamps alone. Rollout requires review of quality and safety alongside effort reduction.

## 5. Guardrails, error costs, and threshold decision

Urgency false negatives can delay incident response or allow continued data exposure. False positives interrupt responders and cause alert fatigue. Category misroutes cause rework and response delay; they are a separate failure class. No monetary incident-loss estimate has been measured, so v1 does not present an invented expected-loss optimum.

Category auto-acceptance requires top cosine similarity ≥0.80 AND at least four of five neighbors agreeing. On validation, increasing similarity from 0.70 to 0.80 at 0.80 agreement added 109 reviews to catch one additional category error. We chose conservative review, then held thresholds fixed on the final test. Similarity and neighbor votes are uncertainty signals, not calibrated correctness probabilities.

Model output must satisfy allowed-field and consistency checks. The JSON parser accepts a complete outer Markdown fence but still validates the decoded fields. Malformed responses never become an invented Low urgency. A valid label or valid JSON is not proof of factual correctness. Ticket instructions are treated as data, though broad prompt-injection robustness has not been established.

Preserve original predictions, human decisions, reasons and relevant audit events. No automatic sending, autonomous closure or unconfirmed urgency assignment. Demo data and genuine customer events must be distinguishable before a pilot. API/invalid-output logging remains incomplete for production monitoring.

## 6. Evidence-based prioritization

| Decision | Rationale | Revisit when |
| --- | --- | --- |
| Embeddings for categories; human exception queue | Automatic Claude replacement changed 4 validation errors to 11 | Broader independent evaluation demonstrates safe gains |
| Human-confirmed urgency | Critical error cost is asymmetric; evidence is limited to small authored cases | A large independently labeled safety evaluation and operating controls exist |
| SQLite + durable pending records | Sufficient for local demonstration, supports recovery and audit | Concurrent workload, locking, retry or reliability requirements exceed it |
| Defer RabbitMQ | No background-workload need was demonstrated | Multiple workers, sustained queues or delivery guarantees are needed |
| Defer response drafting/sending | Triage quality and reviewer control are the current hypothesis | Triage is validated and approved-response content is available |
| Reject resolution forecasts | Source lacks trustworthy lifecycle history | Reliable event data and a baseline forecast can be evaluated |

At published list rates, category Claude v1 projects to about $0.23 per 1,000 similarly sized requests. The case for the current architecture is measured routing quality and control, not a claim of dramatic API savings. Human review and compute costs also matter; see COST_COMPARISON.md.

## 7. Roadmap and launch boundaries

V1 is complete as a local demonstration. It is not a hosted multi-user helpdesk: no authentication, reviewer identity, live ingestion, messaging integration, background priority worker or production reliability guarantee.

Next validation milestone: run the pilot above, audit accepted predictions, record human effort, and improve invalid-response observability. Exit only with adequate quality evidence and a clear user benefit.

V2 candidates, ordered by dependency: (1) authenticated reviewer identity and real helpdesk event ingestion; (2) human-approved drafted responses with grounded content; (3) sentiment trend alerts evaluated for false alarms; (4) background processing when operational load warrants it. Predictive resolution times depend on reliable timestamps, cohort coverage and held-out forecasting evaluation. Each item requires a measurable benefit rather than being added solely for technical breadth.

## 8. Risks and unresolved questions

Synthetic/paraphrase-heavy classification data can inflate results. The uploaded operational CSV has no created timestamp and reversed event order in 49.3% of closed records. Real-user benefit, acceptable review effort, true incident prevalence and escalation definitions remain unvalidated. University gateway costs/terms may differ from published API prices. The next product decision is whether the assisted workflow improves a real support team's work enough to justify its review and maintenance costs.

# Portfolio narrative

## One-paragraph project description

Support Ticket Triage helps support agents route requests and review uncertainty while tracking urgency, first response and resolution. I compared TF-IDF, embeddings and Claude Haiku 4.5, then selected embeddings with human review after automatic LLM overrides increased validation errors. On 3,642 held-out synthetic requests, the classifier achieved 99.86% accuracy and flagged all five observed errors at a 4.39% review rate. I also fixed a structured-output parsing failure without repeating paid calls, audited timestamp quality before publishing service-speed metrics, and packaged the workflow in Docker with persistent SQLite storage. Business time savings and real-world accuracy remain to be validated in a user pilot.

## Role-specific resume bullets

**AI Developer:** Built a Dockerized support-triage app using MiniLM embeddings, nearest-neighbor classification, SQLite and Claude urgency advice; achieved 99.86% accuracy on 3,642 held-out synthetic tickets and captured all five observed errors with a 4.39% human-review rate.

**Product Management:** Defined support-triage requirements, urgency-based response targets and a pilot measurement plan; used model-comparison evidence to retain human review after automatic LLM overrides increased validation errors from 4 to 11.

**Data / Business Analyst:** Audited 8,469 support-ticket records, identifying reversed response/resolution chronology in 49.3% of closed tickets; produced reproducible category/backlog charts and withheld unsupported service-speed KPIs pending corrected event data.

These are alternative descriptions of the same project, not claims of separate jobs or shipped business impact.

## Two-minute demo

1. Explain the agent/lead problem and the distinction between routing, response and resolution.
2. Submit a routine ticket and an ambiguous request; show review reasons and preserve the original prediction when correcting it.
3. Show optional urgency advice, the human decision and a saved note. Explain that missing impact stays unassigned.
4. Show a response deadline and resolution record; describe calendar-time measurement.
5. Open the matched cost/accuracy comparison and explain why an LLM override was rejected.
6. Open the source-audit chart, explain why purchase dates cannot represent ticket arrival, and show the planned user-pilot metrics.

Before recording, use deliberate demo text and do not display API keys or real customer information. Avoid adding paid API calls solely to rehearse when a saved suggestion is sufficient.

## Claims to avoid

No claim of real-world 99.86% accuracy, guaranteed zero accepted errors, calibrated model confidence, independently proven urgency safety, measured productivity gains, production-grade security, authentic historical staffing trends, or predictive resolution estimates. Token estimates are not bills; a working local Docker app is not public deployment.

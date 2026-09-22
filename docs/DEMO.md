# Demo and verification guide

## Before starting

Use fictional tickets. Keep the API key out of recordings, screenshots, source files, and repository commits. Run the app in the existing environment using the README command. The demo works without AI access except for the optional suggestion button.

## Five-minute walkthrough

1. **Routine routing:** submit “Please help me change my shipping address.” Show the category and assigned team. Explain that submission is committed before inference.
2. **Uncertain routing:** submit “I was charged twice for my order.” In the observed model this predicts ORDER but triggers review. Confirm PAYMENT and explain the duplicate-charge issue. Show that the original prediction remains recorded.
3. **Missing impact:** submit “I need help with something.” Save an urgency deferral with a reason and follow-up question. Show Awaiting information and no invented deadline. This does not contact a customer.
4. **Critical scenario:** use a fictional ongoing private-data exposure ticket. Optionally request Claude's suggestion once. Show it separately from the human urgency and confirm Critical based on the ticket evidence.
5. **Response and resolution:** on a suitable demo ticket, record a simulated response with a labeled note, then resolve it. Show the reduced open backlog and retained resolution note. For an old overdue ticket, response becomes Breached; closure does not reset the SLA.
6. **Evidence:** open the safe notebook's saved results. Explain why the LLM replacement experiments were not adopted and distinguish the 60-ticket LLM pilots from the 3,642-ticket category test.

## Verification checklist

- [ ] Empty submission is rejected without creating a record.
- [ ] A pending ticket survives a restart and can be processed through recovery.
- [ ] Category review retains the original prediction and updates the assigned team.
- [ ] AI suggestions do not overwrite human urgency.
- [ ] A deferred assessment retains its note and question, with no urgency deadline.
- [ ] First response can be recorded only once; its deadline is preserved after urgency changes.
- [ ] Resolution requires category triage and a first response.
- [ ] Resolved tickets leave the urgency action list and database urgency mutations reject them.
- [ ] Total tickets equals open backlog plus resolved tickets.
- [ ] Restarting the app preserves saved records.
- [ ] Safe notebook Run All loads results without paid requests or demo-ticket creation.

The user reported successful local workflow checks. A prior review also tested database lifecycle behavior with a simulated classifier and temporary database, plus syntax and urgency parsing. That does not constitute a full automated UI or concurrent-user test suite. Latest local patches were applied by the user and were not all re-uploaded for a final source diff.

## Repository preparation

Before publishing, capture actual working dependency versions and verify a fresh installation. Do not invent a requirements lockfile from documentation. Supply instructions for obtaining/rebuilding model artifacts before claiming the repository runs from a clean clone.

Exclude API keys, `.venv`, local ticket databases, and private customer records. Check notebook outputs and caches before sharing. Review the Bitext license and model license before redistributing datasets or weights. The course-specific provider requires authorized access and is not a universal public API endpoint.

## Portfolio wording

“Built a support-ticket triage prototype with persistent routing, human review, urgency assessment, and SLA tracking. Achieved 99.86% category accuracy on 3,642 held-out synthetic requests; validation-selected thresholds flagged all five errors while accepting 95.61% automatically. Compared TF-IDF, embeddings, and Claude, and retained human review after automatic LLM replacement increased validation errors.”

Avoid claims of production readiness, guaranteed accuracy, reduced resolution time, real-world cost savings, or fully autonomous incident prioritization.

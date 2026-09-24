import os

import pandas as pd
import streamlit as st

from database import (
    TEAM_BY_CATEGORY,
    init_db,
    list_tickets,
    submit_ticket,
    process_ticket,
    review_ticket,
    recover_pending_tickets,
    URGENCY_LEVELS,
    initialize_urgency_fields,
    assess_urgency,
    save_urgency_suggestion,
    first_response_sla,
    record_first_response,
    resolve_ticket,
    resolution_hours,
    defer_urgency_assessment,
)
from urgency import suggest_urgency


PUBLIC_DEMO = os.environ.get("PUBLIC_DEMO", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
GITHUB_URL = "https://github.com/ishikaM2022/support-ticket-triage"

st.set_page_config(
    page_title="Support Ticket Triage",
    page_icon="🎫",
    layout="wide",
)

init_db()

# Run the migration once per browser session.
if not st.session_state.get("urgency_initialized"):
    initialize_urgency_fields()
    st.session_state["urgency_initialized"] = True

st.title("Support Ticket Triage")
st.caption(
    "Classify support requests, review uncertain predictions, "
    "and route tickets to the appropriate team."
)

if PUBLIC_DEMO:
    st.warning(
        "Public portfolio demo: use fictional information only. "
        "Tickets are visible to other visitors and may reset when "
        "the demo service restarts. Live Claude calls are disabled."
    )

# Display confirmation after a successful action triggers a rerun.
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

page = st.sidebar.radio(
    "Navigate",
    ["Submit ticket", "Human review","Urgency assessment","Response SLAs","Resolution", "Dashboard"],
)

if st.sidebar.button("Refresh data"):
    st.rerun()

st.sidebar.link_button("View source on GitHub", GITHUB_URL)


if page == "Submit ticket":
    st.header("Submit a ticket")

    with st.form("submit_ticket_form", clear_on_submit=True):
        text = st.text_area(
            "Describe the issue",
            placeholder="Example: I was charged twice for my order.",
            height=150,
        )
        submitted = st.form_submit_button("Submit ticket")

    if submitted:
        # Save first. Classification happens only after submission commits.
        try:
            saved = submit_ticket(text)
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("The ticket could not be saved. Please try again.")
        else:
            st.caption(f"Saved ticket ID: {saved['ticket_id']}")

            try:
                with st.spinner("Classifying ticket..."):
                    result = process_ticket(saved["ticket_id"])
            except Exception:
                st.warning(
                    "Your ticket was saved, but classification failed. "
                    "Use the recovery button on the Dashboard to retry."
                )
            else:
                st.success("Ticket saved and classified.")

                left, right = st.columns(2)
                left.metric(
                    "Suggested category",
                    result["predicted_category"],
                )
                right.metric("Assigned team", result["assigned_team"])

                st.write("**Triage status:**", result["triage_status"])

                if result["review_reason"]:
                    st.info(result["review_reason"])

                with st.expander("Classification signals"):
                    st.write(
                        "Nearest-ticket similarity:",
                        round(result["top_similarity"], 3),
                    )
                    st.write(
                        "Neighbor vote agreement:",
                        f"{result['vote_agreement']:.0%}",
                    )
                    st.caption(
                        "These signals are not probabilities "
                        "that the prediction is correct."
                    )


elif page == "Human review":
    st.header("Human review")
    pending = list_tickets(status="Pending review")

    st.write(f"Tickets awaiting review: **{len(pending)}**")

    if not pending:
        st.info("No tickets are waiting for review.")
    else:
        by_id = {ticket["ticket_id"]: ticket for ticket in pending}

        selected_id = st.selectbox(
            "Select a ticket — oldest first",
            options=list(by_id),
            format_func=lambda ticket_id: (
                f"{ticket_id[:8]} — {by_id[ticket_id]['text'][:80]}"
            ),
        )

        selected = by_id[selected_id]

        st.subheader("Customer request")
        st.write(selected["text"])

        st.write(
            "**Original prediction:**",
            selected["predicted_category"],
        )
        st.write("**Suggested team:**", selected["suggested_team"])
        st.write("**Review reason:**", selected["review_reason"])

        categories = sorted(TEAM_BY_CATEGORY)

        with st.form(f"review_{selected_id}"):
            final_category = st.selectbox(
                "Confirmed category",
                options=categories,
                index=None,
                placeholder="Choose the category after reviewing the ticket",
            )

            note = st.text_area(
                "Review note",
                placeholder="Explain why you confirmed or changed the category.",
            )

            confirmed = st.form_submit_button("Confirm and route")

        if confirmed:
            if final_category is None:
                st.error("Choose a category.")
            else:
                try:
                    updated = review_ticket(
                        selected_id,
                        final_category,
                        note,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error(
                        "The review could not be saved. "
                        "Refresh to check the ticket before retrying."
                    )
                else:
                    st.session_state["notice"] = (
                        f"Review saved. Ticket routed to "
                        f"{updated['assigned_team']}."
                    )
                    st.rerun()

elif page == "Urgency assessment":
    st.header("Urgency assessment")
    st.caption(
        "Assess urgency from impact and available workarounds. "
        "Category confidence does not determine urgency."
    )

    with st.expander("Urgency definitions"):
        st.markdown("""
- **Critical:** Active security compromise, ongoing data loss,
  or widespread outage.
- **High:** A core task is blocked with significant impact
  and no workaround.
- **Medium:** Limited functional impact or a workable alternative.
- **Low:** Routine information or a nonblocking change.

Leave a ticket unassessed when essential impact information is missing.
""")

    records = [
        record for record in list_tickets()
        if not record.get("resolved_at")
    ]

    if not records:
        st.info("No open tickets need urgency assessment.")
    else:
        unassessed = [
            record for record in records
            if record.get("urgency") is None
        ]

        assessed = [
            record for record in records
            if record.get("urgency") is not None
        ]

        rank = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
        }

        assessed.sort(
            key=lambda record: (
                rank.get(record["urgency"], 4),
                record["created_at"],
            )
        )

        st.subheader("Assessed tickets — highest urgency first")
        st.caption(
            "Includes routed tickets: routing does not mean resolution."
        )

        if assessed:
            st.dataframe(
                pd.DataFrame(assessed)[
                    [
                        "ticket_id",
                        "text",
                        "urgency",
                        "assigned_team",
                        "triage_status",
                    ]
                ],
                hide_index=True,
            )
        else:
            st.info("No urgency assessments recorded yet.")

        st.subheader(f"Needs assessment: {len(unassessed)}")

        if unassessed:
            st.dataframe(
                pd.DataFrame(unassessed)[
                    ["ticket_id", "created_at", "text","urgency_status"]
                ],
                hide_index=True,
            )

        st.subheader("Assess or update a ticket")

        # Unassessed tickets appear first in the assessment selector.
        selectable = unassessed + assessed
        by_id = {
            record["ticket_id"]: record
            for record in selectable
        }

        selected_id = st.selectbox(
            "Ticket",
            options=list(by_id),
            format_func=lambda ticket_id: (
                f"{by_id[ticket_id].get('urgency') or 'Needs assessment'}"
                f" — {ticket_id[:8]}"
                f" — {by_id[ticket_id]['text'][:70]}"
            ),
            key="urgency_ticket",
        )

        selected = by_id[selected_id]

        st.write(selected["text"])

        existing_suggestion = selected.get("ai_urgency_suggestion")

        st.subheader("AI second opinion")

        if PUBLIC_DEMO:
            st.info(
                "Live Claude requests are disabled in the public demo. "
                "The local version supports an optional Claude Haiku 4.5 "
                "second opinion through an authorized Portkey account."
            )
        else:
            st.caption(
                "Optional: sends this ticket to Claude through your "
                "university Portkey account. Uses your API balance. "
                "A reviewer must confirm the final urgency."
            )

            api_key = st.text_input(
                "Portkey API key",
                type="password",
                key="portkey_api_key",
                help=(
                    "Held in this browser session's app state. "
                    "Not saved to the ticket database."
                ),
            )

            button_label = (
                "Generate another AI suggestion"
                if existing_suggestion
                else "Get AI urgency suggestion"
            )

            if st.button(
                button_label,
                key=f"suggest_urgency_{selected_id}",
                disabled=not api_key.strip(),
            ):
                try:
                    with st.spinner("Assessing urgency with Claude..."):
                        suggestion = suggest_urgency(
                            selected["text"],
                            api_key,
                        )
                except ValueError:
                    st.error(
                        "The input or model response failed validation. "
                        "No suggestion was saved. Manual assessment is "
                        "available."
                    )
                except Exception:
                    st.error(
                        "The AI request failed. No suggestion was saved. "
                        "Manual assessment is available."
                    )
                else:
                    try:
                        save_urgency_suggestion(
                            selected_id,
                            suggestion,
                        )
                    except Exception:
                        st.error(
                            "Claude returned a suggestion, but it could "
                            "not be saved. The API request may have used "
                            "credits."
                        )
                        st.json(suggestion)
                    else:
                        st.session_state["notice"] = (
                            "AI suggestion saved. Confirm the urgency "
                            "using the assessment form below."
                        )
                        st.rerun()

        if existing_suggestion:
            suggested_level = (
                existing_suggestion["urgency"]
                or "Needs assessment"
            )

            if existing_suggestion["urgency"] is None:
                st.write("**AI suggested urgency:** Not assigned")
                st.info("More information is needed before urgency can be assessed.")
            else:
                st.write(
                    "**AI suggested urgency:**",
                    existing_suggestion["urgency"],
                )
            st.write("**Reason:**", existing_suggestion["reason"])

            question = existing_suggestion.get("follow_up_question")

            if question:
                st.info(f"Suggested follow-up: {question}")

            st.caption(
                f"Model: {existing_suggestion['model']} · "
                f"Prompt: {existing_suggestion['prompt_version']}"
            )

            if suggested_level == "Critical":
                st.warning(
                    "AI suggests a possible critical incident. "
                    "Review promptly; urgency has not been "
                    "automatically confirmed."
                )

        st.divider()

        if selected.get("urgency_note"):
            st.write("**Previous assessment:**", selected["urgency_note"])

        if selected.get("urgency_status") == "Awaiting information":
            st.info("Urgency assessment is awaiting more information.")
            st.write(
                "**Saved follow-up question:**",
                selected.get("urgency_follow_up_question", ""),
            )
            st.caption("This question has not been sent automatically.")

        if (
            selected.get("urgency") is None
            and not selected.get("resolved_at")
        ):
            with st.expander("Not enough information to assign urgency"):
                st.caption(
                    "Save a clarification request while leaving urgency "
                    "unassigned. This does not contact the customer."
                )

                ai_suggestion = selected.get("ai_urgency_suggestion") or {}

                suggested_question = (
                    selected.get("urgency_follow_up_question")
                    or ai_suggestion.get("follow_up_question")
                    or ""
                )

                with st.form(f"defer_urgency_{selected_id}"):
                    defer_note = st.text_area(
                        "Why is more information needed?",
                        value=(
                            selected.get("urgency_note") or ""
                            if selected.get("urgency_status")
                            == "Awaiting information"
                            else ""
                        ),
                    )

                    follow_up = st.text_area(
                        "Question to ask the customer",
                        value=suggested_question,
                    )

                    defer_submitted = st.form_submit_button(
                        "Save as awaiting information"
                    )

                if defer_submitted:
                    try:
                        defer_urgency_assessment(
                            selected_id,
                            defer_note,
                            follow_up,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error(
                            "Could not confirm the save. "
                            "Refresh and check the ticket before retrying."
                        )
                    else:
                        st.session_state["notice"] = (
                            "Saved as awaiting information. "
                            "No message was sent."
                        )
                        st.rerun()

        with st.form(f"urgency_form_{selected_id}"):
            urgency = st.selectbox(
                "Urgency",
                options=URGENCY_LEVELS,
                index=None,
                placeholder="Choose after assessing impact",
            )

            note = st.text_area(
                "Supporting evidence",
                placeholder=(
                    "Who is affected? What is blocked? "
                    "Is there a workaround?"
                ),
            )

            save = st.form_submit_button("Save urgency")

        if save:
            try:
                assess_urgency(selected_id, urgency, note)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error(
                    "Could not save the assessment. "
                    "Refresh and check the ticket before retrying."
                )
            else:
                st.session_state["notice"] = (
                    f"Urgency saved as {urgency}."
                )
                st.rerun()

elif page == "Response SLAs":
    st.header("First-response SLAs")
    st.caption(
        "Demo targets use calendar time from ticket creation: "
        "Critical 15 minutes, High 1 hour, Medium 8 hours, Low 24 hours. "
        "Times below are UTC. Click Refresh data to update the countdown."
    )

    records = list_tickets()

    if not records:
        st.info("No tickets have been submitted.")
    else:
        sla_rows = []

        for record in records:
            sla = first_response_sla(record)

            sla_rows.append({
                "ticket_id": record["ticket_id"],
                "ticket": record["text"],
                "current_urgency": record.get("urgency"),
                "urgency_at_response": record.get(
                    "urgency_at_first_response"
                ),
                "sla_status": sla["status"],
                "deadline_utc": sla["deadline"],
                "minutes_remaining": sla["minutes_remaining"],
                "first_response_utc": record.get("first_response_at"),
            })

        sla_df = pd.DataFrame(sla_rows)

        overdue, unassessed, responded = st.columns(3)

        overdue.metric(
            "Overdue — no response",
            int(sla_df["sla_status"].eq("Overdue").sum()),
        )
        unassessed.metric(
            "Awaiting response — urgency unassessed",
            int(
                sla_df["sla_status"]
                .eq("Needs urgency assessment")
                .sum()
            ),
        )
        responded.metric(
            "Responses recorded",
            int(sla_df["first_response_utc"].notna().sum()),
        )

        # Keep overdue work prominent; unknown urgency stays visible.
        status_order = {
            "Overdue": 0,
            "Needs urgency assessment": 1,
            "Awaiting response": 2,
            "Breached": 3,
            "Met": 4,
            "Responded — SLA unassessed": 5,
        }

        sla_df["_order"] = sla_df["sla_status"].map(status_order)

        st.dataframe(
            sla_df.sort_values(
                ["_order", "deadline_utc"],
                na_position="last",
            ).drop(columns="_order"),
            hide_index=True,
        )

        st.subheader("Record first response")
        st.caption(
            "This records that a response was sent; it does not "
            "send a message or resolve the ticket. The recorded "
            "response time will be the time you save this form."
        )

        awaiting_response = [
            record for record in records
            if not record.get("first_response_at")
        ]

        if not awaiting_response:
            st.info("All tickets have a first response recorded.")
        else:
            by_id = {
                record["ticket_id"]: record
                for record in awaiting_response
            }

            selected_id = st.selectbox(
                "Ticket awaiting a response",
                options=list(by_id),
                format_func=lambda ticket_id: (
                    f"{ticket_id[:8]} — "
                    f"{by_id[ticket_id]['text'][:80]}"
                ),
                key="response_ticket",
            )

            st.write(by_id[selected_id]["text"])

            with st.form(f"response_form_{selected_id}"):
                note = st.text_area(
                    "Response note",
                    placeholder=(
                        "Summarize the response and the channel used. "
                        "For a demo, explicitly label it as simulated."
                    ),
                )

                confirmed = st.checkbox(
                    "I confirm a response was sent, or this is "
                    "an explicitly labeled demo simulation."
                )

                save_response = st.form_submit_button(
                    "Record first response now"
                )

            if save_response:
                if not confirmed:
                    st.error("Confirm the response before recording it.")
                else:
                    try:
                        record_first_response(selected_id, note)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error(
                            "Could not confirm the save. Refresh and "
                            "check the ticket before retrying."
                        )
                    else:
                        st.session_state["notice"] = (
                            "First response recorded."
                        )
                        st.rerun()

elif page == "Resolution":
    st.header("Ticket resolution")
    st.caption(
        "Resolve a ticket only after the issue has been addressed. "
        "For fictional tickets, label the resolution note as a demo."
    )

    records = list_tickets()

    open_tickets = [
        record for record in records
        if not record.get("resolved_at")
    ]

    st.metric("Open tickets", len(open_tickets))

    eligible = [
        record for record in open_tickets
        if record["triage_status"] in (
            "Auto-routed", "Reviewed and routed"
        )
        and record.get("first_response_at")
    ]

    if not eligible:
        st.info(
            "No tickets are ready for resolution. Complete category "
            "triage and record a first response first."
        )
    else:
        by_id = {
            record["ticket_id"]: record
            for record in eligible
        }

        selected_id = st.selectbox(
            "Ticket to resolve",
            options=list(by_id),
            format_func=lambda ticket_id: (
                f"{ticket_id[:8]} — "
                f"{by_id[ticket_id]['text'][:80]}"
            ),
            key="resolution_ticket",
        )

        st.write(by_id[selected_id]["text"])

        with st.form(f"resolve_{selected_id}"):
            note = st.text_area(
                "Resolution note",
                placeholder="What action resolved the issue?",
            )

            submitted = st.form_submit_button("Mark resolved")

        if submitted:
            try:
                resolve_ticket(selected_id, note)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error(
                    "Could not confirm the save. Refresh and check "
                    "the ticket before retrying."
                )
            else:
                st.session_state["notice"] = "Ticket marked resolved."
                st.rerun()

    st.subheader("Resolved tickets")

    resolved_rows = [
        {
            "ticket_id": record["ticket_id"],
            "ticket": record["text"],
            "urgency_at_resolution": record.get("urgency_at_resolution"),
            "resolved_at": record["resolved_at"],
            "resolution_hours": round(resolution_hours(record), 2),
            "resolution_note": record.get("resolution_note"),
        }
        for record in records
        if record.get("resolved_at")
    ]

    if resolved_rows:
        st.dataframe(pd.DataFrame(resolved_rows), hide_index=True)
    else:
        st.info("No resolved tickets yet.")

else:
    st.header("Dashboard")
    st.caption(
        "Metrics describe this demo's submitted tickets. "
        "They do not establish real-world support performance."
    )

    if st.button("Retry pending classifications"):
        with st.spinner("Processing saved pending tickets..."):
            recovered = recover_pending_tickets()

        if not recovered:
            st.info("No tickets are awaiting classification.")
        else:
            failures = sum(
                item["error"] is not None
                for item in recovered
            )
            st.write(
                f"Processed: {len(recovered) - failures}. "
                f"Still pending after errors: {failures}."
            )

    records = list_tickets()

    if not records:
        st.info("Submit a ticket to populate the dashboard.")
    else:
        rows = []

        for record in records:
            resolved = bool(record.get("resolved_at"))
            sla = first_response_sla(record)

            rows.append({
                "ticket_id": record["ticket_id"],
                "created_at": record["created_at"],
                "text": record["text"],
                "category": (
                    record.get("final_category")
                    or record.get("predicted_category")
                    or "Unclassified"
                ),
                "category_confirmed": (
                    record.get("triage_status") == "Reviewed and routed"
                ),
                "urgency": record.get("urgency") or "Needs assessment",
                "urgency_at_resolution": (
                    record.get("urgency_at_resolution")
                    or "Unassessed at resolution"
                ),
                "assigned_team": record.get("assigned_team"),
                "triage_status": record["triage_status"],
                "resolution_status": "Resolved" if resolved else "Open",
                "first_response_sla": sla["status"],
                "resolution_hours": resolution_hours(record),
            })

        df = pd.DataFrame(rows)
        open_mask = df["resolution_status"].eq("Open")
        resolved_mask = ~open_mask

        total, backlog, closed, overdue = st.columns(4)

        total.metric("Total tickets", len(df))
        backlog.metric("Open backlog", int(open_mask.sum()))
        closed.metric("Resolved", int(resolved_mask.sum()))
        overdue.metric(
            "Open — response overdue",
            int(
                (
                    open_mask
                    & df["first_response_sla"].eq("Overdue")
                ).sum()
            ),
        )

        category_review, urgency_review = st.columns(2)

        category_review.metric(
            "Open — category review needed",
            int(
                (
                    open_mask
                    & df["triage_status"].eq("Pending review")
                ).sum()
            ),
        )

        urgency_review.metric(
            "Open — urgency assessment needed",
            int(
                (
                    open_mask
                    & df["urgency"].eq("Needs assessment")
                ).sum()
            ),
        )

        st.subheader("Ticket volume by creation date")
        st.caption("UTC dates; includes both open and resolved tickets.")

        created = pd.to_datetime(df["created_at"], utc=True)
        daily_counts = (
            df.assign(creation_date=created.dt.strftime("%Y-%m-%d"))
            .groupby("creation_date")
            .size()
            .rename("Tickets")
        )
        st.bar_chart(daily_counts)

        left, right = st.columns(2)

        with left:
            st.subheader("Category breakdown")
            st.caption(
                "All tickets. Uses the final category when available; "
                "otherwise uses the model's suggestion."
            )
            st.bar_chart(
                df["category"].value_counts().rename("Tickets")
            )

        with right:
            st.subheader("Open backlog by urgency")
            st.caption("Human-confirmed urgency; unknowns stay visible.")

            urgency_counts = (
                df.loc[open_mask, "urgency"]
                .value_counts()
                .reindex(
                    ["Critical", "High", "Medium", "Low", "Needs assessment"],
                    fill_value=0,
                )
                .rename("Tickets")
            )
            st.bar_chart(urgency_counts)

        st.subheader("Observed resolution time")
        st.caption(
            "Elapsed calendar hours from creation to resolution. "
            "Resolved tickets only; open tickets are excluded. "
            "These are observations, not estimates for new tickets."
        )

        resolved_df = df.loc[resolved_mask]

        if resolved_df.empty:
            st.info("Resolve a ticket to populate these metrics.")
        else:
            mean_col, median_col = st.columns(2)

            mean_col.metric(
                "Mean resolution hours",
                f"{resolved_df['resolution_hours'].mean():.2f}",
            )
            median_col.metric(
                "Median resolution hours",
                f"{resolved_df['resolution_hours'].median():.2f}",
            )

            resolution_summary = (
                resolved_df.groupby("urgency_at_resolution")
                .agg(
                    resolved_tickets=("ticket_id", "size"),
                    mean_hours=("resolution_hours", "mean"),
                    median_hours=("resolution_hours", "median"),
                )
                .round(2)
                .reset_index()
            )

            st.dataframe(resolution_summary, hide_index=True)

        st.subheader("First-response SLA outcomes")
        st.caption(
            "Met and Breached are completed response outcomes. "
            "Overdue means no response has been recorded."
        )
        st.dataframe(
            df["first_response_sla"]
            .value_counts()
            .rename_axis("SLA status")
            .reset_index(name="Tickets"),
            hide_index=True,
        )

        st.subheader("All tickets")
        st.dataframe(
            df[
                [
                    "ticket_id",
                    "text",
                    "category",
                    "urgency",
                    "assigned_team",
                    "triage_status",
                    "resolution_status",
                    "first_response_sla",
                ]
            ],
            hide_index=True,
        )

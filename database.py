import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from classifier import triage_ticket


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TRIAGE_DB_PATH", str(PROJECT_DIR / "triage.db"))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_DIR / DB_PATH

CONFIG = json.loads(
    (PROJECT_DIR / "artifacts" / "config.json").read_text(
        encoding="utf-8"
    )
)
TEAM_BY_CATEGORY = CONFIG["team_by_category"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect_db():
    """Commit successful operations, roll back failures, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_events (
                event_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                event_json TEXT NOT NULL
            )
        """)


def _read_ticket(conn, ticket_id):
    row = conn.execute(
        "SELECT record_json FROM tickets WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()

    if row is None:
        raise ValueError("Ticket ID not found.")

    return json.loads(row[0])


def _update_ticket(conn, record):
    conn.execute(
        "UPDATE tickets SET record_json = ? WHERE ticket_id = ?",
        (json.dumps(record), record["ticket_id"]),
    )


def get_ticket(ticket_id):
    with connect_db() as conn:
        return _read_ticket(conn, ticket_id)


def list_tickets(status=None):
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT record_json FROM tickets"
        ).fetchall()

    records = [json.loads(row[0]) for row in rows]

    if status is not None:
        records = [
            record for record in records
            if record["triage_status"] == status
        ]

    return sorted(records, key=lambda record: record["created_at"])


def submit_ticket(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please enter a non-empty ticket description.")

    record = {
        "ticket_id": str(uuid4()),
        "created_at": utc_now(),
        "text": text.strip(),
        "predicted_category": None,
        "final_category": None,
        "suggested_team": None,
        "assigned_team": None,
        "triage_status": "Pending classification",
        "top_similarity": None,
        "vote_agreement": None,
        "review_reason": None,
        "classified_at": None,
        "reviewed_at": None,
        "reviewer_note": None,
        "urgency": None,
        "urgency_status": "Needs assessment",
        "urgency_note": None,
        "urgency_assessed_at": None,
        "resolution_status": "Open",
        "resolved_at": None,
        "resolution_note": None,
        "urgency_at_resolution": None,
    }

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO tickets VALUES (?, ?)",
            (record["ticket_id"], json.dumps(record)),
        )

    return record


def process_ticket(ticket_id):
    record = get_ticket(ticket_id)

    if record["triage_status"] != "Pending classification":
        return record

    # If classification fails, the saved ticket remains pending.
    result = triage_ticket(record["text"])
    category = result["predicted_category"]
    needs_review = result["status"] == "Needs human review"

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = _read_ticket(conn, ticket_id)

        # Another process may have completed it while the model ran.
        if current["triage_status"] != "Pending classification":
            return current

        current.update({
            "predicted_category": category,
            "final_category": None if needs_review else category,
            "suggested_team": TEAM_BY_CATEGORY[category],
            "assigned_team": (
                "Human Review" if needs_review
                else TEAM_BY_CATEGORY[category]
            ),
            "triage_status": (
                "Pending review" if needs_review else "Auto-routed"
            ),
            "top_similarity": result["top_similarity"],
            "vote_agreement": result["vote_agreement"],
            "review_reason": result["review_reason"],
            "classified_at": utc_now(),
        })

        _update_ticket(conn, current)

    return current


def review_ticket(ticket_id, final_category, note):
    if final_category not in TEAM_BY_CATEGORY:
        raise ValueError("Choose a valid category.")

    if not isinstance(note, str) or not note.strip():
        raise ValueError("Add a short explanation for the review.")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)

        if record["triage_status"] != "Pending review":
            raise ValueError("This ticket is not awaiting review.")

        reviewed_at = utc_now()
        event = {
            "original_prediction": record["predicted_category"],
            "final_category": final_category,
            "note": note.strip(),
        }

        record.update({
            "final_category": final_category,
            "assigned_team": TEAM_BY_CATEGORY[final_category],
            "triage_status": "Reviewed and routed",
            "reviewed_at": reviewed_at,
            "reviewer_note": note.strip(),
        })

        _update_ticket(conn, record)

        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                reviewed_at,
                json.dumps(event),
            ),
        )

    return record


def recover_pending_tickets():
    results = []

    for record in list_tickets(status="Pending classification"):
        ticket_id = record["ticket_id"]

        try:
            processed = process_ticket(ticket_id)
            results.append({
                "ticket_id": ticket_id,
                "status": processed["triage_status"],
                "error": None,
            })
        except Exception as exc:
            results.append({
                "ticket_id": ticket_id,
                "status": "Pending classification",
                "error": type(exc).__name__,
            })

    return results

URGENCY_LEVELS = ("Critical", "High", "Medium", "Low")


def initialize_urgency_fields():
    """Add urgency fields to existing tickets without overwriting decisions."""
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        rows = conn.execute(
            "SELECT record_json FROM tickets"
        ).fetchall()

        for row in rows:
            record = json.loads(row[0])

            defaults = {
                "urgency": None,
                "urgency_status": "Needs assessment",
                "urgency_note": None,
                "urgency_assessed_at": None,
            }

            changed = False

            for field, value in defaults.items():
                if field not in record:
                    record[field] = value
                    changed = True

            if changed:
                _update_ticket(conn, record)


def assess_urgency(ticket_id, urgency, note):
    
    if urgency not in URGENCY_LEVELS:
        raise ValueError("Choose a valid urgency level.")

    if not isinstance(note, str) or not note.strip():
        raise ValueError("Explain the impact supporting this urgency.")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)
        if record.get("resolved_at"):
            raise ValueError("This ticket is already resolved.")

        assessed_at = utc_now()

        event = {
            "event_type": "urgency_assessment",
            "previous_urgency": record.get("urgency"),
            "new_urgency": urgency,
            "note": note.strip(),
        }

        record.update({
            "urgency": urgency,
            "urgency_status": "Assessed",
            "urgency_note": note.strip(),
            "urgency_assessed_at": assessed_at,
        })

        _update_ticket(conn, record)

        # Reuse our audit-event table.
        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                assessed_at,
                json.dumps(event),
            ),
        )

    return record

def save_urgency_suggestion(ticket_id, suggestion):
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)
        if record.get("resolved_at"):
            raise ValueError("This ticket is already resolved.")

        saved_at = utc_now()

        # Keep AI suggestions separate from human-confirmed urgency.
        record["ai_urgency_suggestion"] = {
            **suggestion,
            "suggested_at": saved_at,
        }

        _update_ticket(conn, record)

        # Preserve previous suggestions in the audit history.
        event = {
            "event_type": "ai_urgency_suggestion",
            "suggestion": record["ai_urgency_suggestion"],
        }

        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                saved_at,
                json.dumps(event),
            ),
        )

    return record

# Demo policy: calendar time, measured from ticket creation.
FIRST_RESPONSE_MINUTES = {
    "Critical": 15,
    "High": 60,
    "Medium": 8 * 60,
    "Low": 24 * 60,
}


def first_response_sla(record, now=None):
    """Calculate status without changing the saved ticket."""
    urgency = record.get("urgency")
    response_at = record.get("first_response_at")

    # Preserve the target used when a response was recorded.
    saved_deadline = record.get("first_response_due_at_at_response")

    if response_at:
        deadline = (
            datetime.fromisoformat(saved_deadline)
            if saved_deadline else None
        )
    elif urgency in FIRST_RESPONSE_MINUTES:
        created_at = datetime.fromisoformat(record["created_at"])
        deadline = created_at + timedelta(
            minutes=FIRST_RESPONSE_MINUTES[urgency]
        )
    else:
        deadline = None

    if deadline is None:
        return {
            "deadline": None,
            "status": (
                "Responded — SLA unassessed"
                if response_at else "Needs urgency assessment"
            ),
            "minutes_remaining": None,
        }

    if response_at:
        responded = datetime.fromisoformat(response_at)
        return {
            "deadline": deadline.isoformat(),
            "status": (
                "Met" if responded <= deadline else "Breached"
            ),
            "minutes_remaining": None,
        }

    now = now or datetime.now(timezone.utc)
    remaining = (deadline - now).total_seconds() / 60

    return {
        "deadline": deadline.isoformat(),
        "status": "Overdue" if remaining < 0 else "Awaiting response",
        "minutes_remaining": round(remaining, 1),
    }


def record_first_response(ticket_id, note):
    """Record a response that was actually sent; does not send a message."""
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Add a note describing the response sent.")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)

        if record.get("first_response_at"):
            raise ValueError("A first response is already recorded.")

        responded_at = utc_now()
        sla = first_response_sla(record)

        record.update({
            "first_response_at": responded_at,
            "first_response_note": note.strip(),
            "urgency_at_first_response": record.get("urgency"),
            "first_response_due_at_at_response": sla["deadline"],
        })

        _update_ticket(conn, record)

        event = {
            "event_type": "first_response",
            "note": note.strip(),
            "urgency_at_response": record.get("urgency"),
            "deadline_at_response": sla["deadline"],
        }

        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                responded_at,
                json.dumps(event),
            ),
        )

    return record

def resolve_ticket(ticket_id, note):
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Explain how the issue was resolved.")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)

        if record.get("resolved_at"):
            raise ValueError("This ticket is already resolved.")

        if record["triage_status"] not in (
            "Auto-routed", "Reviewed and routed"
        ):
            raise ValueError("Complete category triage first.")

        if not record.get("first_response_at"):
            raise ValueError("Record the first response before resolution.")

        resolved_at = utc_now()

        record.update({
            "resolution_status": "Resolved",
            "resolved_at": resolved_at,
            "resolution_note": note.strip(),
            "urgency_at_resolution": record.get("urgency"),
        })

        _update_ticket(conn, record)

        event = {
            "event_type": "ticket_resolved",
            "note": note.strip(),
            "urgency_at_resolution": record.get("urgency"),
        }

        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                resolved_at,
                json.dumps(event),
            ),
        )

    return record


def resolution_hours(record):
    if not record.get("resolved_at"):
        return None

    created = datetime.fromisoformat(record["created_at"])
    resolved = datetime.fromisoformat(record["resolved_at"])

    return (resolved - created).total_seconds() / 3600

def defer_urgency_assessment(ticket_id, note, question):
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Explain why urgency cannot be assessed.")

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Enter a follow-up question.")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = _read_ticket(conn, ticket_id)

        # Don't accidentally remove an existing confirmed priority.
        if record.get("urgency") is not None:
            raise ValueError(
                "This ticket already has confirmed urgency. "
                "This action only applies to unassessed tickets."
            )

        if record.get("resolved_at"):
            raise ValueError("This ticket is already resolved.")

        recorded_at = utc_now()

        record.update({
            "urgency": None,
            "urgency_status": "Awaiting information",
            "urgency_note": note.strip(),
            "urgency_follow_up_question": question.strip(),
            "urgency_information_requested_at": recorded_at,
        })

        _update_ticket(conn, record)

        event = {
            "event_type": "urgency_assessment_deferred",
            "note": note.strip(),
            "follow_up_question": question.strip(),
            "message_sent": False,
        }

        conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?)",
            (
                str(uuid4()),
                ticket_id,
                recorded_at,
                json.dumps(event),
            ),
        )

    return record

if __name__ == "__main__":
    init_db()
    records = list_tickets()

    print("Database:", DB_PATH)
    print("Saved tickets:", len(records))

    for record in records:
        print(
            record["ticket_id"],
            record["triage_status"],
            record["assigned_team"],
        )
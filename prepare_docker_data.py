"""Copy the existing SQLite database once; never overwrite either database."""
from pathlib import Path
import sqlite3


def main():
    root = Path(__file__).resolve().parent
    source = root / "triage.db"
    target = root / "data" / "triage.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print("Docker database already exists; left unchanged:", target)
        return
    if not source.is_file():
        print("No existing triage.db. The app will create a new database in", target.parent)
        return
    # Reserve the destination without overwriting an existing file.
    with target.open("xb"):
        pass
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst)
    finally:
        # SQLite connection context managers do not close connections.
        if "dst" in locals():
            dst.close()
        if "src" in locals():
            src.close()
    print("Copied existing tickets and audit history to:", target)
    print("Original database is unchanged:", source)


if __name__ == "__main__":
    main()

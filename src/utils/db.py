import sqlite3
import os

class LeadDB:
    """
    Simple SQLite-backed store to remember seen lead IDs.
    """

    def __init__(self, db_path: str = "data/seen_leads.db"):
        # ensure directory exists
        db_dir = os.path.dirname(db_path) or "."
        os.makedirs(db_dir, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_leads(
              lead_id TEXT PRIMARY KEY
            )
            """
        )
        self.conn.commit()

    def is_seen(self, lead_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM seen_leads WHERE lead_id=?", (lead_id,))
        return cur.fetchone() is not None

    def mark_seen(self, lead_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_leads(lead_id) VALUES(?)", (lead_id,)
        )
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

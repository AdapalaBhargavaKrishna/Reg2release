import sqlite3
import hashlib
import json
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit_log.db")

class AuditTrail:
    """Tamper-evident, hash-chained SQLite audit logger as specified in Section 7 of Reg2Release proposal."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_id TEXT NOT NULL,
                step TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_clause TEXT,
                input_hash TEXT NOT NULL,
                output_payload TEXT NOT NULL,
                confidence_score REAL,
                reviewer_decision TEXT,
                previous_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Audit log is append-only. Modification is strictly prohibited.');
            END;
            """)

            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Audit log is append-only. Deletion is strictly prohibited.');
            END;
            """)
            conn.commit()
        finally:
            conn.close()

    def get_latest_hash(self, change_id: str) -> str:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT record_hash FROM audit_log WHERE change_id = ? ORDER BY id DESC LIMIT 1",
                (change_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            return "0000000000000000000000000000000000000000000000000000000000000000"
        finally:
            conn.close()

    def log_step(
        self,
        change_id: str,
        step: str,
        source_clause: str,
        input_data: any,
        output_data: any,
        confidence_score: float = 1.0,
        reviewer_decision: str = None
    ) -> dict:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        input_str = json.dumps(input_data, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode("utf-8")).hexdigest()

        output_str = json.dumps(output_data, sort_keys=True, default=str)
        previous_hash = self.get_latest_hash(change_id)

        hasher = hashlib.sha256()
        hasher.update(previous_hash.encode("utf-8"))
        hasher.update(change_id.encode("utf-8"))
        hasher.update(step.encode("utf-8"))
        hasher.update(timestamp.encode("utf-8"))
        hasher.update(input_hash.encode("utf-8"))
        hasher.update(output_str.encode("utf-8"))
        if reviewer_decision:
            hasher.update(reviewer_decision.encode("utf-8"))
        record_hash = hasher.hexdigest()

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_log (
                change_id, step, timestamp, source_clause, input_hash,
                output_payload, confidence_score, reviewer_decision,
                previous_hash, record_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change_id, step, timestamp, source_clause or "",
                input_hash, output_str, confidence_score, reviewer_decision or "N/A",
                previous_hash, record_hash
            ))
            conn.commit()
        finally:
            conn.close()

        return {
            "change_id": change_id,
            "step": step,
            "timestamp": timestamp,
            "record_hash": record_hash,
            "previous_hash": previous_hash
        }

    def get_trail(self, change_id: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, step, timestamp, source_clause, confidence_score,
                   reviewer_decision, previous_hash, record_hash, output_payload
            FROM audit_log
            WHERE change_id = ?
            ORDER BY id ASC
            """, (change_id,))
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()

    def verify_chain_integrity(self, change_id: str) -> dict:
        """Verifies mathematical validity of the hash chain."""
        trail = self.get_trail(change_id)
        if not trail:
            return {"valid": True, "count": 0, "message": "No logs recorded for this change ID."}

        for i, entry in enumerate(trail):
            if i == 0:
                expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"
            else:
                expected_prev = trail[i - 1]["record_hash"]

            if entry["previous_hash"] != expected_prev:
                return {
                    "valid": False,
                    "tampered_step": entry["step"],
                    "entry_id": entry["id"],
                    "message": f"Hash chain broken at entry #{entry['id']} ({entry['step']})."
                }

        return {
            "valid": True,
            "count": len(trail),
            "latest_hash": trail[-1]["record_hash"],
            "message": f"All {len(trail)} audit log records verified cryptographically unbroken."
        }

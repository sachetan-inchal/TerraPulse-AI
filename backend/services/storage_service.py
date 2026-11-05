import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymongo
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()


class StorageService:
    def __init__(self, mongo_uri: Optional[str] = None, db_name: str = "terrapulse_air"):
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = db_name
        self.mongo_client: Optional[pymongo.MongoClient] = None
        self.db: Optional[pymongo.database.Database] = None
        self.is_mongodb_connected = False
        self.connection_error: Optional[str] = None

        # Setup local SQLite fallback storage directory
        self.data_dir = Path(__file__).resolve().parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = self.data_dir / "terrapulse_fallback.db"

        self._init_sqlite()
        self._try_connect_mongodb()

    def _init_sqlite(self):
        """Initialize local SQLite tables for resilient persistence fallback."""
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    created_at TEXT,
                    messages TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_traces (
                    run_id TEXT PRIMARY KEY,
                    user_prompt TEXT,
                    timestamp TEXT,
                    duration_ms REAL,
                    data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS investigation_reports (
                    report_id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_history (
                    test_id TEXT PRIMARY KEY,
                    tab TEXT,
                    component TEXT,
                    status TEXT,
                    duration_ms REAL,
                    timestamp TEXT,
                    data TEXT
                )
            """)
            conn.commit()

    def _try_connect_mongodb(self) -> bool:
        """Attempt connection to MongoDB with a short timeout to prevent blocking."""
        try:
            self.mongo_client = pymongo.MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500
            )
            # Force server check
            self.mongo_client.server_info()
            self.db = self.mongo_client[self.db_name]
            self.is_mongodb_connected = True
            self.connection_error = None
            return True
        except (ServerSelectionTimeoutError, PyMongoError, Exception) as e:
            self.is_mongodb_connected = False
            self.connection_error = str(e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return connectivity status of the persistence subsystem."""
        # Check if Mongo came online
        if not self.is_mongodb_connected:
            self._try_connect_mongodb()

        return {
            "mongodb_connected": self.is_mongodb_connected,
            "mongodb_uri": self.mongo_uri.split("@")[-1],  # redact credentials if any
            "database_name": self.db_name,
            "connection_error": self.connection_error,
            "fallback_active": not self.is_mongodb_connected,
            "fallback_storage": "SQLite Local Persistence Engine",
            "fallback_path": str(self.sqlite_path)
        }

    # 1. Sessions
    def save_session(self, session_id: str, data: Dict[str, Any]):
        now = datetime.now(timezone.utc).isoformat()
        clean_data = self._sanitize_record(data)
        if self.is_mongodb_connected and self.db is not None:
            try:
                self.db.sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"data": clean_data, "updated_at": now}, "$setOnInsert": {"created_at": now}},
                    upsert=True
                )
                return
            except Exception:
                self.is_mongodb_connected = False

        # SQLite fallback
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, created_at, updated_at, data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at, data=excluded.data
            """, (session_id, now, now, json.dumps(clean_data)))
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mongodb_connected and self.db is not None:
            try:
                doc = self.db.sessions.find_one({"session_id": session_id}, {"_id": 0})
                if doc:
                    return doc.get("data")
            except Exception:
                self.is_mongodb_connected = False

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    # 2. Agent Traces
    def save_agent_trace(self, run_id: str, trace_data: Dict[str, Any]):
        now = datetime.now(timezone.utc).isoformat()
        clean_data = self._sanitize_record(trace_data)
        if self.is_mongodb_connected and self.db is not None:
            try:
                self.db.agent_traces.update_one(
                    {"run_id": run_id},
                    {"$set": {**clean_data, "saved_at": now}},
                    upsert=True
                )
                return
            except Exception:
                self.is_mongodb_connected = False

        prompt = clean_data.get("user_prompt", "")
        dur = clean_data.get("total_duration_ms", 0.0)
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_traces (run_id, user_prompt, timestamp, duration_ms, data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET data=excluded.data
            """, (run_id, prompt, now, dur, json.dumps(clean_data)))
            conn.commit()

    def get_agent_trace(self, run_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mongodb_connected and self.db is not None:
            try:
                doc = self.db.agent_traces.find_one({"run_id": run_id}, {"_id": 0})
                if doc:
                    return doc
            except Exception:
                self.is_mongodb_connected = False

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM agent_traces WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    # 3. Investigation Reports
    def save_investigation_report(self, report_id: str, report_data: Dict[str, Any]):
        now = datetime.now(timezone.utc).isoformat()
        clean_data = self._sanitize_record(report_data)
        title = clean_data.get("title", f"Investigation {report_id}")

        if self.is_mongodb_connected and self.db is not None:
            try:
                self.db.reports.update_one(
                    {"report_id": report_id},
                    {"$set": {**clean_data, "created_at": now}},
                    upsert=True
                )
                return
            except Exception:
                self.is_mongodb_connected = False

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO investigation_reports (report_id, title, created_at, data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET data=excluded.data
            """, (report_id, title, now, json.dumps(clean_data)))
            conn.commit()

    def list_investigation_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.is_mongodb_connected and self.db is not None:
            try:
                docs = list(self.db.reports.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
                if docs:
                    return docs
            except Exception:
                self.is_mongodb_connected = False

        results = []
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM investigation_reports ORDER BY created_at DESC LIMIT ?", (limit,))
            for row in cursor.fetchall():
                results.append(json.loads(row[0]))
        return results

    # 4. QA Test Execution History
    def save_test_record(self, record: Dict[str, Any]):
        clean = self._sanitize_record(record)
        test_id = clean.get("test_id", f"TEST_{datetime.now().timestamp()}")
        tab = clean.get("tab", "COMPONENT")
        comp = clean.get("component", "unknown")
        status = clean.get("status", "UNVERIFIED")
        dur = float(clean.get("execution_duration_ms", 0.0))
        ts = clean.get("timestamp") or datetime.now(timezone.utc).isoformat()

        if self.is_mongodb_connected and self.db is not None:
            try:
                self.db.qa_test_history.update_one(
                    {"test_id": test_id},
                    {"$set": clean},
                    upsert=True
                )
                return
            except Exception:
                self.is_mongodb_connected = False

        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO test_history (test_id, tab, component, status, duration_ms, timestamp, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(test_id) DO UPDATE SET data=excluded.data, status=excluded.status
            """, (test_id, tab, comp, status, dur, ts, json.dumps(clean)))
            conn.commit()

    def list_test_records(self, tab: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if self.is_mongodb_connected and self.db is not None:
            try:
                query = {"tab": tab} if tab else {}
                docs = list(self.db.qa_test_history.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit))
                if docs:
                    return docs
            except Exception:
                self.is_mongodb_connected = False

        results = []
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()
            if tab:
                cursor.execute("SELECT data FROM test_history WHERE tab = ? ORDER BY timestamp DESC LIMIT ?", (tab, limit))
            else:
                cursor.execute("SELECT data FROM test_history ORDER BY timestamp DESC LIMIT ?", (limit,))
            for row in cursor.fetchall():
                results.append(json.loads(row[0]))
        return results

    @staticmethod
    def _sanitize_record(data: Any) -> Any:
        """Strip API keys and credentials before storing."""
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in ["api_key", "secret", "password", "token", "auth"]):
                    sanitized[k] = "[REDACTED_CREDENTIAL]"
                else:
                    sanitized[k] = StorageService._sanitize_record(v)
            return sanitized
        elif isinstance(data, list):
            return [StorageService._sanitize_record(x) for x in data]
        return data


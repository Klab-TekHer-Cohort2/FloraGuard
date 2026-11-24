import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_channel TEXT NOT NULL CHECK(input_channel IN ('SMARTPHONE', 'USSD', 'IVR')),
    image_path TEXT,
    ai_status TEXT NOT NULL,
    predicted_problem TEXT,
    reported_problem TEXT,
    severity TEXT NOT NULL,
    confidence REAL,
    latitude REAL,
    longitude REAL,
    area TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    weather_status TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    weather_timestamp TEXT,
    risk_level TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_reasons TEXT NOT NULL,
    alert_generated INTEGER NOT NULL DEFAULT 0,
    is_sample INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_reports_area_timestamp
    ON reports(area, timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_problem_timestamp
    ON reports(predicted_problem, reported_problem, timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_channel
    ON reports(input_channel);

CREATE TABLE IF NOT EXISTS weather_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    observed_at TEXT,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    risk_level TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    reasons TEXT NOT NULL,
    calculated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    problem TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    area TEXT NOT NULL,
    reason TEXT NOT NULL,
    guidance TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivery_channels TEXT NOT NULL,
    delivery_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_area_created
    ON alerts(area, created_at);

CREATE TABLE IF NOT EXISTS ivr_sessions (
    session_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    selected_problem TEXT,
    selected_severity TEXT,
    selected_area TEXT,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.session() as connection:
            connection.executescript(SCHEMA)

    def health(self) -> bool:
        with self.session() as connection:
            connection.execute("SELECT 1").fetchone()
        return True

    def save_report(
        self,
        report: dict[str, Any],
        weather: dict[str, Any],
        risk: dict[str, Any],
        alert: dict[str, Any] | None,
    ) -> dict[str, Any]:
        with self.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reports (
                    input_channel, image_path, ai_status, predicted_problem, reported_problem,
                    severity, confidence, latitude, longitude, area, timestamp,
                    weather_status, temperature, humidity, weather_timestamp,
                    risk_level, risk_score, risk_reasons, alert_generated, is_sample
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report["input_channel"],
                    report.get("image_path"),
                    report["ai_status"],
                    report.get("predicted_problem"),
                    report.get("reported_problem"),
                    report["severity"],
                    report.get("confidence"),
                    report.get("latitude"),
                    report.get("longitude"),
                    report["area"],
                    report["timestamp"],
                    weather["status"],
                    weather.get("temperature"),
                    weather.get("humidity"),
                    weather.get("observed_at"),
                    risk["risk_level"],
                    risk["risk_score"],
                    json.dumps(risk["reasons"]),
                    int(alert is not None),
                    int(report.get("is_sample", False)),
                ),
            )
            report_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO weather_observations
                    (report_id, status, temperature, humidity, observed_at, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    weather["status"],
                    weather.get("temperature"),
                    weather.get("humidity"),
                    weather.get("observed_at"),
                    weather.get("source", "open-meteo"),
                ),
            )
            connection.execute(
                """
                INSERT INTO risk_results (report_id, risk_level, risk_score, reasons, calculated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    risk["risk_level"],
                    risk["risk_score"],
                    json.dumps(risk["reasons"]),
                    risk["calculated_at"],
                ),
            )
            if alert:
                connection.execute(
                    """
                    INSERT INTO alerts (
                        report_id, problem, risk_level, area, reason, guidance,
                        created_at, delivery_channels, delivery_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        alert["problem"],
                        alert["risk_level"],
                        alert["area"],
                        alert["reason"],
                        alert["guidance"],
                        alert["created_at"],
                        json.dumps(alert["delivery_channels"]),
                        alert["delivery_status"],
                    ),
                )
        return self.get_report(report_id)

    def get_report(self, report_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        return self._report_dict(row) if row else None

    def list_reports(
        self,
        area: str | None = None,
        input_channel: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if area:
            clauses.append("area = ?")
            parameters.append(area)
        if input_channel:
            clauses.append("input_channel = ?")
            parameters.append(input_channel)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(limit)
        with self.session() as connection:
            rows = connection.execute(
                f"SELECT * FROM reports {where} ORDER BY timestamp DESC, id DESC LIMIT ?",
                parameters,
            ).fetchall()
        return [self._report_dict(row) for row in rows]

    def recent_reports(self, area: str | None, since: str) -> list[dict[str, Any]]:
        query = "SELECT * FROM reports WHERE timestamp >= ?"
        parameters: list[Any] = [since]
        if area:
            query += " AND area = ?"
            parameters.append(area)
        query += " ORDER BY timestamp DESC, id DESC LIMIT 5000"
        with self.session() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()
        return [self._report_dict(row) for row in rows]

    def list_alerts(self, area: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = """
            SELECT id, report_id, problem, risk_level, area, reason, guidance,
                   created_at, delivery_channels, delivery_status
            FROM alerts
        """
        parameters: list[Any] = []
        if area:
            query += " WHERE area = ?"
            parameters.append(area)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        parameters.append(limit)
        with self.session() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._alert_dict(row) for row in rows]

    def get_ivr_session(self, session_id: str) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM ivr_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def save_ivr_session(self, session: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO ivr_sessions
                    (session_id, state, selected_problem, selected_severity, selected_area, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state = excluded.state,
                    selected_problem = excluded.selected_problem,
                    selected_severity = excluded.selected_severity,
                    selected_area = excluded.selected_area,
                    updated_at = excluded.updated_at
                """,
                (
                    session["session_id"],
                    session["state"],
                    session.get("selected_problem"),
                    session.get("selected_severity"),
                    session.get("selected_area"),
                    session["updated_at"],
                ),
            )

    @staticmethod
    def _report_dict(row: sqlite3.Row) -> dict[str, Any]:
        report = dict(row)
        report["risk_reasons"] = json.loads(report["risk_reasons"])
        report["alert_generated"] = bool(report["alert_generated"])
        report["is_sample"] = bool(report["is_sample"])
        report["image_available"] = bool(report["image_path"])
        report["problem"] = report["reported_problem"] or report["predicted_problem"]
        report["image_url"] = (
            f"/uploads/{Path(report['image_path']).name}" if report["image_path"] else None
        )
        return report

    @staticmethod
    def _alert_dict(row: sqlite3.Row) -> dict[str, Any]:
        alert = dict(row)
        alert["delivery_channels"] = json.loads(alert["delivery_channels"])
        return alert

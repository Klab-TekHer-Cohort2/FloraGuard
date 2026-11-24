from datetime import timedelta

from .config import Settings
from .database import Database
from .risk_engine import RiskEngine
from .services import ReportService, utc_now


SAMPLE_REPORTS = [
    ("SAMPLE - Low Risk", "USSD", "spider_mite", "low", 1),
    ("SAMPLE - Low Risk", "IVR", "thrips", "low", 2),
    ("SAMPLE - Medium Risk", "SMARTPHONE", "powdery_mildew", "medium", 1),
    ("SAMPLE - Medium Risk", "USSD", "powdery_mildew", "medium", 2),
    ("SAMPLE - Medium Risk", "IVR", "powdery_mildew", "medium", 4),
    ("SAMPLE - High Risk", "SMARTPHONE", "spider_mite", "high", 0),
    ("SAMPLE - High Risk", "USSD", "spider_mite", "high", 1),
    ("SAMPLE - High Risk", "IVR", "spider_mite", "high", 2),
    ("SAMPLE - High Risk", "SMARTPHONE", "spider_mite", "high", 3),
    ("SAMPLE - High Risk", "USSD", "spider_mite", "high", 5),
    ("SAMPLE - Medium Risk", "IVR", "grey_mould", "high", 6),
]


def seed_demo(database: Database) -> int:
    database.initialize()
    existing_samples = [
        report for report in database.list_reports(limit=5000) if report["is_sample"]
    ]
    if existing_samples:
        return 0

    settings = Settings.from_env()
    risk_engine = RiskEngine(
        window_days=settings.risk_window_days,
        radius_km=settings.risk_radius_km,
        medium_threshold=settings.risk_medium_threshold,
        high_threshold=settings.risk_high_threshold,
    )
    saved = 0
    for area, channel, problem, severity, days_ago in SAMPLE_REPORTS:
        timestamp = (utc_now() - timedelta(days=days_ago)).isoformat()
        current = {
            "input_channel": channel,
            "image_path": None,
            "ai_status": "sample_data",
            "predicted_problem": problem if channel == "SMARTPHONE" else None,
            "reported_problem": problem if channel != "SMARTPHONE" else None,
            "severity": severity,
            "confidence": None,
            "latitude": None,
            "longitude": None,
            "area": area,
            "timestamp": timestamp,
            "is_sample": True,
        }
        recent = database.recent_reports(
            area,
            (utc_now() - timedelta(days=settings.risk_window_days)).isoformat(),
        )
        weather = {
            "status": "unavailable",
            "temperature": None,
            "humidity": None,
            "observed_at": None,
            "source": "not used for synthetic sample data",
        }
        risk = risk_engine.evaluate(current, [*recent, current], weather)
        alert = ReportService._make_alert(current, problem, risk)
        database.save_report(current, weather, risk, alert)
        saved += 1
    return saved


def main() -> None:
    settings = Settings.from_env()
    database = Database(settings.database_path)
    count = seed_demo(database)
    if count:
        print(f"Seeded {count} synthetic reports. SAMPLE DATA only; not real farm records.")
    else:
        print("Sample reports already exist; no changes made.")


if __name__ == "__main__":
    main()

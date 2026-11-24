import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .database import Database
from .predictor import PredictionError, Predictor
from .risk_engine import RiskEngine
from .weather import OpenMeteoWeather

logger = logging.getLogger("floraguard.reports")

OBSERVATION_PROBLEMS = {
    "healthy",
    "spider_mite",
    "thrips",
    "powdery_mildew",
    "downy_mildew",
    "grey_mould",
    "black_spot",
    "uncertain",
}
OBSERVATION_SEVERITIES = {"low", "medium", "high", "unknown"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_string(value: str | None) -> str:
    if value is None:
        return utc_now().isoformat()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


class ReportService:
    def __init__(
        self,
        database: Database,
        settings: Settings,
        predictor: Predictor,
        weather: OpenMeteoWeather,
    ):
        self.database = database
        self.settings = settings
        self.predictor = predictor
        self.weather = weather
        self.risk_engine = RiskEngine(
            window_days=settings.risk_window_days,
            radius_km=settings.risk_radius_km,
            medium_threshold=settings.risk_medium_threshold,
            high_threshold=settings.risk_high_threshold,
        )

    def create_smartphone_report(
        self,
        image_path: Path,
        latitude: float | None,
        longitude: float | None,
        area: str | None,
        timestamp: str | None,
    ) -> dict[str, Any]:
        try:
            prediction = self.predictor.predict_image(image_path)
        except PredictionError:
            prediction = {
                "problem": "uncertain",
                "severity": "unknown",
                "confidence": None,
                "model_status": "unavailable",
            }
        return self._create(
            input_channel="SMARTPHONE",
            image_path=str(image_path),
            ai_status=prediction["model_status"],
            predicted_problem=prediction["problem"],
            reported_problem=None,
            severity=prediction["severity"],
            confidence=prediction["confidence"],
            latitude=latitude,
            longitude=longitude,
            area=area,
            timestamp=timestamp,
        )

    def create_observation(
        self,
        input_channel: str,
        problem: str,
        severity: str,
        area: str,
        latitude: float | None = None,
        longitude: float | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        problem = problem.strip().lower()
        severity = severity.strip().lower()
        if problem not in OBSERVATION_PROBLEMS:
            raise ValueError(f"Unsupported observed problem: {problem}.")
        if severity not in OBSERVATION_SEVERITIES:
            raise ValueError(f"Unsupported reported severity: {severity}.")
        self.validate_area(area)
        return self._create(
            input_channel=input_channel,
            image_path=None,
            ai_status="not_applicable",
            predicted_problem=None,
            reported_problem=problem,
            severity=severity,
            confidence=None,
            latitude=latitude,
            longitude=longitude,
            area=area,
            timestamp=timestamp,
        )

    def validate_area(self, area: str) -> None:
        if area not in self.settings.areas:
            raise ValueError("Area is not in the configured area list.")

    def _create(
        self,
        input_channel: str,
        image_path: str | None,
        ai_status: str,
        predicted_problem: str | None,
        reported_problem: str | None,
        severity: str,
        confidence: float | None,
        latitude: float | None,
        longitude: float | None,
        area: str | None,
        timestamp: str | None,
    ) -> dict[str, Any]:
        resolved_area = area or (
            "GPS-reported area"
            if latitude is not None and longitude is not None
            else self.settings.areas[0]
            if self.settings.areas
            else "Unspecified area"
        )
        if input_channel in {"USSD", "IVR"}:
            self.validate_area(resolved_area)
        recorded_at = timestamp_string(timestamp)
        current = {
            "input_channel": input_channel,
            "image_path": image_path,
            "ai_status": ai_status,
            "predicted_problem": predicted_problem,
            "reported_problem": reported_problem,
            "severity": severity,
            "confidence": confidence,
            "latitude": latitude,
            "longitude": longitude,
            "area": resolved_area,
            "timestamp": recorded_at,
            "is_sample": False,
        }

        weather_latitude, weather_longitude = latitude, longitude
        if weather_latitude is None or weather_longitude is None:
            configured_coords = self.settings.coordinates_for_area(resolved_area)
            if configured_coords:
                weather_latitude, weather_longitude = configured_coords
        try:
            weather_data = self.weather.current(weather_latitude, weather_longitude)
        except Exception:
            logger.exception("Weather lookup failed; report processing will continue without weather.")
            weather_data = {
                "status": "unavailable",
                "temperature": None,
                "humidity": None,
                "observed_at": None,
                "source": "Open-Meteo",
            }

        cutoff = (utc_now() - timedelta(days=self.settings.risk_window_days)).isoformat()
        recent = self.database.recent_reports(None, cutoff)
        risk = self.risk_engine.evaluate(current, [*recent, current], weather_data)
        problem = reported_problem or predicted_problem or "uncertain"
        alert = self._make_alert(current, problem, risk)
        try:
            return self.database.save_report(current, weather_data, risk, alert)
        except Exception:
            if image_path:
                try:
                    Path(image_path).unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    logger.exception("Unable to remove an unreferenced report image.")
            raise

    def area_risk(self, area: str, problem: str | None = None) -> dict[str, Any]:
        self.validate_area(area)
        cutoff = (utc_now() - timedelta(days=self.settings.risk_window_days)).isoformat()
        recent = self.database.recent_reports(area, cutoff)
        known_problems = [
            report.get("reported_problem") or report.get("predicted_problem")
            for report in recent
        ]
        known_problems = [
            value for value in known_problems if value and value not in {"healthy", "uncertain"}
        ]
        selected_problem = problem or (
            max(set(known_problems), key=known_problems.count)
            if known_problems
            else "uncertain"
        )
        current = {
            "input_channel": "AREA_SUMMARY",
            "area": area,
            "timestamp": utc_now().isoformat(),
            "reported_problem": selected_problem,
            "predicted_problem": None,
            "severity": "unknown",
        }
        coordinates = self.settings.coordinates_for_area(area)
        try:
            weather = (
                self.weather.current(*coordinates)
                if coordinates
                else {"status": "unavailable", "temperature": None, "humidity": None}
            )
        except Exception:
            logger.exception("Area risk weather lookup failed; continuing without weather.")
            weather = {"status": "unavailable", "temperature": None, "humidity": None}
        result = self.risk_engine.evaluate(current, recent, weather)
        return {
            **result,
            "area": area,
            "problem": selected_problem if selected_problem != "uncertain" else None,
            "report_count": len(recent),
            "weather_status": weather["status"],
            "temperature": weather.get("temperature"),
            "humidity": weather.get("humidity"),
        }

    @staticmethod
    def _make_alert(
        report: dict[str, Any], problem: str, risk: dict[str, Any]
    ) -> dict[str, Any] | None:
        if risk["risk_level"] != "HIGH":
            return None
        reason = " ".join(risk["reasons"])
        return {
            "problem": problem,
            "risk_level": "HIGH",
            "area": report["area"],
            "reason": reason,
            "guidance": (
                f"{problem.replace('_', ' ').capitalize()} risk is high in {report['area']}. "
                "Inspect rose plants carefully and contact a local agronomist for serious cases."
            ),
            "created_at": utc_now().isoformat(),
            "delivery_channels": ["smartphone_api", "ussd", "ivr"],
            "delivery_status": "available",
        }

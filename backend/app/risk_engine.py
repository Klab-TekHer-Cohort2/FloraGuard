import math
from datetime import datetime, timedelta, timezone
from typing import Any


DISEASES_FAVOURED_BY_HUMIDITY = {
    "powdery_mildew",
    "downy_mildew",
    "grey_mould",
    "black_spot",
}
PESTS_FAVOURED_BY_WARM_DRY_WEATHER = {"spider_mite", "thrips"}
SEVERITY_POINTS = {"low": 2, "medium": 6, "high": 10}


def _as_datetime(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius = 6371.0
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(min(1.0, math.sqrt(value)))


class RiskEngine:
    """Transparent prototype rules; this score is not a validated forecast."""

    def __init__(
        self,
        window_days: int = 7,
        radius_km: float = 5,
        medium_threshold: int = 30,
        high_threshold: int = 65,
    ):
        self.window_days = window_days
        self.radius_km = radius_km
        if not 0 <= medium_threshold < high_threshold <= 100:
            raise ValueError("Risk score thresholds must satisfy 0 <= medium < high <= 100.")
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold

    def evaluate(
        self,
        current: dict[str, Any],
        recent_reports: list[dict[str, Any]],
        weather: dict[str, Any],
    ) -> dict[str, Any]:
        now = _as_datetime(current["timestamp"])
        cutoff = now - timedelta(days=self.window_days)
        problem = current.get("reported_problem") or current.get("predicted_problem")
        relevant: list[dict[str, Any]] = []
        for report in recent_reports:
            report_problem = report.get("reported_problem") or report.get("predicted_problem")
            if not problem or problem == "uncertain" or report_problem != problem:
                continue
            if report_problem == "healthy":
                continue
            try:
                if _as_datetime(report["timestamp"]) < cutoff:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            if not self._nearby_or_same_area(current, report):
                continue
            relevant.append(report)

        score = 0
        reasons: list[str] = []
        count = len(relevant)
        if count >= 5:
            score += 45
            reasons.append(f"{count} similar reports were recorded within the last {self.window_days} days.")
        elif count >= 3:
            score += 30
            reasons.append(f"{count} similar reports were recorded within the last {self.window_days} days.")
        elif count >= 2:
            score += 18
            reasons.append(f"{count} similar reports were recorded within the last {self.window_days} days.")

        severity_score = min(
            20,
            sum(SEVERITY_POINTS.get(str(report.get("severity", "")).lower(), 0) for report in relevant),
        )
        if severity_score:
            score += severity_score
            reasons.append("Reported case severity contributes to the area risk.")

        nearby_count = sum(
            1
            for report in relevant
            if self._has_coordinates(current)
            and self._has_coordinates(report)
            and haversine_km(
                current["latitude"],
                current["longitude"],
                report["latitude"],
                report["longitude"],
            ) <= self.radius_km
        )
        if nearby_count >= 2:
            score += 10
            reasons.append(f"Several similar reports are within {self.radius_km:g} km.")

        temperature = weather.get("temperature")
        humidity = weather.get("humidity")
        if problem in DISEASES_FAVOURED_BY_HUMIDITY and humidity is not None and humidity >= 80:
            score += 15
            reasons.append("Recent high humidity may favour this disease.")
        elif (
            problem in PESTS_FAVOURED_BY_WARM_DRY_WEATHER
            and temperature is not None
            and humidity is not None
            and temperature >= 25
            and humidity <= 55
        ):
            score += 15
            reasons.append("Recent warm, dry conditions may favour this pest.")

        score = min(100, score)
        level = (
            "HIGH"
            if score >= self.high_threshold
            else "MEDIUM"
            if score >= self.medium_threshold
            else "LOW"
        )
        if not reasons:
            reasons.append("No recent concentration of similar reports was found.")
        return {
            "risk_level": level,
            "risk_score": score,
            "reasons": reasons,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "window_days": self.window_days,
            "prototype_notice": "Prototype rule-based indicator; not a scientifically validated prediction.",
        }

    def _nearby_or_same_area(self, current: dict[str, Any], report: dict[str, Any]) -> bool:
        if self._has_coordinates(current) and self._has_coordinates(report):
            return (
                haversine_km(
                    current["latitude"],
                    current["longitude"],
                    report["latitude"],
                    report["longitude"],
                )
                <= self.radius_km
            )
        return bool(current.get("area") and current.get("area") == report.get("area"))

    @staticmethod
    def _has_coordinates(report: dict[str, Any]) -> bool:
        return report.get("latitude") is not None and report.get("longitude") is not None

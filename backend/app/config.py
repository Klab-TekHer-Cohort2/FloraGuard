import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _area_coordinates(value: str) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    for item in value.split(";"):
        if not item.strip():
            continue
        try:
            name, coords = item.split(":", 1)
            latitude, longitude = (float(part.strip()) for part in coords.split(",", 1))
        except ValueError as exc:
            raise ValueError(
                "FLORAGUARD_AREA_COORDINATES must use 'Area:latitude,longitude' entries."
            ) from exc
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"Invalid coordinates configured for area {name.strip()!r}.")
        result[name.strip()] = (latitude, longitude)
    return result


@dataclass(frozen=True)
class Settings:
    database_path: Path
    upload_dir: Path
    areas: tuple[str, ...]
    area_coordinates: dict[str, tuple[float, float]]
    ussd_code: str
    confidence_threshold: float
    risk_window_days: int
    risk_radius_km: float
    risk_medium_threshold: int
    risk_high_threshold: int
    max_image_size_bytes: int
    weather_timeout_seconds: float
    predictor_path: str | None
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        database_path = Path(
            os.getenv("FLORAGUARD_DATABASE_PATH", "backend/data/floraguard.db")
        )
        upload_dir = Path(
            os.getenv("FLORAGUARD_UPLOAD_DIR", "backend/data/uploads")
        )
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        if not upload_dir.is_absolute():
            upload_dir = PROJECT_ROOT / upload_dir

        areas = tuple(
            name.strip()
            for name in os.getenv(
                "FLORAGUARD_AREAS", "Gishari Flower Park"
            ).split(",")
            if name.strip()
        )
        threshold = float(os.getenv("FLORAGUARD_CONFIDENCE_THRESHOLD", "0.60"))
        if not 0 <= threshold <= 1:
            raise ValueError("FLORAGUARD_CONFIDENCE_THRESHOLD must be between 0 and 1.")
        medium_threshold = int(os.getenv("FLORAGUARD_RISK_MEDIUM_THRESHOLD", "30"))
        high_threshold = int(os.getenv("FLORAGUARD_RISK_HIGH_THRESHOLD", "65"))
        if not 0 <= medium_threshold < high_threshold <= 100:
            raise ValueError(
                "Risk score thresholds must satisfy 0 <= medium < high <= 100."
            )

        return cls(
            database_path=database_path,
            upload_dir=upload_dir,
            areas=areas,
            area_coordinates=_area_coordinates(
                os.getenv("FLORAGUARD_AREA_COORDINATES", "")
            ),
            ussd_code=os.getenv("FLORAGUARD_USSD_CODE", "*XXX#"),
            confidence_threshold=threshold,
            risk_window_days=max(1, int(os.getenv("FLORAGUARD_RISK_WINDOW_DAYS", "7"))),
            risk_radius_km=max(0.1, float(os.getenv("FLORAGUARD_RISK_RADIUS_KM", "5"))),
            risk_medium_threshold=medium_threshold,
            risk_high_threshold=high_threshold,
            max_image_size_bytes=max(
                1, int(os.getenv("FLORAGUARD_MAX_IMAGE_SIZE_MB", "10"))
            )
            * 1024
            * 1024,
            weather_timeout_seconds=max(
                0.1, float(os.getenv("FLORAGUARD_WEATHER_TIMEOUT_SECONDS", "4"))
            ),
            predictor_path=os.getenv("FLORAGUARD_PREDICTOR") or None,
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "FLORAGUARD_CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173",
                ).split(",")
                if origin.strip()
            ),
        )

    def coordinates_for_area(self, area: str | None) -> tuple[float, float] | None:
        if not area:
            return None
        return self.area_coordinates.get(area)

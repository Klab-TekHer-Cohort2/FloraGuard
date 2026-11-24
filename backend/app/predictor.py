import importlib
import logging
import math
from pathlib import Path
from typing import Any, Callable

from .config import Settings

logger = logging.getLogger("floraguard.predictor")

SUPPORTED_PROBLEMS = {
    "healthy",
    "spider_mite",
    "thrips",
    "powdery_mildew",
    "downy_mildew",
    "grey_mould",
    "black_spot",
    "uncertain",
}
SUPPORTED_SEVERITIES = {"low", "medium", "high", "unknown"}


class PredictionError(ValueError):
    pass


def _load_callable(import_path: str) -> Callable[[str], dict[str, Any]]:
    try:
        module_name, function_name = import_path.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
    except (ValueError, ImportError, AttributeError) as exc:
        raise PredictionError(
            "Could not load the configured predictor. Check FLORAGUARD_PREDICTOR."
        ) from exc
    if not callable(function):
        raise PredictionError("The configured predictor is not callable.")
    return function


class Predictor:
    """Adapter for Member 1's predict_image(path) integration point."""

    def __init__(self, settings: Settings, predict_function=None):
        self.threshold = settings.confidence_threshold
        self._predict_function = predict_function
        self._load_error: str | None = None
        if self._predict_function is None and settings.predictor_path:
            try:
                self._predict_function = _load_callable(settings.predictor_path)
            except PredictionError as exc:
                self._load_error = str(exc)
                logger.exception("FloraGuard image predictor could not be loaded.")

    @property
    def available(self) -> bool:
        return self._predict_function is not None

    def predict_image(self, image_path: str | Path) -> dict[str, Any]:
        if self._predict_function is None:
            reason = self._load_error or "No image model is configured."
            logger.warning("Image analysis unavailable: %s", reason)
            return {
                "problem": "uncertain",
                "severity": "unknown",
                "confidence": None,
                "model_status": "unavailable",
            }
        try:
            raw = self._predict_function(str(image_path))
            return self.normalize(raw)
        except Exception as exc:
            logger.exception("Member 1 image predictor failed.")
            raise PredictionError("Image analysis is unavailable.") from exc

    def normalize(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise PredictionError("Predictor must return a dictionary.")

        problem = str(raw.get("problem", "uncertain")).strip().lower()
        severity = str(raw.get("severity", "unknown")).strip().lower()
        confidence = raw.get("confidence")
        if problem not in SUPPORTED_PROBLEMS:
            raise PredictionError(f"Unsupported predicted problem: {problem}.")
        if severity not in SUPPORTED_SEVERITIES:
            raise PredictionError(f"Unsupported predicted severity: {severity}.")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise PredictionError("Prediction confidence must be a number or null.")
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise PredictionError("Prediction confidence must be between 0 and 1.")
            confidence = float(confidence)
            if confidence < self.threshold:
                problem = "uncertain"
                severity = "unknown"

        return {
            "problem": problem,
            "severity": severity,
            "confidence": confidence,
            "model_status": "available",
        }

import importlib
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings


class ImagePredictor(Protocol):
    def predict_image(self, image_path: str) -> Any:
        """Return problem, severity, and confidence for an image."""


class MockPredictor:
    """Deterministic stand-in used until Member 1's model is connected."""

    source = "mock"

    def predict_image(self, image_path: str) -> dict[str, Any]:
        if not Path(image_path).is_file():
            raise FileNotFoundError(f"Image does not exist: {image_path}")
        return {
            "problem": "spider_mite",
            "severity": "medium",
            "confidence": 0.87,
        }


class ModulePredictor:
    def __init__(self, module_name: str, function_name: str):
        module = importlib.import_module(module_name)
        function = getattr(module, function_name, None)
        if not callable(function):
            raise TypeError(
                f"{module_name}.{function_name} must be a callable prediction function"
            )
        self._function = function
        self.module_name = module_name
        self.source = f"model:{module_name}"

    def predict_image(self, image_path: str) -> Any:
        result = self._function(image_path)
        if isinstance(result, dict):
            version = result.get("model_version")
            if isinstance(version, str) and version:
                self.source = f"model:{self.module_name}:version:{version}"
        return result


def create_predictor(settings: Settings) -> ImagePredictor:
    if settings.ai_predictor_module:
        return ModulePredictor(
            settings.ai_predictor_module,
            settings.ai_predictor_function,
        )
    return MockPredictor()

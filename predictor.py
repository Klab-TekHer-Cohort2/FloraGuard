import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from dataset_tools import CLASS_NAMES
from severity import estimate_severity


PROJECT_DIR = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_DIR / "models"
IMAGE_SIZE = (224, 224)
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _resolve_model_bundle() -> tuple[Path, dict[str, Any]]:
    configured_path = os.getenv("FLORAGUARD_MODEL_PATH")
    if configured_path:
        model_path = Path(configured_path).expanduser()
        if not model_path.is_absolute():
            model_path = PROJECT_DIR / model_path
        metadata_path = model_path.with_name(f"{model_path.stem}_metadata.json")
        legacy_labels_path = MODEL_DIR / "labels.json"
        if metadata_path.is_file():
            manifest_path = metadata_path
        elif model_path.name == "rose_classifier.keras" and legacy_labels_path.is_file():
            manifest_path = legacy_labels_path
        else:
            raise FileNotFoundError(
                f"Model metadata not found beside {model_path}: {metadata_path}"
            )
    else:
        active_path = MODEL_DIR / "active_model.json"
        if active_path.is_file():
            active = json.loads(active_path.read_text(encoding="utf-8"))
            model_path = _path_from_pointer(active["model_file"])
            manifest_path = _path_from_pointer(active["metadata_file"])
        else:
            model_path = MODEL_DIR / "rose_classifier.keras"
            manifest_path = MODEL_DIR / "labels.json"
            if not model_path.is_file() or not manifest_path.is_file():
                raise FileNotFoundError(
                    "No active trained model was found. Train a versioned model "
                    "and activate it with `train_model.py --activate`, or set "
                    "FLORAGUARD_MODEL_PATH."
                )

    if not model_path.is_file():
        raise FileNotFoundError(f"Trained model file not found: {model_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Model metadata file not found: {manifest_path}")
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    class_names = metadata.get("class_names")
    if class_names != list(CLASS_NAMES):
        raise ValueError(
            "Model metadata class_names must match the FloraGuard class order: "
            + ", ".join(CLASS_NAMES)
        )
    return model_path.resolve(), metadata


def _path_from_pointer(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if "/" in value or "\\" in value:
        return PROJECT_DIR / path
    return MODEL_DIR / path


@lru_cache(maxsize=2)
def _load_model(model_path: str):
    try:
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError(
            "TensorFlow is required for model inference. Install the AI "
            "requirements before enabling the trained predictor."
        ) from error
    return tf.keras.models.load_model(model_path)


def _model_input(image: Image.Image):
    try:
        import tensorflow as tf
    except ImportError:
        return [
            [
                [list(image.getpixel((x, y))) for x in range(image.width)]
                for y in range(image.height)
            ]
        ]
    image_array = tf.keras.utils.img_to_array(image, dtype="float32")
    return tf.expand_dims(image_array, axis=0)


def _load_image(photo_path: str | Path) -> Image.Image:
    path = Path(photo_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image does not exist: {path}")
    try:
        with Image.open(path) as source:
            if source.format not in SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported image format {source.format!r}; "
                    "use JPEG, PNG, or WebP."
                )
            source.verify()
        with Image.open(path) as source:
            return ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError(f"Invalid or corrupted image: {path}") from error
    except ValueError as error:
        if str(error).startswith("Unsupported image format"):
            raise
        raise ValueError(f"Invalid or corrupted image: {path}") from error


def predict_rose_problem(
    photo_path: str | Path,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    threshold_value = (
        os.getenv("CONFIDENCE_THRESHOLD", "0.60")
        if confidence_threshold is None
        else confidence_threshold
    )
    try:
        threshold = float(threshold_value)
    except (TypeError, ValueError) as error:
        raise ValueError("confidence_threshold must be a number from 0 to 1") from error
    if not 0 <= threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")

    image = _load_image(photo_path)
    model_path, metadata = _resolve_model_bundle()
    image_size = tuple(metadata.get("image_size", IMAGE_SIZE))
    if (
        len(image_size) != 2
        or not all(isinstance(value, int) and value > 0 for value in image_size)
    ):
        raise ValueError("Model metadata has an invalid image_size")
    prepared = image.resize(
        (image_size[1], image_size[0]),
        Image.Resampling.BILINEAR,
    )
    model = _load_model(str(model_path))
    batch = _model_input(prepared)
    scores = model.predict(batch, verbose=0)
    if hasattr(scores, "tolist"):
        scores = scores.tolist()
    if (
        not isinstance(scores, (list, tuple))
        or len(scores) != 1
        or not isinstance(scores[0], (list, tuple))
        or len(scores[0]) != len(CLASS_NAMES)
    ):
        raise ValueError(
            f"Model returned invalid output shape; expected (1, {len(CLASS_NAMES)})"
        )
    try:
        probabilities = [float(value) for value in scores[0]]
    except (TypeError, ValueError) as error:
        raise ValueError("Model returned non-numeric class probabilities") from error
    if (
        not all(math.isfinite(value) for value in probabilities)
        or any(value < 0 or value > 1 for value in probabilities)
        or not math.isclose(sum(probabilities), 1.0, abs_tol=1e-3)
    ):
        raise ValueError("Model returned invalid class probabilities")

    best_index = max(range(len(probabilities)), key=probabilities.__getitem__)
    confidence = float(probabilities[best_index])
    candidate = CLASS_NAMES[best_index]
    uncertain = confidence < threshold
    problem = "uncertain" if uncertain else candidate
    severity_result = estimate_severity(image, problem)
    return {
        "problem": problem,
        "top_candidate": candidate,
        "severity": (
            "unknown" if uncertain else severity_result["severity"]
        ),
        "severity_source": (
            "unavailable" if uncertain else severity_result["severity_source"]
        ),
        "visible_damage_fraction": (
            0.0 if uncertain else severity_result["visible_damage_fraction"]
        ),
        "confidence": round(confidence, 4),
        "class_probabilities": {
            class_name: round(probability, 6)
            for class_name, probability in zip(CLASS_NAMES, probabilities)
        },
        "uncertain": uncertain,
        "model_version": metadata.get("model_version", "legacy"),
    }


def predict_image(image_path: str | Path) -> dict[str, Any]:
    """Backend-compatible prediction entry point for a validated local image."""
    result = predict_rose_problem(image_path)
    return {
        "problem": result["problem"],
        "severity": result["severity"],
        "confidence": result["confidence"],
        "candidate_problem": (
            result["top_candidate"] if result["uncertain"] else None
        ),
        "model_version": result["model_version"],
    }

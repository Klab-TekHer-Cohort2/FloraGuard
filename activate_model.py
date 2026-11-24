import argparse
import json
from pathlib import Path

from dataset_tools import CLASS_NAMES


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_DIR = PROJECT_DIR / "models"


def _pointer_value(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(PROJECT_DIR):
        return resolved.relative_to(PROJECT_DIR).as_posix()
    return str(resolved)


def activate_model(model_path: Path, active_dir: Path | None = None) -> Path:
    model_path = model_path.expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    metadata_path = model_path.with_name(f"{model_path.stem}_metadata.json")
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Model metadata not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("class_names") != list(CLASS_NAMES):
        raise ValueError("Model metadata does not contain the FloraGuard class order")

    active_dir = (active_dir or DEFAULT_MODEL_DIR).resolve()
    active_dir.mkdir(parents=True, exist_ok=True)
    active_path = active_dir / "active_model.json"
    temporary_path = active_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "model_file": _pointer_value(model_path),
                "metadata_file": _pointer_value(metadata_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary_path.replace(active_path)
    return active_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select an existing, reviewed model version without retraining."
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to a versioned .keras model file",
    )
    args = parser.parse_args()
    active_path = activate_model(args.model)
    print(f"Active model pointer updated: {active_path}")


if __name__ == "__main__":
    main()

import argparse
import sys
from pathlib import Path

from predictor import predict_image
from train_model import DEFAULT_DATA_DIR, read_split_manifest


def select_test_image(data_dir: Path, manifest_path: Path | None = None) -> Path:
    data_dir = data_dir.expanduser().resolve()
    manifest_path = (
        manifest_path.expanduser().resolve()
        if manifest_path is not None
        else data_dir / "split_manifest.csv"
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Test split manifest not found: {manifest_path}. Add and review "
            "real source images, then create the split with dataset_tools.py."
        )

    split_records = read_split_manifest(manifest_path, data_dir)
    test_records = split_records["test"]
    if not test_records:
        raise ValueError(f"No test images are listed in {manifest_path}.")
    return Path(test_records[0][0]).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the active model on the first real image in the test split."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    try:
        image_path = select_test_image(args.data_dir, args.manifest)
        prediction = predict_image(image_path)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Predictor test failed: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    print(f"Image: {image_path}")
    print(f"Problem: {prediction['problem']}")
    print(f"Confidence: {prediction['confidence']:.4f}")
    print(f"Severity: {prediction['severity']}")
    print(f"Model version: {prediction['model_version']}")


if __name__ == "__main__":
    main()

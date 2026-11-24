import csv
import json
import random
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

import dataset_tools
import predictor
import train_model
from activate_model import activate_model
from dataset_tools import CLASS_NAMES
from severity import estimate_severity


class FakeModel:
    def __init__(self, scores):
        self.scores = [scores]
        self.received_shape = None

    def predict(self, batch, verbose=0):
        self.received_shape = (
            len(batch),
            len(batch[0]),
            len(batch[0][0]),
            len(batch[0][0][0]),
        )
        return self.scores


def _rose_like_image(path: Path, seed: int) -> None:
    rng = random.Random(seed)
    pixels = [
        tuple(rng.randrange(40, 220) for _ in range(3))
        for _ in range(64 * 64)
    ]
    image = Image.new("RGB", (64, 64))
    image.putdata(pixels)
    image.save(path, format="PNG")


def _class_scores(class_name: str, confidence: float = 0.9) -> list[float]:
    scores = [0.0] * len(CLASS_NAMES)
    index = CLASS_NAMES.index(class_name)
    scores[index] = confidence
    remaining = (1 - confidence) / (len(CLASS_NAMES) - 1)
    for other in range(len(CLASS_NAMES)):
        if other != index:
            scores[other] = remaining
    return scores


def test_predictor_returns_contract_fields_and_model_version(tmp_path, monkeypatch):
    photo = tmp_path / "rose.png"
    Image.new("RGB", (80, 60), (30, 120, 35)).save(photo)
    model = FakeModel(_class_scores("spider_mite"))
    monkeypatch.setattr(
        predictor,
        "_resolve_model_bundle",
        lambda: (
            tmp_path / "floraguard_v1.keras",
            {
                "class_names": list(CLASS_NAMES),
                "image_size": [224, 224],
                "model_version": "v1",
            },
        ),
    )
    monkeypatch.setattr(predictor, "_load_model", lambda _path: model)

    detailed = predictor.predict_rose_problem(photo)
    result = predictor.predict_image(photo)

    assert set(result) == {
        "problem",
        "severity",
        "confidence",
        "candidate_problem",
        "model_version",
    }
    assert result["problem"] == "spider_mite"
    assert result["confidence"] == pytest.approx(0.9, abs=1e-4)
    assert result["severity"] in {"low", "medium", "high", "unknown"}
    assert result["candidate_problem"] is None
    assert result["model_version"] == "v1"
    assert set(detailed["class_probabilities"]) == set(CLASS_NAMES)
    assert sum(detailed["class_probabilities"].values()) == pytest.approx(1.0, abs=1e-5)
    assert model.received_shape == (1, 224, 224, 3)


def test_low_confidence_returns_uncertain_and_unknown_severity(tmp_path, monkeypatch):
    photo = tmp_path / "rose.png"
    Image.new("RGB", (80, 60), (30, 120, 35)).save(photo)
    monkeypatch.setattr(
        predictor,
        "_resolve_model_bundle",
        lambda: (
            tmp_path / "floraguard_v1.keras",
            {"class_names": list(CLASS_NAMES), "image_size": [224, 224]},
        ),
    )
    monkeypatch.setattr(
        predictor,
        "_load_model",
        lambda _path: FakeModel(_class_scores("thrips", 0.42)),
    )

    result = predictor.predict_rose_problem(photo, confidence_threshold=0.60)

    assert result["problem"] == "uncertain"
    assert result["top_candidate"] == "thrips"
    assert result["confidence"] == pytest.approx(0.42, abs=1e-4)
    assert result["severity"] == "unknown"
    assert result["uncertain"] is True


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_predictor_rejects_invalid_confidence_threshold(tmp_path, threshold):
    photo = tmp_path / "rose.png"
    Image.new("RGB", (80, 60), "green").save(photo)

    with pytest.raises(ValueError, match="between 0 and 1"):
        predictor.predict_rose_problem(photo, confidence_threshold=threshold)


def test_predictor_reports_missing_model_and_invalid_images(tmp_path, monkeypatch):
    monkeypatch.delenv("FLORAGUARD_MODEL_PATH", raising=False)
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path / "models")
    (tmp_path / "models").mkdir()
    with pytest.raises(FileNotFoundError, match="No active trained model"):
        predictor._resolve_model_bundle()

    corrupted = tmp_path / "corrupted.jpg"
    corrupted.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="Invalid or corrupted image"):
        predictor._load_image(corrupted)

    unsupported = tmp_path / "rose.bmp"
    Image.new("RGB", (64, 64), "green").save(unsupported)
    with pytest.raises(ValueError, match="Unsupported image format"):
        predictor._load_image(unsupported)

    with pytest.raises(FileNotFoundError, match="Image does not exist"):
        predictor._load_image(tmp_path / "missing.jpg")


def test_predictor_rejects_invalid_model_probabilities(tmp_path, monkeypatch):
    photo = tmp_path / "rose.png"
    Image.new("RGB", (64, 64), "green").save(photo)
    monkeypatch.setattr(
        predictor,
        "_resolve_model_bundle",
        lambda: (
            tmp_path / "model.keras",
            {"class_names": list(CLASS_NAMES), "image_size": [224, 224]},
        ),
    )
    monkeypatch.setattr(
        predictor,
        "_load_model",
        lambda _path: FakeModel([0.1] * len(CLASS_NAMES)),
    )

    with pytest.raises(ValueError, match="invalid class probabilities"):
        predictor.predict_rose_problem(photo)


def test_prototype_severity_is_based_on_visible_coverage_not_confidence():
    low_image = Image.new("RGB", (224, 224), (0, 128, 0))
    medium_image = low_image.copy()
    ImageDraw.Draw(medium_image).rectangle((0, 0, 70, 70), fill=(150, 85, 35))
    high_image = low_image.copy()
    ImageDraw.Draw(high_image).rectangle((0, 0, 130, 130), fill=(150, 85, 35))

    low = estimate_severity(low_image, "spider_mite")
    medium = estimate_severity(medium_image, "spider_mite")
    high = estimate_severity(high_image, "spider_mite")

    assert low["severity"] == "low"
    assert medium["severity"] == "medium"
    assert high["severity"] == "high"
    assert low["severity_source"] == "prototype_visual_coverage"
    assert estimate_severity(high_image, "uncertain")["severity"] == "unknown"


def test_activate_existing_version_changes_pointer_without_retraining(
    tmp_path,
    monkeypatch,
):
    model_path = tmp_path / "floraguard_v2.keras"
    metadata_path = tmp_path / "floraguard_v2_metadata.json"
    model_path.write_bytes(b"test model placeholder")
    metadata_path.write_text(
        json.dumps({"class_names": list(CLASS_NAMES), "model_version": "v2"}),
        encoding="utf-8",
    )
    active_dir = tmp_path / "models"
    monkeypatch.setattr(predictor, "MODEL_DIR", active_dir)
    active_path = activate_model(model_path, active_dir=active_dir)

    active = json.loads(active_path.read_text(encoding="utf-8"))
    resolved_model_path, metadata = predictor._resolve_model_bundle()
    assert resolved_model_path == model_path.resolve()
    assert metadata["model_version"] == "v2"
    assert Path(active["model_file"]) == model_path.resolve()
    assert Path(active["metadata_file"]) == metadata_path.resolve()


def test_model_training_refuses_to_overwrite_a_version(tmp_path):
    model_path = tmp_path / "floraguard_v1.keras"
    metadata_path = tmp_path / "floraguard_v1_metadata.json"
    model_path.write_bytes(b"existing model bytes")
    metadata_path.write_text("{}", encoding="utf-8")
    original_model = model_path.read_bytes()

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        train_model._ensure_new_version((model_path, metadata_path))

    assert model_path.read_bytes() == original_model


def test_dataset_validation_reports_corruption_duplicates_and_counts(tmp_path):
    source = tmp_path / "source"
    for class_name in CLASS_NAMES:
        (source / class_name).mkdir(parents=True)
    image_path = source / CLASS_NAMES[0] / "healthy.png"
    Image.new("RGB", (80, 70), "green").save(image_path)
    (source / CLASS_NAMES[1] / "duplicate.png").write_bytes(image_path.read_bytes())
    (source / CLASS_NAMES[2] / "bad.png").write_bytes(b"broken")
    (source / CLASS_NAMES[3] / "wrong.txt").write_text("not an image", encoding="utf-8")

    report, records = dataset_tools.validate_dataset(source)

    assert report["total_files_reviewed"] == 4
    assert report["valid_images"] == 2
    assert report["counts_per_class"]["healthy"] == 1
    assert len(report["corrupted_images"]) == 1
    assert len(report["invalid_images"]) == 1
    assert len(report["exact_duplicate_groups"]) == 1
    assert "exact_duplicate" in report["review_flags_by_path"][
        str(image_path)
    ]
    assert len(records) == 4

    output = tmp_path / "report"
    dataset_tools.write_validation_report(report, records, output)
    assert json.loads((output / "dataset_validation.json").read_text())["valid_images"] == 2
    assert (output / "image_review.csv").is_file()
    assert image_path.is_file()


def test_group_aware_split_is_reproducible_and_keeps_each_group_together(tmp_path):
    data_dir = tmp_path / "data"
    source_dir = data_dir / "source"
    source_manifest = data_dir / "source_manifest.csv"
    source_manifest.parent.mkdir(parents=True)
    entries = []
    for class_index, class_name in enumerate(CLASS_NAMES):
        class_dir = source_dir / class_name
        class_dir.mkdir(parents=True)
        for group_index in range(5):
            image_path = class_dir / f"plant-{group_index}.png"
            _rose_like_image(image_path, class_index * 100 + group_index)
            entries.append(
                {
                    "path": image_path.relative_to(data_dir).as_posix(),
                    "source_type": "synthetic_test_fixture",
                    "source_name": "unit test",
                    "license": "generated test fixture",
                    "source_url": "",
                    "group_id": f"{class_name}-plant-{group_index}",
                    "review_status": "test_only",
                }
            )
            if class_name == "healthy" and group_index == 0:
                duplicate_path = class_dir / "plant-0-copy.png"
                duplicate_path.write_bytes(image_path.read_bytes())
                entries.append(
                    {
                        "path": duplicate_path.relative_to(data_dir).as_posix(),
                        "source_type": "synthetic_test_fixture",
                        "source_name": "unit test duplicate",
                        "license": "generated test fixture",
                        "source_url": "",
                        "group_id": "healthy-duplicate-group",
                        "review_status": "reviewed_keep",
                    }
                )
                entries[-2]["review_status"] = "reviewed_keep"
    with source_manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=entries[0].keys())
        writer.writeheader()
        writer.writerows(entries)

    manifest_path = data_dir / "split_manifest.csv"
    first = dataset_tools.create_split_manifest(
        data_dir, source_dir, source_manifest, manifest_path, seed=42
    )
    initial_manifest = manifest_path.read_text(encoding="utf-8")
    second = dataset_tools.create_split_manifest(
        data_dir, source_dir, source_manifest, manifest_path, seed=42
    )

    assert first["counts_per_split"] == second["counts_per_split"]
    assert manifest_path.read_text(encoding="utf-8") == initial_manifest
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    group_splits = {}
    for row in rows:
        group_splits.setdefault(row["group_id"], row["split"])
        assert group_splits[row["group_id"]] == row["split"]
    duplicate_splits = {
        row["split"]
        for row in rows
        if row["path"].startswith("source/healthy/")
        and (
            row["path"].endswith("plant-0.png")
            or row["path"].endswith("plant-0-copy.png")
        )
    }
    assert len(duplicate_splits) == 1
    assert set(row["split"] for row in rows) == {"train", "validation", "test"}


def test_class_metrics_are_computed_from_confusion_matrix():
    metrics = train_model._metrics_from_predictions(
        [0, 0, 1, 1],
        [0, 1, 1, 1],
        ("healthy", "spider_mite"),
    )

    assert metrics["accuracy"] == 0.75
    assert metrics["per_class"]["healthy"] == {
        "precision": 1.0,
        "recall": 0.5,
        "f1_score": 0.666667,
        "support": 2,
    }
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]


def test_confidence_metrics_report_uncertain_rate_and_accepted_accuracy():
    summary = train_model._confidence_metrics(
        [0, 1, 1],
        [0, 0, 1],
        [0.9, 0.4, 0.7],
        0.6,
    )

    assert summary == {
        "threshold": 0.6,
        "test_count": 3,
        "uncertain_count": 1,
        "uncertain_rate": 0.333333,
        "accepted_prediction_count": 2,
        "accuracy_on_accepted_predictions": 1.0,
    }


def test_confusion_matrix_artifact_is_written(tmp_path):
    output = tmp_path / "confusion.png"
    train_model._save_confusion_matrix_png(
        [[4, 1], [2, 3]],
        ("healthy", "spider_mite"),
        output,
    )

    with Image.open(output) as image:
        assert image.format == "PNG"
        assert image.width > 0
        assert image.height > 0


def test_split_manifest_rejects_a_group_in_multiple_splits(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = []
    for class_name in CLASS_NAMES:
        image_dir = data_dir / "source" / class_name
        image_dir.mkdir(parents=True)
        photo = image_dir / f"{class_name}.png"
        Image.new("RGB", (64, 64), "green").save(photo)
        rows.append(
            {
                "path": photo.relative_to(data_dir).as_posix(),
                "class_name": class_name,
                "group_id": "shared-plant",
                "split": "train",
            }
        )
    rows[-1]["split"] = "test"
    manifest = data_dir / "split_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="occurs in multiple splits"):
        train_model.read_split_manifest(manifest, data_dir)

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from dataset_tools import CLASS_NAMES, _class_for_path


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PROJECT_DIR / "data" / "rose"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "models"
IMAGE_SIZE = (224, 224)
SPLITS = ("train", "validation", "test")
INITIAL_LEARNING_RATE = 1e-3


def _tensorflow():
    try:
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError(
            "TensorFlow is required for training. Install the root "
            "requirements with `python -m pip install -r requirements.txt`."
        ) from error
    return tf


def class_directories(split_dir: Path) -> list[str]:
    if not split_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset split directory not found: {split_dir}. Prepare a "
            "group-aware split manifest with dataset_tools.py or provide "
            "train, validation, and test directories."
        )
    classes = sorted(path.name for path in split_dir.iterdir() if path.is_dir())
    if tuple(classes) != tuple(sorted(CLASS_NAMES)):
        missing = sorted(set(CLASS_NAMES) - set(classes))
        unexpected = sorted(set(classes) - set(CLASS_NAMES))
        raise ValueError(
            f"{split_dir} must contain exactly the seven required class "
            f"folders. Missing: {missing or 'none'}; unexpected: "
            f"{unexpected or 'none'}."
        )
    return list(CLASS_NAMES)


def read_split_manifest(
    manifest_path: Path,
    data_dir: Path,
) -> dict[str, list[tuple[str, int, str]]]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Split manifest not found: {manifest_path}")
    class_to_index = {name: index for index, name in enumerate(CLASS_NAMES)}
    by_split = {name: [] for name in SPLITS}
    seen_paths = set()
    seen_groups = {}
    with manifest_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        expected = {"path", "class_name", "group_id", "split"}
        if not reader.fieldnames or not expected.issubset(reader.fieldnames):
            raise ValueError(
                "Split manifest must contain: " + ", ".join(sorted(expected))
            )
        for line, row in enumerate(reader, start=2):
            relative = (row["path"] or "").strip().replace("\\", "/")
            class_name = (row["class_name"] or "").strip()
            group_id = (row["group_id"] or "").strip()
            split = (row["split"] or "").strip()
            if class_name not in class_to_index:
                raise ValueError(f"{manifest_path}:{line} has invalid class {class_name!r}")
            if split not in by_split:
                raise ValueError(f"{manifest_path}:{line} has invalid split {split!r}")
            if not relative or not group_id:
                raise ValueError(f"{manifest_path}:{line} requires path and group_id")
            image_path = (data_dir / Path(relative)).resolve()
            if not image_path.is_relative_to(data_dir.resolve()):
                raise ValueError(f"Manifest image path escapes the dataset directory: {relative}")
            if not image_path.is_file():
                raise FileNotFoundError(f"Manifest image does not exist: {image_path}")
            if _class_for_path(image_path) != class_name:
                raise ValueError(
                    f"{manifest_path}:{line} class_name does not match image path"
                )
            if image_path in seen_paths:
                raise ValueError(f"Duplicate image in split manifest: {image_path}")
            seen_paths.add(image_path)
            prior_split = seen_groups.setdefault(group_id, split)
            if prior_split != split:
                raise ValueError(
                    f"Group {group_id!r} occurs in multiple splits; this leaks "
                    "related photos between train, validation, and test."
                )
            by_split[split].append(
                (str(image_path), class_to_index[class_name], group_id)
            )

    if not any(by_split.values()):
        raise ValueError(
            f"Split manifest contains no image rows: {manifest_path}. "
            "Validate the source images and create a split manifest first."
        )

    for split in SPLITS:
        labels = {label for _, label, _ in by_split[split]}
        missing = [name for index, name in enumerate(CLASS_NAMES) if index not in labels]
        if missing:
            raise ValueError(
                f"Split {split!r} is missing classes: {', '.join(missing)}"
            )
    return by_split


def _directory_records(data_dir: Path) -> dict[str, list[tuple[str, int, str]]]:
    result = {}
    for split in SPLITS:
        split_dir = data_dir / split
        class_names = class_directories(split_dir)
        records = []
        for label, class_name in enumerate(class_names):
            image_paths = sorted(
                path
                for path in (split_dir / class_name).rglob("*")
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            )
            if not image_paths:
                raise ValueError(
                    f"No supported images found for class {class_name!r} in "
                    f"{split_dir}. Accepted formats are .jpg, .jpeg, .png, "
                    "and .webp."
                )
            records.extend((str(path.resolve()), label, str(path.resolve())) for path in image_paths)
        result[split] = records
    return result


def load_split(
    records: list[tuple[str, int, str]],
    batch_size: int,
    training: bool,
    seed: int,
):
    tf = _tensorflow()
    paths = [record[0] for record in records]
    labels = [record[1] for record in records]
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(
            buffer_size=len(records),
            seed=seed,
            reshuffle_each_iteration=True,
        )

    def decode_and_resize(path, label):
        def decode_oriented(path_tensor):
            image_path = path_tensor.numpy().decode("utf-8")
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue()

        image_bytes = tf.py_function(decode_oriented, [path], Tout=tf.string)
        image = tf.io.decode_png(image_bytes, channels=3)
        image.set_shape([None, None, 3])
        image = tf.image.resize(image, IMAGE_SIZE)
        return image, label

    dataset = dataset.map(
        decode_and_resize,
        num_parallel_calls=tf.data.AUTOTUNE,
        deterministic=True,
    )
    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(
    number_of_classes: int,
    seed: int,
    learning_rate: float = INITIAL_LEARNING_RATE,
):
    tf = _tensorflow()
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal", seed=seed),
            tf.keras.layers.RandomRotation(0.04, seed=seed + 1),
            tf.keras.layers.RandomZoom(0.08, seed=seed + 2),
            tf.keras.layers.RandomBrightness(0.08, value_range=(0, 255), seed=seed + 3),
        ],
        name="training_augmentation",
    )
    base_model = tf.keras.applications.MobileNetV2(
        weights="imagenet",
        include_top=False,
        input_shape=(*IMAGE_SIZE, 3),
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3))
    images = augmentation(inputs)
    images = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1)(images)
    features = base_model(images, training=False)
    features = tf.keras.layers.GlobalAveragePooling2D()(features)
    features = tf.keras.layers.Dropout(0.2, seed=seed)(features)
    outputs = tf.keras.layers.Dense(number_of_classes, activation="softmax")(features)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def configure_fine_tuning(
    model,
    unfreeze_layers: int,
    learning_rate: float,
) -> int:
    if unfreeze_layers < 1:
        raise ValueError("unfreeze_layers must be a positive integer")
    if learning_rate <= 0:
        raise ValueError("Fine-tuning learning rate must be positive")

    tf = _tensorflow()
    base_model = next(
        (
            layer
            for layer in model.layers
            if isinstance(layer, tf.keras.Model)
            and layer.name.startswith("mobilenetv2")
        ),
        None,
    )
    if base_model is None:
        raise ValueError("Could not locate the nested MobileNetV2 base model.")

    base_model.trainable = True
    unfreeze_from = max(0, len(base_model.layers) - unfreeze_layers)
    trainable_layers = 0
    for index, layer in enumerate(base_model.layers):
        layer.trainable = (
            index >= unfreeze_from
            and not isinstance(layer, tf.keras.layers.BatchNormalization)
        )
        trainable_layers += int(layer.trainable)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return trainable_layers


def _merge_histories(*histories) -> dict[str, list[float]]:
    merged = {}
    for history in histories:
        if history is None:
            continue
        for key, values in history.history.items():
            merged.setdefault(key, []).extend(float(value) for value in values)
    return merged


def _record_experiment(experiment_path: Path, record: dict) -> None:
    experiment_path.parent.mkdir(parents=True, exist_ok=True)
    with experiment_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")


def _metrics_from_predictions(true_labels, predicted_labels, class_names: tuple[str, ...]) -> dict:
    if len(true_labels) != len(predicted_labels):
        raise ValueError("True and predicted label counts must match")
    matrix = [[0 for _ in class_names] for _ in class_names]
    for actual, predicted in zip(true_labels, predicted_labels):
        if not 0 <= int(actual) < len(class_names) or not 0 <= int(predicted) < len(class_names):
            raise ValueError("Prediction labels must be valid class indices")
        matrix[int(actual)][int(predicted)] += 1
    per_class = {}
    for index, name in enumerate(class_names):
        true_positive = matrix[index][index]
        false_positive = sum(row[index] for row in matrix) - true_positive
        false_negative = sum(matrix[index]) - true_positive
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1_score": round(f1, 6),
            "support": sum(matrix[index]),
        }
    support_total = sum(metrics["support"] for metrics in per_class.values())
    macro_average = {
        key: round(sum(item[key] for item in per_class.values()) / len(class_names), 6)
        for key in ("precision", "recall", "f1_score")
    }
    weighted_average = {
        key: round(
            sum(item[key] * item["support"] for item in per_class.values())
            / max(support_total, 1),
            6,
        )
        for key in ("precision", "recall", "f1_score")
    }
    return {
        "accuracy": round(
            sum(matrix[index][index] for index in range(len(class_names)))
            / max(sum(sum(row) for row in matrix), 1),
            6,
        ),
        "per_class": per_class,
        "macro_average": macro_average,
        "weighted_average": weighted_average,
        "confusion_matrix": matrix,
        "class_names_in_matrix_order": list(class_names),
    }


def _confidence_metrics(
    true_labels: list[int],
    predicted_labels: list[int],
    confidence_values: list[float],
    threshold: float,
) -> dict:
    if not (len(true_labels) == len(predicted_labels) == len(confidence_values)):
        raise ValueError("Labels and confidence counts must match")
    if not 0 <= threshold <= 1:
        raise ValueError("Confidence threshold must be between 0 and 1")
    accepted = [
        index for index, confidence in enumerate(confidence_values)
        if confidence >= threshold
    ]
    uncertain_count = len(confidence_values) - len(accepted)
    accepted_correct = sum(
        predicted_labels[index] == true_labels[index] for index in accepted
    )
    return {
        "threshold": threshold,
        "test_count": len(true_labels),
        "uncertain_count": uncertain_count,
        "uncertain_rate": round(
            uncertain_count / len(true_labels) if true_labels else 0.0,
            6,
        ),
        "accepted_prediction_count": len(accepted),
        "accuracy_on_accepted_predictions": round(
            accepted_correct / len(accepted) if accepted else 0.0,
            6,
        ),
    }


def _save_confusion_matrix_png(matrix: list[list[int]], class_names: tuple[str, ...], path: Path) -> None:
    if len(matrix) != len(class_names) or any(
        len(row) != len(class_names) for row in matrix
    ):
        raise ValueError("Confusion matrix dimensions must match class_names")
    if any(value < 0 for row in matrix for value in row):
        raise ValueError("Confusion matrix counts cannot be negative")
    cell = 76
    margin_left = 190
    margin_top = 100
    size = margin_left + cell * len(class_names) + 30
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((margin_left, 20), "Predicted class", fill="black", font=font)
    draw.text((20, margin_top - 25), "Actual class", fill="black", font=font)
    maximum = max((value for row in matrix for value in row), default=0)
    for row_index, actual in enumerate(class_names):
        y = margin_top + row_index * cell
        draw.text((10, y + cell // 2 - 5), actual, fill="black", font=font)
        for column_index, predicted in enumerate(class_names):
            x = margin_left + column_index * cell
            value = matrix[row_index][column_index]
            shade = 255 if not maximum else 255 - int(150 * value / maximum)
            draw.rectangle((x, y, x + cell, y + cell), fill=(shade, shade, 255), outline="gray")
            draw.text((x + cell // 2 - 4, y + cell // 2 - 5), str(value), fill="black", font=font)
            label = predicted.replace("_", " ")
            label_image = Image.new("RGBA", (cell + 30, 18), (255, 255, 255, 0))
            ImageDraw.Draw(label_image).text((0, 0), label, fill="black", font=font)
            rotated = label_image.rotate(45, expand=True)
            image.paste(rotated, (x + 4, margin_top - 53), rotated)
    image.save(path)


def _version_name(value: str | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M%S")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,40}", value):
        raise ValueError("Model version may contain only letters, numbers, '.', '_' and '-'")
    return value


def _ensure_new_version(paths: tuple[Path, ...]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite an existing model version: " + ", ".join(existing)
        )


def _pointer_value(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(PROJECT_DIR):
        return resolved.relative_to(PROJECT_DIR).as_posix()
    return str(resolved)


def _portable_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(PROJECT_DIR):
        return resolved.relative_to(PROJECT_DIR).as_posix()
    return f"external/{path.name}"


def _activate_model(model_path: Path, metadata_path: Path) -> None:
    active_dir = DEFAULT_OUTPUT_DIR
    active_dir.mkdir(parents=True, exist_ok=True)
    active = active_dir / "active_model.json"
    temporary = active_dir / "active_model.json.tmp"
    temporary.write_text(
        json.dumps(
            {
                "model_file": _pointer_value(model_path),
                "metadata_file": _pointer_value(metadata_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(active)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate the FloraGuard rose-problem classifier."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--version")
    parser.add_argument("--dataset-version", default="unversioned")
    parser.add_argument("--confidence-threshold", type=float, default=0.60)
    parser.add_argument("--learning-rate", type=float, default=INITIAL_LEARNING_RATE)
    parser.add_argument("--fine-tune-epochs", type=int, default=0)
    parser.add_argument("--fine-tune-layers", type=int, default=30)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=1e-5)
    parser.add_argument(
        "--experiment-log",
        type=Path,
        default=PROJECT_DIR / "experiments" / "experiments.jsonl",
    )
    parser.add_argument("--experiment-notes", default="")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1 or args.fine_tune_epochs < 0:
        parser.error("--epochs and --batch-size must be positive; fine-tune epochs cannot be negative")
    if not 0 <= args.confidence_threshold <= 1:
        parser.error("--confidence-threshold must be between 0 and 1")
    if args.learning_rate <= 0 or args.fine_tune_learning_rate <= 0:
        parser.error("Learning rates must be positive")
    if args.fine_tune_layers < 1:
        parser.error("--fine-tune-layers must be positive")
    if args.seed < 0:
        parser.error("--seed must be a non-negative integer")

    version = _version_name(args.version)
    manifest = args.manifest or args.data_dir / "split_manifest.csv"
    if manifest.is_file():
        split_records = read_split_manifest(manifest, args.data_dir)
        split_method = "group-aware split_manifest.csv; no image files copied"
    else:
        split_records = _directory_records(args.data_dir)
        split_method = "pre-existing split directories; group leakage not verifiable"

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    experiment_path = args.experiment_log.expanduser()
    if not experiment_path.is_absolute():
        experiment_path = PROJECT_DIR / experiment_path
    experiment_path = experiment_path.resolve()
    stem = f"floraguard_{version}"
    model_path = output_dir / f"{stem}.keras"
    metadata_path = output_dir / f"{stem}_metadata.json"
    evaluation_path = output_dir / f"{stem}_evaluation.json"
    confusion_path = output_dir / f"{stem}_confusion_matrix.png"
    failures_path = output_dir / f"{stem}_incorrect_predictions.csv"
    candidate_path = output_dir / f"{stem}_fine_tune_candidate.keras"
    target_paths = (
        model_path,
        metadata_path,
        evaluation_path,
        confusion_path,
        failures_path,
        candidate_path,
    )
    _ensure_new_version(target_paths)

    tf = _tensorflow()
    tf.keras.utils.set_random_seed(args.seed)
    tf.config.experimental.enable_op_determinism()
    datasets = {
        split: load_split(
            split_records[split],
            args.batch_size,
            training=(split == "train"),
            seed=args.seed,
        )
        for split in SPLITS
    }
    model = build_model(len(CLASS_NAMES), args.seed, args.learning_rate)

    def callbacks_for(checkpoint_path: Path):
        return [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=5,
                restore_best_weights=True,
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath=str(checkpoint_path),
                monitor="val_loss",
                save_best_only=True,
                verbose=1,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.25,
                patience=2,
                min_lr=1e-6,
            ),
        ]

    stage_one_history = model.fit(
        datasets["train"],
        validation_data=datasets["validation"],
        epochs=args.epochs,
        callbacks=callbacks_for(model_path),
        verbose=1,
    )
    if not model_path.is_file():
        raise RuntimeError(
            "Training completed without saving a best validation checkpoint."
        )
    model = tf.keras.models.load_model(model_path)
    stage_two_history = None
    fine_tuning_summary = {
        "enabled": args.fine_tune_epochs > 0,
        "requested_epochs": args.fine_tune_epochs,
        "requested_unfreeze_layers": args.fine_tune_layers,
        "learning_rate": args.fine_tune_learning_rate,
        "trainable_base_layers": 0,
        "selected": False,
    }
    if args.fine_tune_epochs > 0:
        fine_tuning_summary["trainable_base_layers"] = configure_fine_tuning(
            model,
            args.fine_tune_layers,
            args.fine_tune_learning_rate,
        )
        stage_two_history = model.fit(
            datasets["train"],
            validation_data=datasets["validation"],
            epochs=args.fine_tune_epochs,
            callbacks=callbacks_for(candidate_path),
            verbose=1,
        )
        stage_one_best = min(stage_one_history.history["val_loss"])
        stage_two_best = min(stage_two_history.history["val_loss"])
        fine_tuning_summary["stage_one_best_validation_loss"] = float(stage_one_best)
        fine_tuning_summary["stage_two_best_validation_loss"] = float(stage_two_best)
        if candidate_path.is_file() and stage_two_best < stage_one_best:
            candidate_model = tf.keras.models.load_model(candidate_path)
            candidate_model.save(model_path)
            fine_tuning_summary["selected"] = True
        candidate_path.unlink(missing_ok=True)
        model = tf.keras.models.load_model(model_path)

    true_labels = [label for _, label, _ in split_records["test"]]
    predicted_labels = []
    confidence_values = []
    failures = []
    test_probabilities = model.predict(datasets["test"], verbose=0)
    if len(test_probabilities) != len(split_records["test"]):
        raise RuntimeError("Test prediction count does not match the test manifest.")
    for (image_path, label_index, _), probabilities in zip(
        split_records["test"],
        test_probabilities,
    ):
        predicted_index = int(tf.argmax(probabilities).numpy())
        confidence = float(probabilities[predicted_index])
        predicted_labels.append(predicted_index)
        confidence_values.append(confidence)
        if predicted_index != label_index:
            failures.append(
                {
                    "image_path": image_path,
                    "actual_class": CLASS_NAMES[label_index],
                    "predicted_class": CLASS_NAMES[predicted_index],
                    "confidence": round(confidence, 6),
                    "uncertain_at_threshold": confidence < args.confidence_threshold,
                    "final_prediction": (
                        "uncertain"
                        if confidence < args.confidence_threshold
                        else CLASS_NAMES[predicted_index]
                    ),
                    "severity": "unknown",
                    "possible_cause": "",
                    "review_notes": "",
                }
            )

    evaluation = _metrics_from_predictions(true_labels, predicted_labels, CLASS_NAMES)
    evaluation["test_image_count"] = len(true_labels)
    evaluation["incorrect_prediction_count"] = len(failures)
    evaluation["incorrect_predictions_csv"] = failures_path.name
    evaluation["confidence_threshold"] = args.confidence_threshold
    evaluation["confidence_threshold_metrics"] = _confidence_metrics(
        true_labels,
        predicted_labels,
        confidence_values,
        args.confidence_threshold,
    )
    evaluation["training_history"] = _merge_histories(
        stage_one_history,
        stage_two_history,
    )
    _save_confusion_matrix_png(
        evaluation["confusion_matrix"],
        CLASS_NAMES,
        confusion_path,
    )
    with failures_path.open("w", newline="", encoding="utf-8") as file:
        fields = (
            "image_path",
            "actual_class",
            "predicted_class",
            "confidence",
            "uncertain_at_threshold",
            "final_prediction",
            "severity",
            "possible_cause",
            "review_notes",
        )
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(failures)

    experiment_id = (
        f"floraguard_{version}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    merged_history = _merge_histories(stage_one_history, stage_two_history)
    experiment_record = {
        "experiment_id": experiment_id,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": version,
        "dataset_version": args.dataset_version,
        "model_architecture": "MobileNetV2",
        "image_size": list(IMAGE_SIZE),
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "fine_tuning": fine_tuning_summary,
        "epochs": {
            "head_training_maximum": args.epochs,
            "fine_tuning_maximum": args.fine_tune_epochs,
        },
        "augmentation": [
            "horizontal_flip",
            "rotation_0.04",
            "zoom_0.08",
            "brightness_0.08",
        ],
        "validation_metrics": {
            key: merged_history[key]
            for key in ("loss", "accuracy", "val_loss", "val_accuracy")
            if key in merged_history
        },
        "test_metrics": evaluation,
        "confidence_threshold": args.confidence_threshold,
        "notes": args.experiment_notes,
        "experiment_log": _portable_path(experiment_path),
    }
    metadata = {
        "experiment_id": experiment_id,
        "model_version": version,
        "training_date_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_version": args.dataset_version,
        "dataset_manifest": _portable_path(manifest) if manifest.is_file() else None,
        "split_method": split_method,
        "class_names": list(CLASS_NAMES),
        "image_size": list(IMAGE_SIZE),
        "model_architecture": "MobileNetV2",
        "transfer_learning": {
            "pretrained_weights": "ImageNet",
            "base_trainable": False,
            "augmentation": [
                "horizontal_flip",
                "rotation_0.04",
                "zoom_0.08",
                "brightness_0.08",
            ],
        },
        "training_configuration": {
            "seed": args.seed,
            "maximum_epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "confidence_threshold": args.confidence_threshold,
            "optimizer": "Adam",
            "loss": "sparse_categorical_crossentropy",
            "early_stopping": {"monitor": "val_loss", "patience": 5},
            "fine_tuning": fine_tuning_summary,
        },
        "split_image_counts": {
            split: len(split_records[split]) for split in SPLITS
        },
        "evaluation": evaluation,
        "severity_method": "prototype_visual_coverage",
        "experiment_notes": args.experiment_notes,
    }
    model.save(model_path)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    evaluation_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    _record_experiment(experiment_path, experiment_record)
    if args.activate:
        _activate_model(model_path, metadata_path)

    print(json.dumps(metadata, indent=2))
    print(f"Model: {model_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Evaluation: {evaluation_path}")
    print(f"Confusion matrix: {confusion_path}")
    print(f"Incorrect predictions: {failures_path}")
    print(f"Experiment log: {experiment_path}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as error:
        print(f"Training failed: {error}", file=sys.stderr)
        raise SystemExit(2) from error

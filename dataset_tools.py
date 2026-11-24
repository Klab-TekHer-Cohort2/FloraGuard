import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat


CLASS_NAMES = (
    "healthy",
    "spider_mite",
    "thrips",
    "powdery_mildew",
    "downy_mildew",
    "grey_mould",
    "black_spot",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
SPLIT_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}


def _class_for_path(path: Path) -> str | None:
    return next((parent.name for parent in path.parents if parent.name in CLASS_NAMES), None)


def _difference_hash(image: Image.Image) -> int:
    pixels = image.convert("L").resize(
        (9, 8), Image.Resampling.LANCZOS
    ).tobytes()
    value = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            value = (value << 1) | int(
                pixels[offset + column] > pixels[offset + column + 1]
            )
    return value


def _inspect_image(path: Path, blur_threshold: float) -> dict:
    result = {
        "path": str(path),
        "class_name": _class_for_path(path),
        "status": "ok",
        "format": None,
        "width": None,
        "height": None,
        "bytes": path.stat().st_size,
        "sha256": None,
        "difference_hash": None,
        "blur_score": None,
        "review_flags": [],
    }
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        result["status"] = "invalid_format"
        result["review_flags"].append("unsupported_extension")
        return result
    if result["class_name"] is None:
        result["status"] = "unlabelled"
        result["review_flags"].append("no_class_folder")
        return result

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            result["format"] = image.format
            result["width"], result["height"] = image.size
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                result["status"] = "invalid_format"
                result["review_flags"].append("unsupported_image_format")
                return result
            if min(image.size) < 64:
                result["review_flags"].append("very_small_image")
            rgb_image = image.convert("RGB")
            result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            result["difference_hash"] = _difference_hash(rgb_image)
            edge_image = rgb_image.convert("L").filter(ImageFilter.FIND_EDGES)
            result["blur_score"] = round(float(ImageStat.Stat(edge_image).var[0]), 3)
            if result["blur_score"] < blur_threshold:
                result["review_flags"].append("possible_blur")
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        result["status"] = "corrupted"
        result["review_flags"].append(f"unreadable_image: {error}")
    return result


def _duplicate_groups(records: list[dict], distance_limit: int = 4) -> tuple[list, list]:
    valid = [record for record in records if record["status"] == "ok"]
    exact_buckets = defaultdict(list)
    for record in valid:
        exact_buckets[record["sha256"]].append(record["path"])
    exact = [paths for paths in exact_buckets.values() if len(paths) > 1]

    near = []
    hashed = [record for record in valid if record["difference_hash"] is not None]
    for index, first in enumerate(hashed):
        for second in hashed[index + 1 :]:
            if first["sha256"] == second["sha256"]:
                continue
            if (first["difference_hash"] ^ second["difference_hash"]).bit_count() <= distance_limit:
                near.append([first["path"], second["path"]])
    return exact, near


def validate_dataset(data_dir: Path, blur_threshold: float = 10.0) -> tuple[dict, list[dict]]:
    data_dir = data_dir.resolve()
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_dir}")

    candidate_files = []
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if _class_for_path(path) is not None or path.suffix.lower() in IMAGE_SUFFIXES:
            candidate_files.append(path)
    records = [_inspect_image(path, blur_threshold) for path in sorted(candidate_files)]

    counts = Counter(
        record["class_name"]
        for record in records
        if record["class_name"] is not None and record["status"] == "ok"
    )
    nonzero_counts = [counts[name] for name in CLASS_NAMES if counts[name]]
    exact_duplicates, near_duplicates = _duplicate_groups(records)
    review_flags = defaultdict(list)
    records_by_path = {record["path"]: record for record in records}
    for record in records:
        for flag in record["review_flags"]:
            review_flags[record["path"]].append(flag)
    for group in exact_duplicates:
        for path in group:
            review_flags[path].append("exact_duplicate")
            records_by_path[path]["review_flags"].append("exact_duplicate")
    for pair in near_duplicates:
        for path in pair:
            review_flags[path].append("possible_near_duplicate")
            records_by_path[path]["review_flags"].append("possible_near_duplicate")

    dimensions = [
        (record["width"], record["height"])
        for record in records
        if record["width"] is not None and record["height"] is not None
    ]
    report = {
        "dataset_dir": str(data_dir),
        "total_files_reviewed": len(records),
        "valid_images": sum(record["status"] == "ok" for record in records),
        "counts_per_class": {name: counts[name] for name in CLASS_NAMES},
        "missing_classes": [name for name in CLASS_NAMES if counts[name] == 0],
        "class_imbalance_ratio": (
            round(max(nonzero_counts) / min(nonzero_counts), 3)
            if nonzero_counts
            else None
        ),
        "dimensions": {
            "minimum_width": min((item[0] for item in dimensions), default=None),
            "minimum_height": min((item[1] for item in dimensions), default=None),
            "maximum_width": max((item[0] for item in dimensions), default=None),
            "maximum_height": max((item[1] for item in dimensions), default=None),
        },
        "corrupted_images": [
            record["path"] for record in records if record["status"] == "corrupted"
        ],
        "invalid_images": [
            record["path"]
            for record in records
            if record["status"] in {"invalid_format", "unlabelled"}
        ],
        "exact_duplicate_groups": exact_duplicates,
        "possible_near_duplicate_pairs": near_duplicates,
        "small_image_paths": [
            record["path"]
            for record in records
            if "very_small_image" in record["review_flags"]
        ],
        "possible_blurry_paths": [
            record["path"]
            for record in records
            if "possible_blur" in record["review_flags"]
        ],
        "review_flags_by_path": dict(review_flags),
        "blur_score_note": (
            "Pillow edge-variance screening heuristic only; review flagged images "
            "manually. No images were modified or deleted."
        ),
    }
    return report, records


def write_validation_report(report: dict, records: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dataset_validation.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    fields = [
        "path",
        "class_name",
        "status",
        "format",
        "width",
        "height",
        "bytes",
        "sha256",
        "blur_score",
        "review_flags",
    ]
    with (output_dir / "image_review.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {key: record[key] for key in fields if key != "review_flags"}
            row["review_flags"] = ";".join(record["review_flags"])
            writer.writerow(row)


def _read_source_manifest(data_dir: Path, manifest_path: Path) -> list[dict]:
    expected_fields = {
        "path",
        "source_type",
        "source_name",
        "license",
        "source_url",
        "group_id",
        "review_status",
    }
    with manifest_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not expected_fields.issubset(reader.fieldnames):
            raise ValueError(
                "Source manifest must contain: " + ", ".join(sorted(expected_fields))
            )
        entries = []
        seen_paths = set()
        for row_number, row in enumerate(reader, start=2):
            relative = (row["path"] or "").strip().replace("\\", "/")
            group_id = (row["group_id"] or "").strip()
            if not relative or not group_id:
                raise ValueError(
                    f"{manifest_path}:{row_number} requires path and group_id"
                )
            path = (data_dir / Path(relative)).resolve()
            if not path.is_relative_to(data_dir.resolve()):
                raise ValueError(f"Manifest path escapes dataset directory: {relative}")
            if relative in seen_paths:
                raise ValueError(f"Duplicate path in source manifest: {relative}")
            seen_paths.add(relative)
            entries.append(
                {
                    "path": path,
                    "relative_path": Path(relative).as_posix(),
                    "group_id": group_id,
                    "source_type": (row["source_type"] or "").strip(),
                    "source_name": (row["source_name"] or "").strip(),
                    "license": (row["license"] or "").strip(),
                    "source_url": (row["source_url"] or "").strip(),
                    "review_status": (row["review_status"] or "").strip(),
                }
            )
    return entries


def create_split_manifest(
    data_dir: Path,
    source_dir: Path,
    source_manifest: Path,
    output_path: Path,
    seed: int,
) -> dict:
    data_dir = data_dir.resolve()
    source_dir = source_dir.resolve()
    entries = _read_source_manifest(data_dir, source_manifest.resolve())
    if not entries:
        raise ValueError(f"No images are listed in {source_manifest}")

    validation_report, inspected = validate_dataset(source_dir)
    if any(record["status"] != "ok" for record in inspected):
        invalid_count = sum(record["status"] != "ok" for record in inspected)
        raise ValueError(
            f"Dataset has {invalid_count} corrupted, unsupported, or unlabelled "
            "images; resolve them before creating a split manifest"
        )

    image_paths = {
        record["path"] for record in inspected if record["status"] == "ok"
    }
    listed_paths = {str(entry["path"]) for entry in entries}
    if listed_paths != image_paths:
        missing = sorted(image_paths - listed_paths)
        unknown = sorted(listed_paths - image_paths)
        raise ValueError(
            f"Source manifest must cover every dataset image. "
            f"Missing entries: {missing[:5]}; invalid entries: {unknown[:5]}"
        )

    for entry in entries:
        entry["class_name"] = _class_for_path(entry["path"])
        if entry["class_name"] is None:
            raise ValueError(f"Image is not inside one of the class folders: {entry['path']}")
        if entry["class_name"] not in CLASS_NAMES:
            raise ValueError(f"Unsupported class folder: {entry['class_name']}")
        for required in ("source_type", "source_name", "license", "review_status"):
            if not entry[required]:
                raise ValueError(
                    f"Source manifest entry {entry['relative_path']} needs {required}"
                )
        if entry["source_type"].lower() in {"public_dataset", "open_dataset"}:
            if entry["license"].lower() in {"unknown", "pending"}:
                raise ValueError(
                    f"Confirm the public-data licence before using "
                    f"{entry['relative_path']}"
                )
            if not entry["source_url"]:
                raise ValueError(
                    f"Record the source URL for public image {entry['relative_path']}"
                )

    group_parent = {entry["group_id"]: entry["group_id"] for entry in entries}

    def find(group: str) -> str:
        while group_parent[group] != group:
            group_parent[group] = group_parent[group_parent[group]]
            group = group_parent[group]
        return group

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            group_parent[second_root] = first_root

    hash_groups = defaultdict(list)
    for record in inspected:
        if record["sha256"]:
            hash_groups[record["sha256"]].append(record["path"])
    path_groups = {str(entry["path"]): entry["group_id"] for entry in entries}
    inspected_by_path = {record["path"]: record for record in inspected}
    for paths in hash_groups.values():
        if len(paths) > 1:
            first_group = path_groups[paths[0]]
            for path in paths[1:]:
                union(first_group, path_groups[path])
    for pair in validation_report["possible_near_duplicate_pairs"]:
        union(path_groups[pair[0]], path_groups[pair[1]])

    group_counts = defaultdict(Counter)
    for entry in entries:
        group = find(entry["group_id"])
        if entry["review_status"].lower() in {"needs_review", "rejected"}:
            raise ValueError(
                f"Resolve review status for {entry['relative_path']}: "
                f"{entry['review_status']}"
            )
        matching_record = inspected_by_path[str(entry["path"])]
        if matching_record["review_flags"] and entry["review_status"].lower() not in {
            "reviewed_keep",
            "expert_reviewed",
        }:
            raise ValueError(
                f"Review flagged image {entry['relative_path']} and set "
                "review_status to reviewed_keep or expert_reviewed before splitting"
            )
        group_counts[group][entry["class_name"]] += 1

    total_by_class = Counter(entry["class_name"] for entry in entries)
    missing = [name for name in CLASS_NAMES if total_by_class[name] == 0]
    if missing:
        raise ValueError(f"Cannot split dataset; missing classes: {', '.join(missing)}")

    rng = random.Random(seed)
    groups = list(group_counts)
    rng.shuffle(groups)
    groups.sort(
        key=lambda group: max(group_counts[group].values()),
        reverse=True,
    )
    target_by_split = {
        split: {
            class_name: total_by_class[class_name] * fraction
            for class_name in CLASS_NAMES
        }
        for split, fraction in SPLIT_FRACTIONS.items()
    }
    target_totals = {
        split: len(entries) * fraction for split, fraction in SPLIT_FRACTIONS.items()
    }
    assigned = {
        split: Counter()
        for split in SPLIT_FRACTIONS
    }
    total_assigned = Counter()
    group_split = {}
    split_names = tuple(SPLIT_FRACTIONS)

    for group in groups:
        options = list(split_names)
        rng.shuffle(options)
        best_split = min(
            options,
            key=lambda split: sum(
                (
                    (
                        assigned[split][class_name]
                        + group_counts[group][class_name]
                        - target_by_split[split][class_name]
                    )
                    / max(target_by_split[split][class_name], 1)
                )
                ** 2
                for class_name in CLASS_NAMES
            )
            + 0.15
            * (
                (
                    total_assigned[split]
                    + sum(group_counts[group].values())
                    - target_totals[split]
                )
                / max(target_totals[split], 1)
            )
            ** 2,
        )
        group_split[group] = best_split
        assigned[best_split].update(group_counts[group])
        total_assigned[best_split] += sum(group_counts[group].values())

    for class_name in CLASS_NAMES:
        for target_split in split_names:
            if assigned[target_split][class_name]:
                continue
            candidates = []
            for group, source_split in group_split.items():
                if source_split == target_split or not group_counts[group][class_name]:
                    continue
                if any(
                    assigned[source_split][other_class] - count < 1
                    for other_class, count in group_counts[group].items()
                ):
                    continue
                candidates.append(group)
            if not candidates:
                continue
            group = min(
                candidates,
                key=lambda candidate: sum(
                    (
                        (
                            assigned[target_split][name]
                            + group_counts[candidate][name]
                            - target_by_split[target_split][name]
                        )
                        / max(target_by_split[target_split][name], 1)
                    )
                    ** 2
                    for name in CLASS_NAMES
                ),
            )
            source_split = group_split[group]
            assigned[source_split].subtract(group_counts[group])
            assigned[target_split].update(group_counts[group])
            total_assigned[source_split] -= sum(group_counts[group].values())
            total_assigned[target_split] += sum(group_counts[group].values())
            group_split[group] = target_split

    split_counts = {
        split: {name: assigned[split][name] for name in CLASS_NAMES}
        for split in SPLIT_FRACTIONS
    }
    missing_per_split = {
        split: [name for name in CLASS_NAMES if not assigned[split][name]]
        for split in SPLIT_FRACTIONS
    }
    if any(missing_per_split.values()):
        raise ValueError(
            "Group-aware split cannot place every class in each split. "
            f"Add more independent groups. Missing: {missing_per_split}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("path", "class_name", "group_id", "split"),
        )
        writer.writeheader()
        for entry in entries:
            group = find(entry["group_id"])
            relative_to_data = entry["path"].relative_to(data_dir).as_posix()
            writer.writerow(
                {
                    "path": relative_to_data,
                    "class_name": entry["class_name"],
                    "group_id": group,
                    "split": group_split[group],
                }
            )
    return {
        "seed": seed,
        "split_fractions": SPLIT_FRACTIONS,
        "counts_per_split": split_counts,
        "images_per_split": dict(total_assigned),
        "group_count": len(groups),
        "exact_duplicate_groups_kept_together": sum(
            len(paths) > 1 for paths in hash_groups.values()
        ),
        "manifest_path": str(output_path.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate rose images or create a group-aware split manifest."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--data-dir", type=Path, default=Path("data/rose/source"))
    validate_parser.add_argument("--output-dir", type=Path, default=Path("reports/dataset"))
    validate_parser.add_argument("--blur-threshold", type=float, default=10.0)

    split_parser = subparsers.add_parser("split")
    split_parser.add_argument("--data-dir", type=Path, default=Path("data/rose"))
    split_parser.add_argument("--source-dir", type=Path, default=Path("data/rose/source"))
    split_parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path("data/rose/source_manifest.csv"),
    )
    split_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/rose/split_manifest.csv"),
    )
    split_parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    if args.command == "validate":
        report, records = validate_dataset(args.data_dir, args.blur_threshold)
        write_validation_report(report, records, args.output_dir)
        print(json.dumps(report, indent=2))
        print(f"Review files: {args.output_dir.resolve()}")
    else:
        summary = create_split_manifest(
            args.data_dir,
            args.source_dir,
            args.source_manifest,
            args.output,
            args.seed,
        )
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

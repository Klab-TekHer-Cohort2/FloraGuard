# FloraGuard image dataset

## Current inventory and provenance

At the time this AI/data implementation was inspected, the project contained
no rose image folders, no public-dataset downloads, no team-collected photos,
and no trained model files. Therefore the currently verified count is **zero
available images**; per-class counts and evaluation metrics are unavailable.
The project does not claim that any photos are real farm observations or
agronomist-validated.

The expected local source layout is `data/rose/source/<class>/`. Empty class
directories are provided as a scaffold. Images must be real and obtained with
permission. Do not generate or relabel synthetic images as disease examples.
Track provenance and grouping in `data/rose/source_manifest.csv`:

| Field | What to record |
|---|---|
| `path` | Image path relative to `data/rose/`, using `/` separators |
| `source_type` | `team_collected`, `public_dataset`, or another accurate value |
| `source_name` | Farm/team collection session or dataset name |
| `license` | Exact licence/permission terms, or `unknown` pending review |
| `source_url` | Original dataset/item URL if applicable; blank for team photos |
| `group_id` | Same stable value for photos from the same plant/source/session |
| `review_status` | `unreviewed`, `expert_reviewed`, `needs_review`, or another explicit status |

No public dataset is currently selected, downloaded, or licence-cleared. Check
and record the licence and attribution requirements before importing public
images. Ask an agronomist to review uncertain or ambiguous disease labels; do
not mark review complete until it has actually happened.
The split command requires a recorded licence and source URL for entries marked
`public_dataset` or `open_dataset`; this records provenance but does not itself
verify that the licence permits this use.

Target approximately 100 or more usable images per class for the initial
prototype:

- `healthy`
- `spider_mite`
- `thrips`
- `powdery_mildew`
- `downy_mildew`
- `grey_mould`
- `black_spot`

For spider mites and thrips, include symptom photographs as well as insects;
the insects may be too small to identify in a phone image. Collect varied
lighting, angles, leaf surfaces, symptom stages, and backgrounds. Record
whether photos came from a real farm or another source. Do not claim a target
is met until measured from the actual files.

## Quality review

Run:

```powershell
python dataset_tools.py validate `
  --data-dir data/rose/source `
  --output-dir reports/dataset
```

`dataset_validation.json` reports totals, counts by class, missing classes,
imbalance, image dimension ranges, exact duplicates, possible near-duplicates,
corrupt/unsupported files, small images, and heuristic blur suspects.
`image_review.csv` contains per-image details and review flags.

The quality checks do not infer botanical correctness, confirm that an image
contains a rose, or decide whether a disease label is correct. Human review is
required for unrelated, mislabelled, visually ambiguous, or questionable
images. Blur screening is based on image edge variance and is only a triage
heuristic. No image is silently deleted or changed.

## Group-aware data split

Use the source manifest's `group_id` to keep images from the same plant,
collection session, or near-identical photo sequence in a single split:

```powershell
python dataset_tools.py split `
  --data-dir data/rose `
  --source-dir data/rose/source `
  --source-manifest data/rose/source_manifest.csv `
  --output data/rose/split_manifest.csv `
  --seed 42
```

The generated manifest uses a reproducible 70% training, 15% validation, and
15% test target. Group assignments take precedence over exact proportions.
Exact byte-identical duplicates are forced into the same group. The split
command refuses to proceed when images are invalid, flagged images have not
been reviewed, provenance/group fields are missing, or a class cannot appear
in all three splits. Use `reviewed_keep` after a human has checked and accepted
a heuristic quality flag; use `expert_reviewed` only after expert review. If
there are too few independent plants/sessions, collect more; do not weaken the
test boundary to make training run.

Training uses only the training split to update weights and validation split
for early stopping/checkpoint selection. The test split is evaluated once after
training and never used for training or model selection. Keep the generated
manifest with the dataset version so a later run can reproduce the split.

## Preprocessing and augmentation

Images are EXIF-oriented, decoded as RGB, resized to 224 x 224, and rescaled
for MobileNetV2. Training-only augmentation includes horizontal flips, small
rotations, zoom, and brightness changes. Validation and test images are not
augmented.

The trainer uses group-aware manifest paths without copying image files.
Pre-existing `train/validation/test` folders remain supported for compatibility,
but their source grouping cannot be verified; the group-aware manifest is
preferred.

## Expert validation and limitations

No dataset has yet been populated or expert-reviewed, so no class counts,
quality conclusions, or model performance can currently be reported. The
classifier may not generalize across rose varieties, farms, phone cameras,
lighting, disease stages, or visually similar symptoms. A classification
model can be confidently wrong, especially on non-rose, cluttered, blurry, or
unfamiliar images. The confidence threshold does not guarantee detection of
unrelated photos; evaluate those explicitly before field use.
The default 0.60 threshold is an initial configurable value, not one selected
or calibrated from this project's data. Training evaluation records the
uncertain rate and accuracy among accepted test predictions so the team can
choose a threshold using validation evidence.

Severity is not present as a verified training label in the current project.
The implementation uses a prototype color/coverage heuristic, which can be
misled by background, shadows, lighting, and the disease itself. It is not a
validated severity diagnosis or treatment recommendation. Replace it with
expert-defined severity labels and a separately evaluated model or method
before relying on severity in field decisions.

The prototype severity helper compares simple symptom-colored pixel coverage
within a rough green/symptom-colored region. Its unvalidated thresholds are
below 5% for low, 5% to less than 20% for medium, and 20% or more for high.
It returns unknown when it cannot identify a plausible region. These
percentages are provisional rules, not expert-defined severity criteria, and
must not be treated as ground-truth labels or treatment guidance.

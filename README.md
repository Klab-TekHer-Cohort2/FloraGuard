# FloraGuard AI and data starter

This project contains Member 1's image-classification and data pipeline. The
classifier predicts what is visible in a rose photograph; it does not calculate
community outbreak risk. Severity is a separate, explicitly experimental
visual-coverage estimate until expert-labelled severity data is available.

## Current project status

- The supported classes are `healthy`, `spider_mite`, `thrips`,
  `powdery_mildew`, `downy_mildew`, `grey_mould`, and `black_spot`.
- The existing model design is MobileNetV2 transfer learning, initialized from
  ImageNet weights, with a 224 x 224 input and a seven-class softmax output.
- No rose dataset, trained weights, or prior evaluation results were present
  when the AI pipeline was inspected. No photographs, metrics, or expert review
  claims have been fabricated.
- Until a model is trained and activated, the backend should continue using its
  marked mock predictor.

See [DATASET.md](./DATASET.md) for collection/provenance requirements and
[AI_INTEGRATION.md](./AI_INTEGRATION.md) for the predictor contract.

## Install

Use Python supported by TensorFlow (the current project targets Python 3.11):

```powershell
Set-Location G:\codes\FloweraAI
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The root requirements provide TensorFlow/Keras, NumPy, and Pillow. Training
downloads MobileNetV2 ImageNet weights on first use if they are not cached, so
that first training run needs network access.

## Prepare and check the dataset

Place genuine, correctly labelled images under `data/rose/source/<class>/`.
Use only the seven supported class folder names. Do not copy test fixtures or
sample/demo images into the real training dataset.

For each image, add a row to `data/rose/source_manifest.csv`. Use a stable
`group_id` for every photo of the same plant or photo session. Record source
type, source name, licence, source URL where applicable, and review status.
The source manifest is not proof of expert validation; record the actual status.

Generate quality reports without changing or deleting any images:

```powershell
python dataset_tools.py validate `
  --data-dir data/rose/source `
  --output-dir reports/dataset
```

The JSON report and CSV review sheet show image counts and dimensions,
corrupted/unsupported files, exact and possible near-duplicates, small images,
class imbalance, and a heuristic blur flag. Review flagged images manually;
the blur screen is not an expert judgement.

Create a reproducible 70/15/15 group-aware split manifest:

```powershell
python dataset_tools.py split `
  --data-dir data/rose `
  --source-dir data/rose/source `
  --source-manifest data/rose/source_manifest.csv `
  --output data/rose/split_manifest.csv `
  --seed 42
```

This writes paths and split assignments to a CSV and does not copy or move
photos. It refuses to split invalid data or flagged images not explicitly
reviewed, and requires enough distinct groups for all seven classes to appear
in each split. Exact duplicate images are assigned together. The test split is
read only after training finishes; it is never used for fitting or callbacks.
Keep related/near-duplicate photos in one `group_id` to prevent leakage.

## Train and evaluate

```powershell
python train_model.py `
  --data-dir data/rose `
  --output-dir models `
  --version v1 `
  --dataset-version rose-data-1 `
  --seed 42 `
  --epochs 30 `
  --batch-size 32 `
  --confidence-threshold 0.60
```

Training requires `train`, `validation`, and `test` examples for every class.
`train_model.py` uses MobileNetV2 transfer learning, training-only random
horizontal flips, small rotations/zooms/brightness changes, early stopping,
and validation-loss checkpointing. The best validation checkpoint is evaluated
once on the held-out test split.

Each model version is written to distinct files such as
`models/floraguard_v1.keras` and `models/floraguard_v1_metadata.json`.
Existing versions are never overwritten. Evaluation JSON includes actual
accuracy, per-class precision/recall/F1, confusion matrix, test count, and
training history. The script also writes a confusion-matrix PNG and an
incorrect-prediction CSV with image path, actual/predicted classes, and
confidence plus blank `possible_cause` and `review_notes` fields for human
analysis (for example lighting, blur, early symptoms, similar diseases, camera
angle, background, or a class with too few examples). The pipeline does not
guess a cause. Do not quote results until they have been produced from the
project's own reviewed test data.

Review the artifacts, then activate the version explicitly without retraining:

```powershell
python activate_model.py --model models/floraguard_v1.keras
```

The predictor reads the selected version from `models/active_model.json`.
Alternatively, set `FLORAGUARD_MODEL_PATH=models/floraguard_v1.keras` to select
a particular model. `train_model.py --activate` is also available when you
explicitly want a newly trained version to become active immediately.

The trainer also accepts an existing `train/validation/test` folder layout when
no split manifest exists. In that case, the group provenance cannot be checked;
the group-aware manifest workflow above is preferred.

## Predict a photograph

```python
from predictor import predict_rose_problem, predict_image

details = predict_rose_problem("path/to/rose.jpg")
print(details)

# The backend contract:
backend_result = predict_image("path/to/rose.jpg")
print(backend_result)
```

The backend function returns `problem`, `severity`, `confidence`, and
`model_version`. `problem` becomes `uncertain` when the highest class
probability is below the configurable `CONFIDENCE_THRESHOLD` (default `0.60`).
For low-confidence results the severity is `unknown`. The detailed prediction
also includes the top candidate and whether the model was uncertain.
The initial `0.60` threshold is a prototype starting point, not calibrated on
FloraGuard images; tune it using validation data and expert review.

The classifier's confidence is not disease severity. Since no expert severity
labels currently exist, severity uses an isolated prototype visual-coverage
heuristic and reports `severity_source: "prototype_visual_coverage"` when it
can estimate from the image. See [DATASET.md](./DATASET.md) and
[AI_INTEGRATION.md](./AI_INTEGRATION.md) for limitations.
Detailed output includes a probability for each supported class. These
probabilities and the prototype severity estimate are not agronomist diagnoses.

## Tests

From the project root, using an environment with the root requirements and
pytest installed:

```powershell
python -m pytest -q tests
```

The tests use a fake model for predictor contract/threshold checks and generated
temporary images for data-pipeline checks. They do not train a model and do not
produce model-performance metrics.

## Backend handoff

See [AI_INTEGRATION.md](./AI_INTEGRATION.md) for the simple predictor function
and response contract. Area-level risk calculation remains outside this AI
component.

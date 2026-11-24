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
- The source-manifest template currently has zero image rows. Add real,
  reviewed images and provenance before attempting a split or training.
- Until a model is trained and activated, an integrating backend should keep
  its own marked mock predictor.

See [DATASET.md](./DATASET.md) for collection/provenance requirements and
[AI_INTEGRATION.md](./AI_INTEGRATION.md) for the predictor contract.

## AI/Data workspace layout

This repository itself is the AI/Data workspace; the reusable implementations
remain at the root rather than being duplicated under another `ai_ml/src`
tree:

```text
data/rose/source/      genuine labelled source images (currently empty)
data/rose/             source manifest and generated group-aware split manifest
models/                versioned model and evaluation outputs (currently empty)
experiments/           append-only experiment log
notebooks/             Colab/VS Code training notebook
reports/dataset/       generated validation report and image review CSV
tests/                 AI/data pipeline tests
```

`dataset_tools.py`, `train_model.py`, `predictor.py`, `severity.py`, and
`activate_model.py` are the canonical data, training, inference, severity, and
model-selection modules. Backend, frontend, risk-engine, Graph, USSD, and IVR
applications are not part of this AI workspace.

## Install

Use Python supported by TensorFlow (the current project targets Python 3.11):

```powershell
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

`--source-manifest` must be the CSV **file**, not the `data/rose/` directory.
The checked-in file has the correct header but currently has zero image rows.
Add one row per source image using the columns described in [DATASET.md](./DATASET.md).

This implementation intentionally writes paths and assignments to
`data/rose/split_manifest.csv`; it does not copy photos or create
`train/validation/test` directories. The trainer reads that manifest directly,
avoiding duplicate image files. It refuses to split invalid data or flagged
images not explicitly reviewed, and requires enough distinct groups for every
class to appear in each split. Its JSON summary contains actual per-class
counts for train, validation, and test. Exact and near-duplicate photos are
kept in the same split. The test set is read only after training finishes; it
is never used for fitting or callbacks. Keep related photos in one `group_id`
to prevent leakage.

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

Training requires examples for every class in the train, validation, and test
parts of the split manifest.
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

Every successful run appends its configuration and measured validation/test
metrics to `experiments/experiments.jsonl`; it never replaces prior records. See
[MODEL.md](./MODEL.md) for the architecture and
[TRAINING.md](./TRAINING.md) for the end-to-end workflow.

Optional second-stage fine-tuning unfreezes up to 30 upper MobileNetV2 layers,
keeps Batch Normalization frozen, and uses Adam at `1e-5` by default. It runs
only when `--fine-tune-epochs` is greater than zero, and its checkpoint is
selected only if validation loss improves over the frozen-head checkpoint.
For example:

```powershell
python train_model.py --data-dir data/rose --output-dir models --manifest data/rose/split_manifest.csv --version v2 --dataset-version rose-data-1 --seed 42 --epochs 30 --batch-size 32 --learning-rate 0.001 --fine-tune-epochs 10 --fine-tune-layers 30 --fine-tune-learning-rate 0.00001
```

Review the artifacts, then activate the version explicitly without retraining:

```powershell
python activate_model.py --model models
```

The directory form works when it contains exactly one `floraguard_*.keras`
version. If it contains multiple versions, specify the exact model file, for
example `--model models/floraguard_v2.keras`.

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

After real images have been split and a trained model activated, this smoke test
selects an actual image from the test split and runs the predictor:

```powershell
python test_predictor.py
```

It reports the selected image, problem, confidence, severity, and model version.
It fails clearly if the split manifest or active trained model is missing.

The optional reusable training notebook is
[notebooks/train_floraguard.ipynb](./notebooks/train_floraguard.ipynb). It
orchestrates the same scripts, including validation, split, training, evaluation
review, activation, smoke testing, and optional Colab artifact download; it
does not contain sample data or a duplicate model implementation.

## CPU, GPU, and Google Colab

CPU training is supported and no NVIDIA hardware, CUDA, or GPU packages are
required. Check the devices visible to the active TensorFlow environment with:

```powershell
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

An empty list means TensorFlow will use the CPU. Native Windows TensorFlow 2.11
and newer does not provide NVIDIA CUDA GPU support; do not install CUDA to fix
an empty list. If local CPU training is too slow, Google Colab is an option:
clone or upload this AI/data project, place the real dataset and manifest in
its expected layout, select a GPU runtime if desired, install
`requirements.txt`, and run the same validation, split, and training commands.
The scripts use project/data paths and command-line options rather than
machine-specific `G:\` or `C:\` paths. Save the trained model and evaluation
artifacts somewhere persistent before the Colab runtime ends.

## Backend handoff

See [AI_INTEGRATION.md](./AI_INTEGRATION.md) for the simple predictor function
and response contract. Area-level risk calculation remains outside this AI
component.

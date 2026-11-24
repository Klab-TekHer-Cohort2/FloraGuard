# Training and evaluation workflow

The source dataset is `data/rose/source/<class>/`; the checked-in source
manifest is a CSV template with no image rows. Add genuine, correctly labelled
photos and accurate provenance before training. Do not use generated images.
See `DATASET.md` for class, source, licence, grouping, and review requirements.

## Local VS Code / PowerShell

Create and activate a standalone AI environment from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q tests
```

Validate the raw source images and review the generated report:

```powershell
python dataset_tools.py validate --data-dir data/rose/source --output-dir reports/dataset
```

The source manifest (`--source-manifest`) argument is a **CSV file path**, not
a directory. After each real image has a manifest row, make the reproducible
group-aware split:

```powershell
python dataset_tools.py split --data-dir data/rose --source-dir data/rose/source --source-manifest data/rose/source_manifest.csv --output data/rose/split_manifest.csv --seed 42
```

The split is stored as paths in `split_manifest.csv`; images are not copied.
Its JSON output reports actual train/validation/test counts by class.
Repeated or near-duplicate images and all images assigned the same `group_id`
remain together to reduce leakage. The split tool requires each class to have
enough independent groups to appear in all three splits.

Train the frozen-head baseline, evaluate on the held-out test split, and save
a new model version:

```powershell
python train_model.py --data-dir data/rose --output-dir models --manifest data/rose/split_manifest.csv --version v1 --dataset-version rose-data-1 --seed 42 --epochs 30 --batch-size 32 --learning-rate 0.001 --confidence-threshold 0.60
```

Optional fine-tuning runs up to 10 more epochs over the last 30 base layers at
a lower learning rate. The fine-tuned checkpoint replaces Stage 1 only when it
has lower validation loss:

```powershell
python train_model.py --data-dir data/rose --output-dir models --manifest data/rose/split_manifest.csv --version v2 --dataset-version rose-data-1 --seed 42 --epochs 30 --batch-size 32 --learning-rate 0.001 --fine-tune-epochs 10 --fine-tune-layers 30 --fine-tune-learning-rate 0.00001 --confidence-threshold 0.60
```

Use a new version for each run. Training stops before model construction when a
split or class is missing. No model is produced from an empty dataset.

Inspect these actual-run artifacts before activation:

- `models/floraguard_<version>_metadata.json`
- `models/floraguard_<version>_evaluation.json`
- `models/floraguard_<version>_confusion_matrix.png`
- `models/floraguard_<version>_incorrect_predictions.csv`
- append-only `experiments/experiments.jsonl`

Then activate and run inference on an image assigned to the test split:

```powershell
python activate_model.py --model models
python test_predictor.py
```

The notebook `notebooks/train_floraguard.ipynb` runs these same reusable
scripts; it does not contain a second model implementation or sample data.

## CPU and Google Colab

CPU execution is supported. NVIDIA GPU/CUDA installation is not required.
`python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`
reports the devices visible to the active TensorFlow install. An empty list
means training will use CPU.

For Colab, clone or upload this project, put the genuine images and manifest
into the documented paths, install `requirements.txt`, and run the same
validation, split, and training scripts (or open the notebook). A Colab GPU
runtime is optional. Save model and evaluation artifacts to persistent storage
before the runtime is closed.

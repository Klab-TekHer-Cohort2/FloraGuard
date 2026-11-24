# FloraGuard AI integration

This repository contains the AI and data component only. The backend can call
the image predictor directly; it does not need to import the training code or
know the model architecture, preprocessing, or dataset layout.

## Predictor interface

From the project root (or with the project root on `PYTHONPATH`), call:

```python
from predictor import predict_image

prediction = predict_image(saved_image_path)
```

`saved_image_path` must point to a local JPEG, PNG, or WebP image. The function
returns a dictionary with these contract fields:

```python
{
    "problem": "spider_mite",
    "severity": "medium",
    "confidence": 0.87,
    "candidate_problem": None,
    "model_version": "v1",
}
```

Allowed problems are `healthy`, `spider_mite`, `thrips`, `powdery_mildew`,
`downy_mildew`, `grey_mould`, `black_spot`, and `uncertain`. Severity is `low`,
`medium`, `high`, or `unknown`. Confidence is the highest class probability;
it is not disease severity. The backend can store the additional
`candidate_problem` and `model_version` fields or ignore them.

The default configurable confidence threshold is `0.60` via
`CONFIDENCE_THRESHOLD`. Below it, `problem` is `uncertain`, severity is
`unknown`, and `candidate_problem` retains the most likely class.

The predictor raises clear errors for a missing model, missing or corrupted
images, unsupported formats, and invalid model output. A trained model is
required for real predictions. Until one is trained and activated, keep the
backend's own mock predictor selected; do not report mock output as a model
prediction.

## Model selection

Train and review a version before activation:

```powershell
python dataset_tools.py validate --data-dir data/rose/source --output-dir reports/dataset
python dataset_tools.py split --data-dir data/rose --source-dir data/rose/source --source-manifest data/rose/source_manifest.csv --output data/rose/split_manifest.csv --seed 42
python train_model.py --data-dir data/rose --output-dir models --version v1
python activate_model.py --model models
```

The checked-in source manifest currently contains no image rows, so splitting
and training stop until real, correctly labelled images and provenance are
added. The split command expects `--source-manifest` to name the CSV file.
`test_predictor.py` then runs inference on an actual image listed in the test
split; it does not create a sample image.

The active model is selected by `models/active_model.json`. Set
`FLORAGUARD_MODEL_PATH` to select a specific version instead. Install the AI
dependencies from the project root with `python -m pip install -r requirements.txt`.
See [README.md](./README.md) for dataset preparation and training, and
[DATASET.md](./DATASET.md) for provenance and quality requirements.

Training supports CPU without CUDA or NVIDIA dependencies. On Google Colab,
install the same requirements, provide the real dataset and manifest, and run
the same scripts with paths adjusted for the mounted storage location.

No rose dataset or trained model is currently included. Severity is a
prototype visual-coverage estimate, not an expert-validated diagnosis.
Image classification only identifies what is visible in a photograph; it does
not calculate community or area-level risk.

## Optional Neo4j knowledge layer

The standard `predict_image()` contract above does not connect to Neo4j and
continues to work without graph dependencies or credentials. If graph storage
and enrichment are needed, install the separate optional dependency file and
use `knowledge_graph.integration.predict_image_with_knowledge()`; it returns
the same AI result under `prediction`, plus `knowledge_status` and optional
graph data. Neo4j failure does not discard an otherwise successful AI result.

Configure `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` in the process
environment (and optionally `NEO4J_DATABASE`). The [knowledge graph guide](./knowledge_graph/README.md)
documents installation, Aura/local connection checks, schema setup, and the
seed scope. The seed contains only project class names and prediction severity
values; it does not invent symptoms, treatments, field observations, or
environmental claims.

```python
from knowledge_graph.integration import predict_image_with_knowledge

result = predict_image_with_knowledge(saved_image_path)
prediction = result["prediction"]
knowledge_status = result["knowledge_status"]
```

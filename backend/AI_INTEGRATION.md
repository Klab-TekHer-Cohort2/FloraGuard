# Member 1: AI integration contract

The backend accepts a local image path and expects an importable synchronous
function returning at least:

```python
{
    "problem": "spider_mite",
    "severity": "medium",
    "confidence": 0.87,
}
```

Allowed problems are `healthy`, `spider_mite`, `thrips`, `powdery_mildew`,
`downy_mildew`, `grey_mould`, `black_spot`, and `uncertain`. Severity is `low`,
`medium`, `high`, or `unknown`; confidence is between 0 and 1. Confidence is
the classifier's probability, not severity.

## FloraGuard AI implementation

The root `predictor.py` is the canonical prediction interface. It loads a
versioned Keras model and metadata, applies the model's RGB/224 x 224
preprocessing, validates class probabilities, applies the configured
`CONFIDENCE_THRESHOLD` (default `0.60`), and returns `uncertain` below the
threshold. It supports JPEG, PNG, and WebP files and raises explicit errors for
missing/corrupted images, missing model files, unsupported formats, and invalid
model outputs.

The classifier architecture is MobileNetV2 with ImageNet transfer learning.
There is currently no trained model or real rose dataset in the workspace.
Until Member 1 collects, reviews, and trains on the data, keep the backend's
`MockPredictor` selected; do not activate a nonexistent model or report
unmeasured performance.

No expert severity labels are currently available. The AI output includes a
modular prototype visual-coverage severity estimate when possible. It is not a
validated severity diagnosis. Low-confidence classification returns severity
`unknown`; image-analysis conditions that the prototype cannot assess also
return `unknown`.

## Connect the trained model

1. Follow the collection, provenance, validation, split, and training steps in
   the root [README](../README.md) and [DATASET.md](../DATASET.md).
2. Review the saved test evaluation and failure cases. Activate a reviewed
   version with `python activate_model.py --model models/floraguard_v1.keras`.
3. Install the root AI requirements into the backend environment:

   ```powershell
   Set-Location G:\codes\FloweraAI
   .\backend\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
   ```

4. In `backend/.env`, set:

   ```text
   AI_PREDICTOR_MODULE=app.ai.member1_adapter
   AI_PREDICTOR_FUNCTION=predict_image
   CONFIDENCE_THRESHOLD=0.60
   ```

   By default, the adapter loads `models/active_model.json` under the project
   root. To select a specific version instead, set
   `FLORAGUARD_MODEL_PATH=G:\codes\FloweraAI\models\floraguard_v1.keras`.
5. Restart the backend and submit a valid smartphone photo. The report's
   `prediction_source` records the adapter and returned model version, for
   example `model:app.ai.member1_adapter:version:v1`.

The backend continues to apply its own confidence threshold after the function
returns. Keep the root model threshold and backend setting aligned. If a
prediction is below threshold, the backend stores `problem="uncertain"`,
retains the candidate class where available, and sets severity to `unknown`.
Extra diagnostic output (`model_version`, `top_candidate`,
`severity_source`, class probabilities) is tolerated; the backend consumes the
contract fields. A low-confidence `predict_image` result also returns
`candidate_problem`, and the backend preserves it in the report while setting
the visible problem to `uncertain`.

Errors from invalid predictor output return `502`; unavailable model/runtime
errors return `503`. The regular smartphone upload workflow is the only channel
that calls this image predictor. USSD/IVR structured observations must not
invoke it. The separate community risk engine remains Member 2's responsibility
and is not replaced by image classification.

## Model files

Models are saved as versioned files, for example
`models/floraguard_v1.keras` and `models/floraguard_v1_metadata.json`.
`active_model.json` selects a version without modifying its weights.
`FLORAGUARD_MODEL_PATH` overrides that selection. Training refuses to overwrite
an existing model version. Metadata includes the class order, image size,
training configuration, dataset version, confidence threshold, evaluation
metrics, and split counts.

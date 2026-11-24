# FloraGuard image model

## Status

The repository contains training and inference code, but no real rose images
and no trained model weights. Model metrics and field performance are therefore
not available. Do not treat successful model construction or unit tests as a
trained classifier.

## Architecture and preprocessing

The selected model is MobileNetV2 with ImageNet initialization and a compact
seven-class softmax head. It is a lightweight transfer-learning baseline for
smartphone-sized image classification. Inputs are EXIF-oriented, converted to
RGB, resized to 224 x 224, and rescaled to MobileNetV2's expected range.

Training-only augmentation currently applies horizontal flips, small rotations,
zoom, and brightness variation. Validation and test images are not augmented.
The model emits probabilities in the fixed class order documented in
`dataset_tools.py`.

## Training stages

Stage 1 freezes the MobileNetV2 feature extractor and trains the classification
head using Adam at learning rate `1e-3`, sparse categorical cross-entropy, and
the configured batch size and epoch limit. Early stopping monitors validation
loss with patience 5; a checkpoint and learning-rate reduction callback are
used.

Stage 2 is opt-in with `--fine-tune-epochs`. It unfreezes at most the last
`--fine-tune-layers` base-model layers, keeps Batch Normalization layers frozen,
and recompiles with Adam at `1e-5` by default. Fine-tuning's best checkpoint is
selected only if its validation loss beats the Stage 1 best. This is a
validation-based selection rule, not evidence that fine-tuning has been run or
that it improves performance.

## Evaluation and uncertainty

After model selection, the held-out test split is evaluated once for accuracy,
per-class precision/recall/F1, macro and weighted metrics, confusion matrix,
incorrect predictions, and confidence-threshold summaries. The test set is
not used for fitting, early stopping, checkpoint selection, or fine-tuning.
Review the confusion matrix and incorrect-prediction CSV; possible failure
causes are left for human review rather than guessed.

`CONFIDENCE_THRESHOLD` defaults to 0.60 and can be overridden at prediction
time or during training metadata capture. A maximum class probability below
the threshold produces `problem="uncertain"` and `severity="unknown"`.
Confidence is not a calibrated probability until calibration is evaluated on
appropriate held-out data.

## Severity and limitations

There are no verified expert severity labels. Severity is a separate
`prototype_visual_coverage` color/coverage heuristic, not a severity model or a
ground-truth label. Lighting, shadows, background, camera differences, and
symptom appearance can make its output wrong. Replace it with an expert-defined
and separately evaluated approach before using it for decisions.

The classifier has not been trained or evaluated on FloraGuard rose images.
Its accuracy, robustness to field conditions, and generalization are unknown.
It may confuse visually similar diseases or fail on non-rose, blurry, cluttered,
or unfamiliar photographs.

## Artifacts and deployment

Each training run requires a new model version and writes versioned weights,
metadata, evaluation JSON, confusion-matrix PNG, and incorrect-prediction CSV.
The append-only `experiments/experiments.jsonl` records experiment configuration
and measured metrics. Existing versions are not overwritten. Activate a single
version with `python activate_model.py --model models` or pass its specific
`.keras` path when several versions exist.

The inference function is `predict_image(image_path)` in `predictor.py`. It
does not start or import FastAPI, Uvicorn, Swagger, SQLite, or the risk engine.

# FloraGuard AI/Data architecture

## Current state

The repository is the AI/Data workspace. It contains an image/data pipeline,
not an executable backend. The source manifest currently contains no image
rows, so no train/validation/test split, trained model, or performance metrics
exist. The intended state is **code ready, dataset not populated, model not
trained** until genuine images are supplied.

## Components and responsibilities

### Computer vision and machine learning

`dataset_tools.py` validates genuine image files and source provenance, then
creates a deterministic group-aware split manifest. `train_model.py` uses
TensorFlow/Keras MobileNetV2 transfer learning, training-only augmentation,
validation-based early stopping/checkpoint selection, and optional
validation-gated fine-tuning. The held-out test set is evaluated only after
model selection.

### Prediction and severity

`predictor.py` preprocesses an image and returns class probabilities, the
highest valid class, confidence, and `uncertain` below the configurable
threshold. It has no Neo4j dependency. `severity.py` is an isolated prototype
visual-coverage heuristic because expert severity labels are not available.
Confidence is model certainty; severity estimates visible damage and is not a
ground-truth label.

### Neo4j graph data layer

`knowledge_graph/` is an optional module using the official Neo4j Python
driver. It manages a graph vocabulary for diseases, pests, health status,
severity, and future expert-reviewed symptoms, environmental conditions, and
treatments. It can store structured prediction records and retrieve related
knowledge. It is not part of CNN training, an image store, a risk engine, or a
replacement for the dataset.

The seed marks only project class names and prediction-contract severity
values. It adds no unsupported agronomic relationships. New symptom, treatment,
or environmental facts must include a documented source and review status.

### Optional prediction integration

The normal flow remains:

```text
photo -> preprocessing -> TensorFlow/Keras classifier
      -> problem + confidence -> prototype severity
```

When graph enrichment is explicitly requested, the optional wrapper does:

```text
prediction -> optional Neo4j storage/retrieval -> prediction + graph status
```

If Neo4j is offline or unconfigured, callers still receive the completed AI
prediction with `knowledge_status="unavailable"`. Predictor errors are not
converted into successful-looking graph responses.

The backend integration contract remains the plain Python
`predict_image(image_path)` function documented in `AI_INTEGRATION.md`. The
backend can separately choose whether to persist a result in Neo4j.

### Optional future LLM/GraphRAG

No LLM, vector index, LangChain, or GraphRAG is implemented or required for
photo classification. A future graph-question answering component should be
separate from the classifier and introduced only if the product requirements
call for it.

## Dependencies and commands

Core AI/Data dependencies are in `requirements.txt`; the optional official
Neo4j driver is in `requirements-neo4j.txt`. No FastAPI, Flask, Uvicorn,
Swagger, or backend API is needed to validate data, train, predict, or run the
Neo4j connection test.

See `knowledge_graph/README.md` for secure environment configuration, seed,
schema, and graph repository examples. See `TRAINING.md` for the image-data
workflow.

import logging
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable

from knowledge_graph.connection import open_repository_from_env
from knowledge_graph.errors import KnowledgeGraphError
from knowledge_graph.repository import KnowledgeRepository
from predictor import predict_image


LOGGER = logging.getLogger(__name__)


def enrich_prediction(
    prediction: dict[str, Any],
    *,
    repository_context: Callable[
        [], AbstractContextManager[KnowledgeRepository]
    ] | None = None,
) -> dict[str, Any]:
    """Optionally store a prediction and retrieve graph context without blocking AI."""
    context = (
        repository_context
        if repository_context is not None
        else open_repository_from_env
    )
    try:
        with context() as repository:
            stored = repository.store_prediction(prediction)
            problem = prediction["problem"]
            if problem == "uncertain":
                related = None
            else:
                related = repository.get_problem_information(problem)
        return {
            "prediction": prediction,
            "knowledge_status": "available",
            "stored_prediction": stored,
            "related_knowledge": related,
        }
    except KnowledgeGraphError as error:
        LOGGER.warning(
            "Neo4j knowledge layer unavailable (%s): %s; returning AI prediction only.",
            type(error).__name__,
            error,
        )
        return {
            "prediction": prediction,
            "knowledge_status": "unavailable",
            "knowledge_error": {
                "type": type(error).__name__,
                "message": str(error),
            },
            "stored_prediction": None,
            "related_knowledge": None,
        }


def predict_image_with_knowledge(
    image_path: str | Path,
    *,
    repository_context: Callable[
        [], AbstractContextManager[KnowledgeRepository]
    ] | None = None,
) -> dict[str, Any]:
    prediction = predict_image(image_path)
    return enrich_prediction(prediction, repository_context=repository_context)

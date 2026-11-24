import math
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from knowledge_graph import queries
from knowledge_graph.errors import (
    KnowledgeGraphError,
    Neo4jDriverUnavailableError,
    Neo4jUnavailableError,
)
from knowledge_graph.schema import SCHEMA_QUERIES


PROBLEM_KINDS = {
    "healthy": "health_status",
    "spider_mite": "pest",
    "thrips": "pest",
    "powdery_mildew": "disease",
    "downy_mildew": "disease",
    "grey_mould": "disease",
    "black_spot": "disease",
}
PREDICTION_PROBLEMS = frozenset((*PROBLEM_KINDS, "uncertain"))
SEVERITY_VALUES = frozenset({"low", "medium", "high", "unknown"})
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def _validate_slug(value: str, field_name: str = "slug") -> str:
    if not isinstance(value, str) or not SLUG_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase snake_case identifier.")
    return value


def _validate_name(value: str, field_name: str = "name") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


class KnowledgeRepository:
    def __init__(self, driver: Any, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def _run(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            from neo4j.exceptions import Neo4jError
        except ImportError as error:
            raise Neo4jDriverUnavailableError(
                "Install optional graph dependencies with "
                "`python -m pip install -r requirements-neo4j.txt`."
            ) from error

        try:
            with self.driver.session(database=self.database) as session:
                return [
                    dict(record)
                    for record in session.run(query, parameters or {})
                ]
        except Neo4jError as error:
            raise Neo4jUnavailableError("Neo4j query failed.") from error

    @staticmethod
    def _first(records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            raise KnowledgeGraphError(
                "Neo4j returned no record. Seed the graph classes before storing "
                "a classified prediction."
            )
        return records[0]

    def ping(self) -> None:
        self._run("RETURN 1 AS ok")

    def ensure_schema(self) -> None:
        for query in SCHEMA_QUERIES:
            self._run(query)

    def create_disease(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_DISEASE,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_pest(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_PEST,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_health_status(
        self,
        slug: str,
        name: str,
        validation_status: str = "project_class_only",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_HEALTH_STATUS,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_symptom(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_SYMPTOM,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_severity(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        slug = _validate_slug(slug)
        if slug not in SEVERITY_VALUES:
            raise ValueError("severity must be low, medium, high, or unknown.")
        return self._first(
            self._run(
                queries.CREATE_SEVERITY,
                {
                    "slug": slug,
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_environmental_condition(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_ENVIRONMENTAL_CONDITION,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_treatment(
        self,
        slug: str,
        name: str,
        validation_status: str = "needs_expert_review",
    ) -> dict[str, Any]:
        return self._first(
            self._run(
                queries.CREATE_TREATMENT,
                {
                    "slug": _validate_slug(slug),
                    "name": _validate_name(name),
                    "validation_status": _validate_name(
                        validation_status, "validation_status"
                    ),
                },
            )
        )

    def create_relationship(
        self,
        source_label: str,
        source_slug: str,
        relationship: str,
        target_label: str,
        target_slug: str,
    ) -> dict[str, Any]:
        query = queries.relationship_query(
            source_label,
            relationship,
            target_label,
        )
        return self._first(
            self._run(
                query,
                {
                    "source_slug": _validate_slug(source_slug, "source_slug"),
                    "target_slug": _validate_slug(target_slug, "target_slug"),
                },
            )
        )

    def get_problem_information(self, slug: str) -> dict[str, Any] | None:
        records = self._run(
            queries.GET_PROBLEM_INFORMATION,
            {"slug": _validate_slug(slug)},
        )
        return records[0] if records else None

    def get_disease_information(self, slug: str) -> dict[str, Any] | None:
        records = self._run(
            queries.GET_DISEASE_INFORMATION,
            {"slug": _validate_slug(slug)},
        )
        return records[0] if records else None

    def get_related_symptoms(self, problem_slug: str) -> list[dict[str, Any]]:
        return self._run(
            queries.GET_RELATED_SYMPTOMS,
            {"slug": _validate_slug(problem_slug)},
        )

    def get_pests_for_symptom(self, symptom_slug: str) -> list[dict[str, Any]]:
        return self._run(
            queries.GET_PESTS_FOR_SYMPTOM,
            {"symptom_slug": _validate_slug(symptom_slug, "symptom_slug")},
        )

    def get_environmental_relationships(
        self,
        problem_slug: str,
    ) -> list[dict[str, Any]]:
        return self._run(
            queries.GET_ENVIRONMENTAL_RELATIONSHIPS,
            {"slug": _validate_slug(problem_slug)},
        )

    def get_treatments(self, problem_slug: str) -> list[dict[str, Any]]:
        return self._run(
            queries.GET_TREATMENTS,
            {"slug": _validate_slug(problem_slug)},
        )

    def store_prediction(
        self,
        prediction: dict[str, Any],
        *,
        image_id: str | None = None,
        location_slug: str | None = None,
        location_name: str | None = None,
        prediction_id: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(prediction, dict):
            raise ValueError("prediction must be a dictionary.")
        problem = prediction.get("problem")
        if not isinstance(problem, str) or problem not in PREDICTION_PROBLEMS:
            raise ValueError("prediction.problem is not a supported FloraGuard class.")
        severity = prediction.get("severity")
        if not isinstance(severity, str) or severity not in SEVERITY_VALUES:
            raise ValueError("prediction.severity is not a supported severity value.")
        confidence = prediction.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("prediction.confidence must be a finite number from 0 to 1.")

        candidate_problem = prediction.get("candidate_problem")
        if candidate_problem is not None and (
            not isinstance(candidate_problem, str)
            or candidate_problem not in PROBLEM_KINDS
        ):
            raise ValueError("candidate_problem must be a known class or None.")
        model_version = prediction.get("model_version")
        if model_version is not None:
            model_version = _validate_name(model_version, "model_version")
        if image_id is not None:
            image_id = _validate_name(image_id, "image_id")
        if location_slug is not None:
            location_slug = _validate_slug(location_slug, "location_slug")
            if location_name is not None:
                location_name = _validate_name(location_name, "location_name")
        elif location_name is not None:
            raise ValueError("location_name requires location_slug.")
        if prediction_id is not None:
            prediction_id = _validate_name(prediction_id, "prediction_id")

        parameters = {
            "prediction_id": prediction_id or str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "problem": problem,
            "candidate_problem": candidate_problem,
            "confidence": float(confidence),
            "severity": severity,
            "model_version": model_version,
            "image_id": image_id,
            "location_slug": location_slug,
            "location_name": location_name,
        }
        query = (
            queries.STORE_UNCERTAIN_PREDICTION
            if problem == "uncertain"
            else queries.STORE_PREDICTION
        )
        return self._first(self._run(query, parameters))

    def get_previous_predictions(
        self,
        problem: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if problem is not None and (
            not isinstance(problem, str) or problem not in PREDICTION_PROBLEMS
        ):
            raise ValueError("problem is not a supported FloraGuard class.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500.")
        return self._run(
            queries.GET_PREVIOUS_PREDICTIONS,
            {"problem": problem, "limit": limit},
        )

import json
import sys

from knowledge_graph.connection import open_repository_from_env
from knowledge_graph.errors import KnowledgeGraphError
from knowledge_graph.repository import KnowledgeRepository


DISEASE_CLASSES = (
    "powdery_mildew",
    "downy_mildew",
    "grey_mould",
    "black_spot",
)
PEST_CLASSES = ("spider_mite", "thrips")
SEVERITY_VALUES = ("low", "medium", "high", "unknown")


def seed_project_classes(repository: KnowledgeRepository) -> dict[str, int]:
    for slug in DISEASE_CLASSES:
        repository.create_disease(
            slug,
            slug,
            validation_status="project_class_only",
        )
    for slug in PEST_CLASSES:
        repository.create_pest(
            slug,
            slug,
            validation_status="project_class_only",
        )
    repository.create_health_status(
        "healthy",
        "healthy",
        validation_status="project_class_only",
    )
    for slug in SEVERITY_VALUES:
        repository.create_severity(
            slug,
            slug,
            validation_status="prediction_contract_value",
        )
    return {
        "disease_classes": len(DISEASE_CLASSES),
        "pest_classes": len(PEST_CLASSES),
        "health_statuses": 1,
        "severity_values": len(SEVERITY_VALUES),
        "symptoms_treatments_environmental_facts": 0,
    }


def main() -> int:
    try:
        with open_repository_from_env() as repository:
            repository.ensure_schema()
            counts = seed_project_classes(repository)
    except KnowledgeGraphError as error:
        print(f"Neo4j seed failed: {error}", file=sys.stderr)
        return 2
    print(
        "Seeded project class taxonomy only; no field observations or "
        "unverified symptom/treatment facts were added."
    )
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

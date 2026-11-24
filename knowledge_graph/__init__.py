"""Optional Neo4j knowledge layer for FloraGuard AI predictions."""

from knowledge_graph.errors import (
    KnowledgeGraphError,
    Neo4jConfigurationError,
    Neo4jDriverUnavailableError,
    Neo4jUnavailableError,
)

__all__ = [
    "KnowledgeGraphError",
    "Neo4jConfigurationError",
    "Neo4jDriverUnavailableError",
    "Neo4jUnavailableError",
]

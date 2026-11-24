class KnowledgeGraphError(RuntimeError):
    """Base error for optional knowledge graph operations."""


class Neo4jUnavailableError(KnowledgeGraphError):
    """Neo4j could not be reached or a graph operation failed."""


class Neo4jConfigurationError(KnowledgeGraphError):
    """Neo4j environment configuration is missing or invalid."""


class Neo4jDriverUnavailableError(KnowledgeGraphError):
    """The optional Neo4j Python driver is not installed."""

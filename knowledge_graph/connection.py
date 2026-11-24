import argparse
from contextlib import contextmanager
from typing import Any, Generator

from knowledge_graph.config import Neo4jConfig
from knowledge_graph.errors import (
    KnowledgeGraphError,
    Neo4jDriverUnavailableError,
    Neo4jUnavailableError,
)
from knowledge_graph.repository import KnowledgeRepository


def create_driver(config: Neo4jConfig) -> Any:
    try:
        from neo4j import GraphDatabase
    except ImportError as error:
        raise Neo4jDriverUnavailableError(
            "Neo4j support is optional. Install it with "
            "`python -m pip install -r requirements-neo4j.txt`."
        ) from error
    return GraphDatabase.driver(
        config.uri,
        auth=(config.username, config.password),
    )


@contextmanager
def open_repository_from_env(
    config: Neo4jConfig | None = None,
) -> Generator[KnowledgeRepository, None, None]:
    config = config or Neo4jConfig.from_env()
    driver = create_driver(config)
    try:
        try:
            from neo4j.exceptions import Neo4jError
        except ImportError as error:
            raise Neo4jDriverUnavailableError(
                "Neo4j support is optional. Install it with "
                "`python -m pip install -r requirements-neo4j.txt`."
            ) from error

        try:
            driver.verify_connectivity()
        except Neo4jError as error:
            raise Neo4jUnavailableError(
                "Neo4j is unavailable; check the URI, credentials, network, "
                "and database name."
            ) from error
        yield KnowledgeRepository(driver, config.database)
    finally:
        driver.close()


def test_connection() -> None:
    with open_repository_from_env() as repository:
        repository.ping()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Neo4j configuration, authentication, and database access."
    )
    parser.parse_args()
    try:
        test_connection()
    except KnowledgeGraphError as error:
        print(f"Neo4j connection unavailable: {error}")
        return 2
    print("Neo4j connection successful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

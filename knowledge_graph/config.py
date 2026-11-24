import os
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit

from knowledge_graph.errors import Neo4jConfigurationError


SUPPORTED_URI_SCHEMES = {
    "neo4j",
    "neo4j+s",
    "bolt",
    "bolt+s",
}
PLAINTEXT_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    username: str
    password: str = field(repr=False)
    database: str = "neo4j"

    def __post_init__(self) -> None:
        try:
            parsed_uri = urlsplit(self.uri) if isinstance(self.uri, str) else None
            hostname = parsed_uri.hostname if parsed_uri is not None else None
            port = parsed_uri.port if parsed_uri is not None else None
        except ValueError:
            parsed_uri = None
            hostname = None
            port = None
        if (
            parsed_uri is None
            or parsed_uri.scheme not in SUPPORTED_URI_SCHEMES
            or not hostname
            or port == 0
            or parsed_uri.username is not None
            or parsed_uri.password is not None
        ):
            raise Neo4jConfigurationError(
                "NEO4J_URI must be a Neo4j/Bolt URI without embedded credentials."
            )
        normalized_host = hostname.lower().rstrip(".")
        if normalized_host.endswith(".databases.neo4j.io") and parsed_uri.scheme != "neo4j+s":
            raise Neo4jConfigurationError(
                "Neo4j Aura URIs must use neo4j+s:// for encrypted, "
                "certificate-verified routing."
            )
        if (
            parsed_uri.scheme in {"neo4j", "bolt"}
            and normalized_host not in PLAINTEXT_LOCAL_HOSTS
        ):
            raise Neo4jConfigurationError(
                "Unencrypted Neo4j URIs are allowed only for localhost. "
                "Use the provider-issued encrypted URI for remote databases."
            )
        if not isinstance(self.username, str) or not self.username.strip():
            raise Neo4jConfigurationError("NEO4J_USERNAME cannot be empty.")
        if not isinstance(self.password, str) or not self.password:
            raise Neo4jConfigurationError("NEO4J_PASSWORD cannot be empty.")
        if not isinstance(self.database, str) or not self.database.strip():
            raise Neo4jConfigurationError("NEO4J_DATABASE cannot be empty.")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Neo4jConfig":
        values = os.environ if environ is None else environ
        required = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
        missing = [key for key in required if not values.get(key)]
        if missing:
            raise Neo4jConfigurationError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )

        uri = values["NEO4J_URI"].strip()
        username = values["NEO4J_USERNAME"].strip()
        password = values["NEO4J_PASSWORD"]
        database = values.get("NEO4J_DATABASE", "neo4j").strip() or "neo4j"
        return cls(uri, username, password, database)

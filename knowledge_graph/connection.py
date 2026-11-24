import argparse
import os
import socket
import ssl
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generator
from urllib.parse import urlsplit

from knowledge_graph.config import Neo4jConfig
from knowledge_graph.errors import (
    KnowledgeGraphError,
    Neo4jDriverUnavailableError,
    Neo4jUnavailableError,
)
from knowledge_graph.repository import KnowledgeRepository


def _configure_tls_trust() -> str:
    """Make configured PEM roots visible to Python's verified TLS defaults."""
    bundle = (
        os.environ.get("NEO4J_CA_BUNDLE")
        or os.environ.get("SSL_CERT_FILE")
        or os.environ.get("CURL_CA_BUNDLE")
    )
    if not bundle:
        return "system CA store"

    bundle_path = Path(bundle).expanduser()
    try:
        if not bundle_path.is_file():
            raise OSError
        with bundle_path.open("rb") as certificate_file:
            has_pem_certificate = b"-----BEGIN CERTIFICATE-----" in certificate_file.read()
    except OSError as error:
        raise KnowledgeGraphError(
            "The configured TLS CA bundle is not a readable file."
        ) from error
    if not has_pem_certificate:
        raise KnowledgeGraphError(
            "The configured TLS CA bundle must contain PEM certificates."
        )

    resolved_bundle = str(bundle_path.resolve())
    if os.environ.get("NEO4J_CA_BUNDLE"):
        os.environ["SSL_CERT_FILE"] = resolved_bundle
        return "system CA store plus NEO4J_CA_BUNDLE"
    if os.environ.get("SSL_CERT_FILE"):
        return "system CA store plus SSL_CERT_FILE"

    os.environ["SSL_CERT_FILE"] = resolved_bundle
    return "system CA store plus CURL_CA_BUNDLE"


def create_driver(config: Neo4jConfig) -> Any:
    _configure_tls_trust()
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


def _resolve_addresses(host: str, port: int) -> list[tuple]:
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def _check_tcp(addresses: list[tuple], timeout: float) -> None:
    last_error = None
    for family, socket_type, protocol, _canonical_name, address in addresses:
        try:
            with socket.socket(family, socket_type, protocol) as connection:
                connection.settimeout(timeout)
                connection.connect(address)
            return
        except OSError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise OSError("DNS returned no TCP addresses.")


def _verify_tls(host: str, port: int, timeout: float) -> None:
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as connection:
        with context.wrap_socket(connection, server_hostname=host) as tls_connection:
            tls_connection.getpeercert()


def _finish_diagnostics(
    statuses: dict[str, str],
    output: Callable[[str], None],
    final_status: str,
) -> bool:
    statuses["Final connection status"] = final_status
    for name in (
        "URI configuration",
        "DNS resolution",
        "TCP connectivity",
        "TLS/SSL verification",
        "Neo4j authentication",
        "Final connection status",
    ):
        output(f"{name}: {statuses[name]}")
    return final_status.startswith("PASS")


def diagnose_connection(
    config: Neo4jConfig | None = None,
    *,
    output: Callable[[str], None] = print,
    timeout: float = 5.0,
) -> bool:
    statuses = {
        "URI configuration": "NOT TESTED",
        "DNS resolution": "NOT TESTED",
        "TCP connectivity": "NOT TESTED",
        "TLS/SSL verification": "NOT TESTED",
        "Neo4j authentication": "NOT TESTED",
        "Final connection status": "FAILED",
    }

    try:
        config = config or Neo4jConfig.from_env()
    except KnowledgeGraphError as error:
        statuses["URI configuration"] = f"FAILED ({error})"
        for name in (
            "DNS resolution",
            "TCP connectivity",
            "TLS/SSL verification",
            "Neo4j authentication",
        ):
            statuses[name] = "NOT TESTED (URI configuration unavailable)"
        return _finish_diagnostics(statuses, output, "FAILED")

    parsed_uri = urlsplit(config.uri)
    host = parsed_uri.hostname
    if host is None:
        statuses["URI configuration"] = "FAILED (URI host is missing)"
        return _finish_diagnostics(statuses, output, "FAILED")
    port = parsed_uri.port or 7687
    statuses["URI configuration"] = (
        f"PASS (scheme={parsed_uri.scheme}; endpoint and credentials configured; "
        "database configured)"
    )

    try:
        addresses = _resolve_addresses(host, port)
    except OSError:
        statuses["DNS resolution"] = "FAILED (host name could not be resolved)"
        statuses["TCP connectivity"] = "NOT TESTED (DNS resolution failed)"
        statuses["TLS/SSL verification"] = "NOT TESTED (DNS resolution failed)"
        statuses["Neo4j authentication"] = "NOT TESTED (DNS resolution failed)"
        return _finish_diagnostics(statuses, output, "FAILED")
    statuses["DNS resolution"] = f"PASS ({len(addresses)} address(es))"

    try:
        _check_tcp(addresses, timeout)
    except OSError:
        statuses["TCP connectivity"] = "FAILED (could not open TCP connection)"
        statuses["TLS/SSL verification"] = "NOT TESTED (TCP connection failed)"
        statuses["Neo4j authentication"] = "NOT TESTED (TCP connection failed)"
        return _finish_diagnostics(statuses, output, "FAILED")
    statuses["TCP connectivity"] = "PASS"

    encrypted = parsed_uri.scheme.endswith("+s")
    if encrypted:
        try:
            trust_source = _configure_tls_trust()
            _verify_tls(host, port, timeout)
        except ssl.SSLCertVerificationError:
            statuses["TLS/SSL verification"] = (
                f"FAILED (certificate chain is not trusted by {trust_source}; "
                "if TLS inspection is expected, configure its verified root "
                "CA with NEO4J_CA_BUNDLE)"
            )
            statuses["Neo4j authentication"] = (
                "NOT TESTED (blocked by TLS certificate verification)"
            )
            return _finish_diagnostics(statuses, output, "FAILED")
        except KnowledgeGraphError as error:
            statuses["TLS/SSL verification"] = f"FAILED ({error})"
            statuses["Neo4j authentication"] = (
                "NOT TESTED (TLS trust configuration failed)"
            )
            return _finish_diagnostics(statuses, output, "FAILED")
        except (ssl.SSLError, OSError):
            statuses["TLS/SSL verification"] = "FAILED (TLS handshake failed)"
            statuses["Neo4j authentication"] = (
                "NOT TESTED (TLS handshake failed)"
            )
            return _finish_diagnostics(statuses, output, "FAILED")
        statuses["TLS/SSL verification"] = (
            f"PASS ({trust_source} and host verification)"
        )
    else:
        statuses["TLS/SSL verification"] = (
            "NOT APPLICABLE (unencrypted localhost URI)"
        )

    try:
        driver = create_driver(config)
    except KnowledgeGraphError as error:
        statuses["Neo4j authentication"] = f"NOT TESTED ({type(error).__name__})"
        return _finish_diagnostics(statuses, output, "FAILED")

    try:
        from neo4j.exceptions import AuthError, Neo4jError

        verify_authentication = getattr(driver, "verify_authentication", None)
        if callable(verify_authentication):
            authenticated = verify_authentication()
            if not authenticated:
                statuses["Neo4j authentication"] = "FAILED (credentials rejected)"
                return _finish_diagnostics(statuses, output, "FAILED")
            statuses["Neo4j authentication"] = "PASS"

        driver.verify_connectivity()
        with driver.session(database=config.database) as session:
            result = session.run("RETURN 1 AS ok").single()
        if result is None:
            if statuses["Neo4j authentication"] == "NOT TESTED":
                statuses["Neo4j authentication"] = (
                    "NOT CONFIRMED (database query returned no result)"
                )
            return _finish_diagnostics(
                statuses,
                output,
                "FAILED (database query returned no result)",
            )
        if statuses["Neo4j authentication"] == "NOT TESTED":
            statuses["Neo4j authentication"] = "PASS"
    except AuthError:
        statuses["Neo4j authentication"] = "FAILED (credentials rejected)"
        return _finish_diagnostics(statuses, output, "FAILED")
    except Neo4jError as error:
        if statuses["Neo4j authentication"] == "NOT TESTED":
            statuses["Neo4j authentication"] = (
                f"NOT CONFIRMED ({type(error).__name__})"
            )
        return _finish_diagnostics(
            statuses,
            output,
            f"FAILED (Neo4j routing/database check: {type(error).__name__})",
        )
    finally:
        driver.close()

    return _finish_diagnostics(statuses, output, "PASS")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safely diagnose Neo4j URI, DNS, TCP, TLS, authentication, and "
            "database access."
        )
    )
    parser.parse_args()
    return 0 if diagnose_connection() else 2


if __name__ == "__main__":
    raise SystemExit(main())

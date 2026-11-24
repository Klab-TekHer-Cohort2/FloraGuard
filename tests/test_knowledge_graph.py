import ssl

import pytest

from knowledge_graph import connection
from knowledge_graph.config import Neo4jConfig
from knowledge_graph.errors import Neo4jConfigurationError, Neo4jUnavailableError
from knowledge_graph.integration import enrich_prediction, predict_image_with_knowledge
from knowledge_graph.queries import relationship_query
from knowledge_graph.repository import KnowledgeRepository
from knowledge_graph.schema import SCHEMA_QUERIES
from knowledge_graph.seed_data import seed_project_classes


class FakeSession:
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def run(self, query, parameters):
        self.driver.calls.append((query, parameters))
        if "AS entity" in query:
            return [{"entity": {"slug": parameters.get("slug")}}]
        if "AS prediction" in query:
            return [{"prediction": {"id": parameters.get("prediction_id")}}]
        if "AS problem" in query:
            return [{"problem": {"slug": parameters.get("slug")}, "related": []}]
        if "AS relationship" in query:
            return [{"relationship": "CAUSES"}]
        return []


class FakeDriver:
    def __init__(self):
        self.calls = []

    def session(self, database):
        assert database == "neo4j"
        return FakeSession(self)


class FailingContext:
    def __init__(self, error):
        self.error = error

    def __enter__(self):
        raise self.error

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False


def test_neo4j_config_requires_credentials_and_redacts_password():
    with pytest.raises(Neo4jConfigurationError, match="NEO4J_URI"):
        Neo4jConfig.from_env({})

    config = Neo4jConfig.from_env(
        {
            "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "do-not-print-this",
        }
    )

    assert config.database == "neo4j"
    assert "do-not-print-this" not in repr(config)


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com",
        "neo4j+s://user:password@example.databases.neo4j.io",
        "neo4j+s:///missing-host",
        "neo4j+ssc://example.databases.neo4j.io",
        "neo4j://example.databases.neo4j.io",
    ],
)
def test_neo4j_config_rejects_invalid_or_embedded_credentials(uri):
    with pytest.raises(Neo4jConfigurationError):
        Neo4jConfig.from_env(
            {
                "NEO4J_URI": uri,
                "NEO4J_USERNAME": "neo4j",
                "NEO4J_PASSWORD": "secret",
            }
        )


def test_plaintext_uri_is_restricted_to_localhost():
    config = Neo4jConfig.from_env(
        {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "secret",
        }
    )

    assert config.uri == "bolt://localhost:7687"


def test_neo4j_config_rejects_malformed_authority():
    with pytest.raises(Neo4jConfigurationError, match="NEO4J_URI"):
        Neo4jConfig.from_env(
            {
                "NEO4J_URI": "neo4j+s://[",
                "NEO4J_USERNAME": "neo4j",
                "NEO4J_PASSWORD": "secret",
            }
        )


def test_diagnostics_report_all_stages_without_credentials_when_unconfigured(
    monkeypatch,
):
    for key in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(key, raising=False)
    output = []

    connected = connection.diagnose_connection(output=output.append)

    assert connected is False
    assert len(output) == 6
    assert output[0].startswith("URI configuration: FAILED")
    assert all("NOT TESTED" in line for line in output[1:5])
    assert output[-1] == "Final connection status: FAILED"
    assert "secret" not in "\n".join(output)


def test_diagnostics_stop_before_authentication_when_tls_verification_fails(
    monkeypatch,
):
    config = Neo4jConfig.from_env(
        {
            "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "do-not-print-this",
        }
    )
    monkeypatch.setattr(
        connection,
        "_resolve_addresses",
        lambda _host, _port: [(None, None, None, None, None)],
    )
    monkeypatch.setattr(connection, "_check_tcp", lambda _addresses, _timeout: None)

    def fail_tls(_host, _port, _timeout):
        raise ssl.SSLCertVerificationError("untrusted chain")

    monkeypatch.setattr(connection, "_verify_tls", fail_tls)
    monkeypatch.setattr(
        connection,
        "create_driver",
        lambda _config: pytest.fail("Authentication must not run after TLS failure."),
    )
    output = []

    connected = connection.diagnose_connection(config, output=output.append)

    assert connected is False
    assert "TLS/SSL verification: FAILED" in output[3]
    assert "Neo4j authentication: NOT TESTED" in output[4]
    assert "do-not-print-this" not in "\n".join(output)


def test_diagnostics_report_success_after_verified_tls_and_database_query(monkeypatch):
    config = Neo4jConfig.from_env(
        {
            "NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "secret",
        }
    )

    class FakeResult:
        def single(self):
            return {"ok": 1}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc_value, _traceback):
            return False

        def run(self, query):
            assert query == "RETURN 1 AS ok"
            return FakeResult()

    class FakeDriver:
        def verify_authentication(self):
            return True

        def verify_connectivity(self):
            return None

        def session(self, database):
            assert database == "neo4j"
            return FakeSession()

        def close(self):
            return None

    monkeypatch.setattr(
        connection,
        "_resolve_addresses",
        lambda _host, _port: [(None, None, None, None, None)],
    )
    monkeypatch.setattr(connection, "_check_tcp", lambda _addresses, _timeout: None)
    monkeypatch.setattr(connection, "_verify_tls", lambda _host, _port, _timeout: None)
    monkeypatch.setattr(connection, "create_driver", lambda _config: FakeDriver())
    output = []

    connected = connection.diagnose_connection(config, output=output.append)

    assert connected is True
    assert all(line.endswith("PASS") or "PASS (" in line for line in output)
    assert "secret" not in "\n".join(output)


def test_relationship_query_uses_allowlisted_identifiers_and_parameter_values():
    query = relationship_query("Disease", "CAUSES", "Symptom")

    assert "MATCH (source:Disease {slug: $source_slug})" in query
    assert "MERGE (source)-[edge:CAUSES]->(target)" in query
    with pytest.raises(ValueError, match="Unsupported"):
        relationship_query("Disease", "CAUSES]->(:User)-[:X", "Symptom")
    with pytest.raises(ValueError, match="Unsupported"):
        relationship_query("User", "CAUSES", "Symptom")


def test_repository_relationship_values_are_passed_as_parameters():
    driver = FakeDriver()
    repository = KnowledgeRepository(driver)

    repository.create_relationship(
        "Disease",
        "powdery_mildew",
        "CAUSES",
        "Symptom",
        "leaf_spots",
    )

    query, parameters = driver.calls[0]
    assert "powdery_mildew" not in query
    assert "leaf_spots" not in query
    assert parameters == {
        "source_slug": "powdery_mildew",
        "target_slug": "leaf_spots",
    }


def test_repository_parameterizes_prediction_and_uses_uncertain_query():
    driver = FakeDriver()
    repository = KnowledgeRepository(driver)
    prediction = {
        "problem": "uncertain",
        "severity": "unknown",
        "confidence": 0.42,
        "candidate_problem": "thrips",
        "model_version": "v1",
    }

    result = repository.store_prediction(
        prediction,
        image_id="opaque-image-id",
        location_slug="field_1",
        location_name="Field 1",
        prediction_id="prediction-1",
    )

    query, parameters = driver.calls[0]
    assert "MATCH (problem:Problem" not in query
    assert parameters["problem"] == "uncertain"
    assert parameters["image_id"] == "opaque-image-id"
    assert parameters["location_slug"] == "field_1"
    assert parameters["prediction_id"] == "prediction-1"
    assert "opaque-image-id" not in query
    assert result == {"prediction": {"id": "prediction-1"}}


@pytest.mark.parametrize(
    "prediction",
    [
        {"problem": "unknown", "severity": "low", "confidence": 0.8},
        {"problem": "healthy", "severity": "extreme", "confidence": 0.8},
        {"problem": "healthy", "severity": "low", "confidence": float("nan")},
        {"problem": "healthy", "severity": "low", "confidence": 1.1},
        {
            "problem": "uncertain",
            "severity": "unknown",
            "confidence": 0.4,
            "candidate_problem": "unknown",
        },
    ],
)
def test_repository_rejects_invalid_prediction_values(prediction):
    with pytest.raises(ValueError):
        KnowledgeRepository(FakeDriver()).store_prediction(prediction)


def test_repository_validates_history_limit_and_relationship_values():
    repository = KnowledgeRepository(FakeDriver())
    with pytest.raises(ValueError, match="limit"):
        repository.get_previous_predictions(limit=501)
    with pytest.raises(ValueError, match="lowercase snake_case"):
        repository.get_disease_information("powdery_mildew MATCH")


def test_repository_applies_idempotent_schema_constraints():
    driver = FakeDriver()

    KnowledgeRepository(driver).ensure_schema()

    assert len(driver.calls) == len(SCHEMA_QUERIES)
    assert all("IF NOT EXISTS" in query for query, _parameters in driver.calls)


def test_graph_enrichment_returns_stored_prediction_and_context():
    prediction = {
        "problem": "spider_mite",
        "severity": "medium",
        "confidence": 0.87,
        "candidate_problem": None,
        "model_version": "v1",
    }

    class SuccessfulRepository:
        def store_prediction(self, result):
            assert result is prediction
            return {"id": "prediction-1"}

        def get_problem_information(self, slug):
            assert slug == "spider_mite"
            return {"problem": {"slug": slug}, "related": []}

    class SuccessfulContext:
        def __enter__(self):
            return SuccessfulRepository()

        def __exit__(self, _exc_type, _exc_value, _traceback):
            return False

    result = enrich_prediction(
        prediction,
        repository_context=SuccessfulContext,
    )

    assert result == {
        "prediction": prediction,
        "knowledge_status": "available",
        "stored_prediction": {"id": "prediction-1"},
        "related_knowledge": {"problem": {"slug": "spider_mite"}, "related": []},
    }


def test_graph_failure_preserves_prediction_and_reports_unavailable(caplog):
    prediction = {
        "problem": "spider_mite",
        "severity": "medium",
        "confidence": 0.87,
        "candidate_problem": None,
        "model_version": "v1",
    }

    result = enrich_prediction(
        prediction,
        repository_context=lambda: FailingContext(
            Neo4jUnavailableError("Neo4j is unavailable.")
        ),
    )

    assert result["prediction"] is prediction
    assert result["knowledge_status"] == "unavailable"
    assert result["stored_prediction"] is None
    assert "Neo4jUnavailableError" in caplog.text
    assert result["knowledge_error"]["message"] == "Neo4j is unavailable."


def test_optional_wrapper_runs_predictor_before_graph_fallback(monkeypatch):
    from knowledge_graph import integration

    prediction = {
        "problem": "healthy",
        "severity": "unknown",
        "confidence": 0.9,
        "candidate_problem": None,
        "model_version": "v1",
    }

    def fake_predict(path):
        assert path == "rose.jpg"
        return prediction

    monkeypatch.setattr(integration, "predict_image", fake_predict)
    result = predict_image_with_knowledge(
        "rose.jpg",
        repository_context=lambda: FailingContext(
            Neo4jConfigurationError("Missing NEO4J_URI.")
        ),
    )

    assert result["prediction"] is prediction
    assert result["knowledge_status"] == "unavailable"
    assert result["knowledge_error"] == {
        "type": "Neo4jConfigurationError",
        "message": "Missing NEO4J_URI.",
    }


def test_optional_wrapper_does_not_hide_predictor_errors(monkeypatch):
    from knowledge_graph import integration

    def failed_prediction(_path):
        raise FileNotFoundError("No active trained model.")

    monkeypatch.setattr(integration, "predict_image", failed_prediction)

    with pytest.raises(FileNotFoundError, match="No active trained model"):
        predict_image_with_knowledge("rose.jpg")


def test_seed_contains_only_project_taxonomy_and_contract_severity_values():
    class SeedRecorder:
        def __init__(self):
            self.created = []

        def create_disease(self, slug, name, validation_status):
            self.created.append(("disease", slug, validation_status))

        def create_pest(self, slug, name, validation_status):
            self.created.append(("pest", slug, validation_status))

        def create_health_status(self, slug, name, validation_status):
            self.created.append(("health_status", slug, validation_status))

        def create_severity(self, slug, name, validation_status):
            self.created.append(("severity", slug, validation_status))

    repository = SeedRecorder()
    counts = seed_project_classes(repository)

    assert counts == {
        "disease_classes": 4,
        "pest_classes": 2,
        "health_statuses": 1,
        "severity_values": 4,
        "symptoms_treatments_environmental_facts": 0,
    }
    assert len(repository.created) == 11
    assert all(record[2] != "expert_verified" for record in repository.created)

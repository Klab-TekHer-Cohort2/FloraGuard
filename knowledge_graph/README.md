# Optional Neo4j knowledge layer

## Role and boundaries

Neo4j is an optional graph database for project class taxonomy and, when
explicitly requested, structured AI prediction records. It does **not** train,
host, or replace the TensorFlow/Keras image classifier. `predict_image()` in
the project root remains usable without the Neo4j driver, credentials, or
database.

The checked-in seed is only the project's classification vocabulary and
severity contract. It does not assert expert-verified symptoms, treatments,
environmental effects, or real farm observations. Those graph nodes and edges
must be supplied from documented, reviewed sources before being presented as
agronomic facts.

## Graph schema

| Label | Meaning |
|---|---|
| `Problem` | Common label used for matching a model output |
| `Disease` | `powdery_mildew`, `downy_mildew`, `grey_mould`, `black_spot` |
| `Pest` | `spider_mite`, `thrips` |
| `HealthStatus` | `healthy`; it is not modelled as a disease |
| `Symptom` | Expert-reviewed symptom knowledge when later provided |
| `Severity` | Prediction contract levels: `low`, `medium`, `high`, `unknown` |
| `EnvironmentalCondition` | Reviewed condition knowledge when later provided |
| `Treatment` | Reviewed treatment information when later provided |
| `Prediction` | Structured prediction and model metadata; no image bytes |
| `Image` | Optional opaque image ID, not a local path or image content |
| `Location` | Optional caller-provided location ID/name |
| `Rose` | Optional rose entity for future reviewed observations |

Supported semantic edges include `CAUSES`, `HAS_SEVERITY`,
`ASSOCIATED_WITH`, `FAVOURED_BY`, `HAS_TREATMENT`, `HAS_PROBLEM`, `HAS_PEST`,
`IDENTIFIED`, `BASED_ON`, and `LOCATED_AT`. The seed creates only class and
severity nodes; it does not invent edges about symptoms, treatments, or
environment.

## Install and configure

The root `requirements.txt` contains only the AI/data packages. Install the
official Neo4j Python driver separately and only when using this module:

```powershell
python -m pip install -r requirements-neo4j.txt
```

Set credentials in the process environment; do not commit them:

```powershell
$env:NEO4J_URI = "neo4j+s://<your-aura-instance>.databases.neo4j.io"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "<your-password>"
$env:NEO4J_DATABASE = "neo4j"
```

The driver verifies Aura certificates against the operating-system CA store.
Python's Neo4j driver does not automatically honor `CURL_CA_BUNDLE`; the
connection command now bridges that setting to Python's standard
`SSL_CERT_FILE` trust path when needed, while retaining Windows system roots
and hostname verification. If your network intentionally inspects TLS, ask
your administrator for its approved PEM root CA bundle and set
`NEO4J_CA_BUNDLE` to that file. Only trust a CA obtained and verified through
your organization's trusted channel; never add a certificate copied from a
failed server connection. This option adds CA trust and does not disable
certificate verification.

For a local Neo4j instance, use its configured Bolt URI, for example
`bolt://localhost:7687`. Aura's encrypted `neo4j+s://` URI is supported. URI
credentials are rejected; credentials must be passed through environment
variables.
Schema constraints use Neo4j 5+ Cypher syntax.
The configuration rejects Aura hosts without `neo4j+s://`, remote plaintext
URIs, and the `+ssc` scheme that skips normal certificate authority
verification.

The connection diagnostic reports URI configuration, DNS, TCP, TLS
certificate verification, authentication, and final database access without
printing the URI, username, or password:

```powershell
python -m knowledge_graph.connection
```

## Seed the project taxonomy

```powershell
python -m knowledge_graph.seed_data
```

Seeding creates uniqueness constraints, the six disease/pest nodes, the
`healthy` status node, and the four prediction severity values. It is
idempotent. It deliberately adds no symptoms, treatments, environmental facts,
predictions, sample reports, or fabricated observations.

## Parameterized repository examples

```python
from knowledge_graph.connection import open_repository_from_env

with open_repository_from_env() as repository:
    repository.create_symptom(
        "example_symptom",
        "Example symptom",
        validation_status="needs_expert_review",
    )
    repository.create_relationship(
        "Disease",
        "powdery_mildew",
        "CAUSES",
        "Symptom",
        "example_symptom",
    )
    disease = repository.get_problem_information("powdery_mildew")
    symptoms = repository.get_related_symptoms("powdery_mildew")
    treatments = repository.get_treatments("powdery_mildew")
```

All property values are Cypher parameters. Dynamic labels and relationship
types are selected only from a fixed allowlist. Do not treat unreviewed content
as authoritative advice.

Equivalent Cypher retrieval:

```cypher
MATCH (disease:Disease {slug: $slug})-[:CAUSES]->(symptom:Symptom)
RETURN disease, symptom
```

## Prediction integration and availability

The default `predict_image(image_path)` does not import this package or make a
database connection. A separate opt-in
`predict_image_with_knowledge(image_path)` first runs the same predictor, then
attempts to store the structured result and retrieve related graph information.
If Neo4j configuration, authentication, or access is unavailable, the response
still contains the original AI prediction and reports
`knowledge_status="unavailable"`. No image bytes or filesystem path are stored;
an opaque `image_id` can be supplied directly to the repository if desired.

Neo4j errors are logged without credentials. A model-loading, invalid-image, or
prediction error remains an AI error and is not hidden by this graph fallback.

Unit tests mock the driver and do not require a live Neo4j instance. The
connection command and seed command require a separately configured Neo4j
server or Aura database.

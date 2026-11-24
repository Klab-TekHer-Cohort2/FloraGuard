CREATE_DISEASE = """
MERGE (node:Disease:Problem {slug: $slug})
SET node.name = $name,
    node.kind = 'disease',
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_PEST = """
MERGE (node:Pest:Problem {slug: $slug})
SET node.name = $name,
    node.kind = 'pest',
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_HEALTH_STATUS = """
MERGE (node:HealthStatus:Problem {slug: $slug})
SET node.name = $name,
    node.kind = 'health_status',
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_SYMPTOM = """
MERGE (node:Symptom {slug: $slug})
SET node.name = $name,
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_SEVERITY = """
MERGE (node:Severity {slug: $slug})
SET node.name = $name,
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_ENVIRONMENTAL_CONDITION = """
MERGE (node:EnvironmentalCondition {slug: $slug})
SET node.name = $name,
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

CREATE_TREATMENT = """
MERGE (node:Treatment {slug: $slug})
SET node.name = $name,
    node.validation_status = $validation_status
RETURN properties(node) AS entity
"""

GET_PROBLEM_INFORMATION = """
MATCH (problem:Problem {slug: $slug})
OPTIONAL MATCH (problem)-[relationship]-(related)
WHERE related:Symptom
   OR related:Severity
   OR related:EnvironmentalCondition
   OR related:Treatment
RETURN properties(problem) AS problem,
       collect(CASE WHEN relationship IS NULL THEN null ELSE {
           relationship: type(relationship),
           labels: labels(related),
           properties: properties(related)
       } END) AS related
"""

GET_DISEASE_INFORMATION = """
MATCH (disease:Disease {slug: $slug})
OPTIONAL MATCH (disease)-[relationship]-(related)
WHERE related:Symptom
   OR related:Severity
   OR related:EnvironmentalCondition
   OR related:Treatment
RETURN properties(disease) AS disease,
       collect(CASE WHEN relationship IS NULL THEN null ELSE {
           relationship: type(relationship),
           labels: labels(related),
           properties: properties(related)
       } END) AS related
"""

GET_RELATED_SYMPTOMS = """
MATCH (problem:Problem {slug: $slug})-[:CAUSES]->(symptom:Symptom)
RETURN properties(symptom) AS symptom
ORDER BY symptom.name
"""

GET_PESTS_FOR_SYMPTOM = """
MATCH (pest:Pest)-[:CAUSES]->(symptom:Symptom {slug: $symptom_slug})
RETURN properties(pest) AS pest
ORDER BY pest.name
"""

GET_ENVIRONMENTAL_RELATIONSHIPS = """
MATCH (problem:Problem {slug: $slug})-[relationship]->(condition:EnvironmentalCondition)
WHERE type(relationship) IN ['ASSOCIATED_WITH', 'FAVOURED_BY']
RETURN type(relationship) AS relationship,
       properties(condition) AS condition
ORDER BY condition.name
"""

GET_TREATMENTS = """
MATCH (problem:Problem {slug: $slug})-[:HAS_TREATMENT]->(treatment:Treatment)
RETURN properties(treatment) AS treatment
ORDER BY treatment.name
"""

STORE_PREDICTION = """
MATCH (problem:Problem {slug: $problem})
MERGE (prediction:Prediction {id: $prediction_id})
ON CREATE SET prediction.created_at = $created_at
SET prediction.problem = $problem,
    prediction.candidate_problem = $candidate_problem,
    prediction.confidence = $confidence,
    prediction.severity = $severity,
    prediction.model_version = $model_version
MERGE (prediction)-[:IDENTIFIED]->(problem)
WITH prediction
MERGE (severity:Severity {slug: $severity})
SET severity.name = $severity,
    severity.validation_status = 'prediction_contract_value'
MERGE (prediction)-[:HAS_SEVERITY]->(severity)
FOREACH (_ IN CASE WHEN $image_id IS NULL THEN [] ELSE [1] END |
    MERGE (image:Image {id: $image_id})
    MERGE (prediction)-[:BASED_ON]->(image)
)
FOREACH (_ IN CASE WHEN $location_slug IS NULL THEN [] ELSE [1] END |
    MERGE (location:Location {slug: $location_slug})
    SET location.name = $location_name
    MERGE (prediction)-[:LOCATED_AT]->(location)
)
RETURN properties(prediction) AS prediction
"""

STORE_UNCERTAIN_PREDICTION = """
MERGE (prediction:Prediction {id: $prediction_id})
ON CREATE SET prediction.created_at = $created_at
SET prediction.problem = $problem,
    prediction.candidate_problem = $candidate_problem,
    prediction.confidence = $confidence,
    prediction.severity = $severity,
    prediction.model_version = $model_version
MERGE (severity:Severity {slug: $severity})
SET severity.name = $severity,
    severity.validation_status = 'prediction_contract_value'
MERGE (prediction)-[:HAS_SEVERITY]->(severity)
FOREACH (_ IN CASE WHEN $image_id IS NULL THEN [] ELSE [1] END |
    MERGE (image:Image {id: $image_id})
    MERGE (prediction)-[:BASED_ON]->(image)
)
FOREACH (_ IN CASE WHEN $location_slug IS NULL THEN [] ELSE [1] END |
    MERGE (location:Location {slug: $location_slug})
    SET location.name = $location_name
    MERGE (prediction)-[:LOCATED_AT]->(location)
)
RETURN properties(prediction) AS prediction
"""

GET_PREVIOUS_PREDICTIONS = """
MATCH (prediction:Prediction)
WHERE $problem IS NULL OR prediction.problem = $problem
RETURN properties(prediction) AS prediction
ORDER BY prediction.created_at DESC
LIMIT $limit
"""

NODE_LABELS = {
    "Disease",
    "Pest",
    "HealthStatus",
    "Symptom",
    "Severity",
    "EnvironmentalCondition",
    "Treatment",
    "Rose",
}

RELATIONSHIP_ENDPOINTS = {
    ("Disease", "CAUSES", "Symptom"),
    ("Pest", "CAUSES", "Symptom"),
    ("Disease", "HAS_SEVERITY", "Severity"),
    ("Pest", "HAS_SEVERITY", "Severity"),
    ("Disease", "ASSOCIATED_WITH", "EnvironmentalCondition"),
    ("Pest", "FAVOURED_BY", "EnvironmentalCondition"),
    ("Disease", "HAS_TREATMENT", "Treatment"),
    ("Pest", "HAS_TREATMENT", "Treatment"),
    ("Rose", "HAS_PROBLEM", "Disease"),
    ("Rose", "HAS_PEST", "Pest"),
}


def relationship_query(
    source_label: str,
    relationship: str,
    target_label: str,
) -> str:
    if not all(
        isinstance(value, str)
        for value in (source_label, relationship, target_label)
    ):
        raise ValueError("Graph labels and relationship types must be strings.")
    signature = (source_label, relationship, target_label)
    if source_label not in NODE_LABELS or target_label not in NODE_LABELS:
        raise ValueError("Unsupported graph node type.")
    if signature not in RELATIONSHIP_ENDPOINTS:
        raise ValueError("Unsupported relationship for the selected node types.")
    return f"""
MATCH (source:{source_label} {{slug: $source_slug}})
MATCH (target:{target_label} {{slug: $target_slug}})
MERGE (source)-[edge:{relationship}]->(target)
RETURN type(edge) AS relationship
"""

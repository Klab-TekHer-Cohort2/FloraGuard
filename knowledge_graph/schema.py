SCHEMA_QUERIES = (
    "CREATE CONSTRAINT problem_slug IF NOT EXISTS "
    "FOR (node:Problem) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT symptom_slug IF NOT EXISTS "
    "FOR (node:Symptom) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT severity_slug IF NOT EXISTS "
    "FOR (node:Severity) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT environment_slug IF NOT EXISTS "
    "FOR (node:EnvironmentalCondition) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT treatment_slug IF NOT EXISTS "
    "FOR (node:Treatment) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT rose_slug IF NOT EXISTS "
    "FOR (node:Rose) REQUIRE node.slug IS UNIQUE",
    "CREATE CONSTRAINT image_id IF NOT EXISTS "
    "FOR (node:Image) REQUIRE node.id IS UNIQUE",
    "CREATE CONSTRAINT prediction_id IF NOT EXISTS "
    "FOR (node:Prediction) REQUIRE node.id IS UNIQUE",
    "CREATE CONSTRAINT location_slug IF NOT EXISTS "
    "FOR (node:Location) REQUIRE node.slug IS UNIQUE",
)

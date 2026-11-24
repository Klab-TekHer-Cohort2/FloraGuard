# FloraGuard API contract

Base URL while running locally: `http://127.0.0.1:8000`.
Interactive documentation: `/docs`; machine-readable OpenAPI: `/openapi.json`.
All responses use JSON except the multipart image upload. Times are UTC where
the server assigns them; clients may submit an ISO-8601 timestamp.

## `GET /api/health`

Checks that the API process and SQLite database respond.

Example response:

```json
{"status": "ok", "database": "ok", "graph": "ok"}
```

Returns `503` if the database is unavailable.
`graph` is `"ok"`, `"not_configured"`, or `"unavailable"`; Neo4j is not
required for ordinary report and risk endpoints.

## `POST /api/reports`

Accepts `multipart/form-data` and creates a report. Required:

| Field | Type | Constraints |
|---|---|---|
| `photo` | file | Valid JPEG, PNG, or WebP; maximum size from `MAX_UPLOAD_BYTES` |
| `latitude` | number | -90 through 90 |
| `longitude` | number | -180 through 180 |

Optional: `area_id` (internal zone label, max 100 characters), `timestamp` (ISO-8601).
If timestamp is omitted, the server uses the current time. The server calls the
configured predictor and weather service, stores the report even if weather is
unavailable, calculates risk, and creates/reuses an alert when risk is HIGH.

Example using PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/reports" `
  -F "photo=@C:\photos\rose.jpg" `
  -F "latitude=-1.82" `
  -F "longitude=30.43"
```

Example response (`201 Created`):

```json
{
  "id": 1,
  "photo_path": "c0ffee123456.jpg",
  "problem": "spider_mite",
  "candidate_problem": null,
  "prediction_source": "mock",
  "severity": "medium",
  "confidence": 0.87,
  "latitude": -1.82,
  "longitude": 30.43,
  "area_id": null,
  "created_at": "2026-11-23T08:00:00Z",
  "weather": {
    "status": "available",
    "temperature_c": 28.4,
    "relative_humidity_percent": 48,
    "observed_at": "2026-11-23T10:00"
  },
  "risk_level": "MEDIUM",
  "risk_score": 45,
  "risk_reasons": [
    "1 similar report(s) within 3 km during the last 7 days",
    "Average reported severity is medium",
    "Current weather is a prototype risk factor for spider mite"
  ],
  "alert_status": "none",
  "alert_id": null,
  "is_sample": false
}
```

Possible errors: `400` empty image, `413` image too large, `415` unsupported or
invalid image, `422` invalid/missing form fields, `502` invalid AI response,
`503` AI or database unavailable.

## `GET /api/channels`

Returns the currently supported reporting channels and configured area choices.
The directory may return `null` for the USSD service code or IVR access number
until an actual telecom provider assigns them. Area coordinates are represented
only as availability flags.

## `POST /api/ussd`

Provider-neutral callback for USSD sessions. The telecom adapter must send the
complete accumulated `text` sequence on each callback, with menu choices
separated by `*`. The built-in menu provides report submission, area risk, and
latest-alert lookup. Example complete report sequence:

```json
{
  "session_id": "carrier-session-123",
  "service_code": "*123#",
  "text": "1*1*2*1"
}
```

This sequence selects report, spider mite, medium severity, and the first
configured area. `service_code` is optional; when `USSD_SERVICE_CODE` is
configured and a callback includes a code, it must match. Optional
`latitude` and `longitude` must be supplied together and may be used when the
carrier provides caller location. Successful callback responses use
`{"action":"CONTINUE","text":"..."}` for another menu step or
`{"action":"END","text":"..."}` for completion; text is limited to 160
characters.

## `POST /api/ivr`

Provider-neutral callback for an IVR call. Send `event: "start"` to receive the
welcome prompt. On digit callbacks, `digits` must contain the complete
accumulated keypad sequence, with choices separated by `*`; the carrier adapter
is responsible for collecting and forwarding each sequence. Example:

```json
{
  "session_id": "carrier-call-456",
  "event": "digits",
  "digits": "1*2*3*1"
}
```

This sequence reports thrips, high severity, and the first configured area.
Responses use `action: "COLLECT"` with `speech_text` for another prompt or
`action: "END"` when complete. Optional caller coordinates must be supplied as
a pair. Phone reports do not run the vision model; they store the caller's
selected problem and severity, with null confidence and no image.

### Phone channel configuration and limitations

Set `FLORAGUARD_AREAS` to a JSON array of verified zones; each has `id` and
`name`, and may have both `latitude` and `longitude`. The default menu includes
Gishari plus an “Other” choice. “Other” without carrier coordinates stays
unlocated and gets no fabricated weather. `USSD_SERVICE_CODE` and
`IVR_ACCESS_NUMBER` are optional directory values, not telecom integrations.
The prototype has no carrier callback authentication, session-state storage,
or direct SMS/voice delivery; connect a provider adapter before field use.
All endpoints are unauthenticated and must not be exposed publicly as-is.

## `GET /api/reports`

Internal report listing. Supports `problem` (one allowed class), `limit` (1-500,
default 100), and `offset` (default 0).

Example: `GET /api/reports?problem=spider_mite&limit=20`

Returns `{"items": [...], "total": 1, "limit": 20, "offset": 0}`. A report item
uses the `POST /api/reports` response shape. This endpoint includes report
coordinates and internal area labels; do not expose it as the public map feed.

## `GET /api/reports/{id}`

Returns one internal report using the same report response shape. Returns `404`
when the ID does not exist.

## `GET /api/map/reports`

Returns aggregated, recent, area-level report summaries. It does not return
photo paths or farm/area identifiers. Coordinates are rounded to 0.01 degrees
for approximate map placement.

Example response:

```json
{
  "areas": [
    {
      "latitude": -1.82,
      "longitude": 30.43,
      "risk_level": "HIGH",
      "problem": "spider_mite",
      "report_count": 5,
      "area": "Approx. area -1.82, 30.43"
    }
  ],
  "generated_at": "2026-11-23T08:00:00Z",
  "sample_data_included": true
}
```

## `GET /api/risk`

Calculates a current rule-based risk estimate. Required query parameters:
`latitude`, `longitude`, and `problem` (one allowed class).

Example: `GET /api/risk?latitude=-1.82&longitude=30.43&problem=spider_mite`

Example response:

```json
{
  "problem": "spider_mite",
  "risk_level": "HIGH",
  "score": 85,
  "similar_report_count": 5,
  "radius_km": 3,
  "window_days": 7,
  "reasons": [
    "5 similar report(s) within 3 km during the last 7 days",
    "Average reported severity is medium",
    "Current weather is a prototype risk factor for spider mite"
  ]
}
```

This is a community-level estimate, not a diagnosis or confirmation of spread.
If weather is unavailable, the response explains that no weather points were
added.

## `GET /api/alerts`

Returns generated alerts, newest first. Supports `limit` (1-500, default 100)
and `offset` (default 0). Response shape:

```json
{
  "items": [
    {
      "id": 1,
      "problem": "spider_mite",
      "risk_level": "HIGH",
      "score": 85,
      "affected_area": "Approx. area -1.82, 30.43",
      "report_count": 5,
      "message": "Several recent reports suggest high spider mite risk ...",
      "preventive_actions": [
        "Inspect the undersides of leaves and monitor affected plants.",
        "Ask an agronomist to confirm the cause before choosing treatment."
      ],
      "created_at": "2026-11-23T08:00:00Z",
      "is_sample": false
    }
  ],
  "total": 1
}
```

Invalid pagination returns `422`. Alerts are deduplicated by approximate area
and problem for 24 hours.

## `POST /api/rag/query`

Requires configured and reachable Neo4j. It retrieves a bounded set of relevant
graph records and returns an evidence-grounded explanation. It never calculates
or overrides the official risk level. An optional LLM receives only the
retrieved context and must cite known report IDs. Without an LLM key, the API
returns a deterministic retrieved-data summary.

Request JSON:

```json
{
  "question": "Why is spider mite risk high around Gishari?",
  "problem": "spider_mite",
  "area": "Gishari",
  "days": 7,
  "radius_km": 3
}
```

`question` is required (4-1000 characters). `problem`, `area`, `latitude`,
`longitude`, `days` (1-30, default 7), and `radius_km` (>0-50, default 3) are
optional. Coordinates must be supplied together. A Gishari query without
coordinates uses the configurable approximate center. Unknown named areas are
not guessed.

Example response:

```json
{
  "question": "Why is spider mite risk high around Gishari?",
  "answer": "The graph contains 5 spider mite report(s) in the Gishari area from the last 7 days. Reported severity counts: 3 medium, 2 high. Recorded average temperature was 29.0 °C. Recorded average relative humidity was 45.0%. 5 stored HIGH risk result(s); the rule engine remains authoritative.",
  "risk_level": "HIGH",
  "sources": [
    {"type": "report", "id": "102", "is_sample": true},
    {"type": "report", "id": "108", "is_sample": false}
  ],
  "data_status": "sample_and_real",
  "explanation_source": "llm",
  "explanation_status": "generated",
  "retrieved_context": {
    "filters": {
      "problem": "spider_mite",
      "area": "Gishari",
      "latitude": -1.82,
      "longitude": 30.43,
      "radius_km": 3,
      "days": 7
    },
    "report_count": 5,
    "severity_counts": {"medium": 3, "high": 2}
  }
}
```

Values above are illustrative; actual values come from Neo4j. `data_status`
distinguishes `real`, `sample`, or `sample_and_real`. `explanation_source` is
`llm` or `retrieval_summary`; `explanation_status` distinguishes successful
generation, an unconfigured LLM, or an LLM failure/fallback. If no matching reports are found, or the question
is unrelated to FloraGuard data, the API returns HTTP 200 with
`"Insufficient data is available to determine this."`, no sources, and
`data_status: "insufficient"`. Unavailable Neo4j returns `503`; invalid input
returns `422`.

## Allowed AI values

- `problem`: `healthy`, `spider_mite`, `thrips`, `powdery_mildew`,
  `downy_mildew`, `grey_mould`, `black_spot`, `uncertain`
- `severity`: `low`, `medium`, `high`, `unknown`
- `confidence`: number from `0.0` to `1.0`

If confidence is below `CONFIDENCE_THRESHOLD`, the stored problem becomes
`uncertain`, the original class is retained as `candidate_problem`, and
severity becomes `unknown`. The Member 1 model adapter reports the active
version in `prediction_source`, for example
`model:app.ai.member1_adapter:version:v1`; the backend still only requires the
problem, severity, confidence, and optional candidate problem.

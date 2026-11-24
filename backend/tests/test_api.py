from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.weather import OpenMeteoWeather


class FakeWeather:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def current(self, latitude, longitude):
        self.calls.append((latitude, longitude))
        if self.fail:
            raise TimeoutError("test weather timeout")
        if latitude is None or longitude is None:
            return {
                "status": "unavailable",
                "temperature": None,
                "humidity": None,
                "observed_at": None,
                "source": "Open-Meteo",
            }
        return {
            "status": "available",
            "temperature": 26.0,
            "humidity": 48.0,
            "observed_at": "2026-11-24T08:00:00Z",
            "source": "test weather",
        }


def build_client(tmp_path, predictor=None, weather=None, **settings_overrides):
    settings = Settings(
        database_path=tmp_path / "floraguard-test.sqlite",
        upload_dir=tmp_path / "uploads",
        areas=("Gishari Flower Park", "Demo Area"),
        area_coordinates={},
        ussd_code="*XXX#",
        confidence_threshold=0.60,
        risk_window_days=7,
        risk_radius_km=5,
        risk_medium_threshold=30,
        risk_high_threshold=65,
        max_image_size_bytes=10 * 1024 * 1024,
        weather_timeout_seconds=0.1,
        predictor_path=None,
        cors_origins=("http://localhost:5173",),
    )
    if settings_overrides:
        settings = replace(settings, **settings_overrides)
    app = create_app(
        settings=settings,
        predictor_function=predictor,
        weather_service=weather or FakeWeather(),
    )
    return TestClient(app)


def submit_ussd_report(client, problem="1", severity="3", area="1"):
    return client.post(
        "/api/ussd",
        json={"session_id": "test-session", "text": f"1*{problem}*{severity}*{area}"},
    )


def submit_ivr_report(client, session="test-ivr", problem="1", severity="3", area="1"):
    client.post("/api/ivr", json={"session_id": session})
    for digit in ("1", problem, severity, area):
        response = client.post("/api/ivr", json={"session_id": session, "digit": digit})
    return response


def test_health_endpoint_and_database_status(tmp_path):
    client = build_client(tmp_path)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert response.json()["ai_model"] == "unavailable"


def test_root_describes_floraguard_backend(tmp_path):
    response = build_client(tmp_path).get("/")
    assert response.status_code == 200
    assert response.json()["project"] == "FloraGuard"


def test_smartphone_report_uses_model_weather_and_stores_result(tmp_path):
    weather = FakeWeather()
    client = build_client(
        tmp_path,
        predictor=lambda _: {
            "problem": "spider_mite",
            "severity": "medium",
            "confidence": 0.87,
        },
        weather=weather,
    )
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffsample image", "image/jpeg")},
        data={"latitude": "-1.9", "longitude": "29.8", "area": "Gishari Flower Park"},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["input_channel"] == "SMARTPHONE"
    assert report["predicted_problem"] == "spider_mite"
    assert report["confidence"] == pytest.approx(0.87)
    assert report["image_available"] is True
    assert report["temperature"] == 26.0
    assert weather.calls == [(-1.9, 29.8)]
    stored = client.get(f"/api/reports/{report['id']}").json()
    assert stored["area"] == "Gishari Flower Park"
    assert stored["ai_status"] == "available"


def test_low_confidence_prediction_is_marked_uncertain(tmp_path):
    client = build_client(
        tmp_path,
        predictor=lambda _: {
            "problem": "thrips",
            "severity": "high",
            "confidence": 0.42,
        },
    )
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
    )
    assert response.status_code == 201
    assert response.json()["predicted_problem"] == "uncertain"
    assert response.json()["severity"] == "unknown"
    assert response.json()["confidence"] == pytest.approx(0.42)


def test_invalid_model_output_does_not_drop_the_report(tmp_path):
    client = build_client(
        tmp_path,
        predictor=lambda _: {
            "problem": "unknown-label",
            "severity": "high",
            "confidence": 2,
        },
    )
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
    )
    assert response.status_code == 201
    assert response.json()["predicted_problem"] == "uncertain"
    assert response.json()["confidence"] is None
    assert response.json()["ai_status"] == "unavailable"


def test_missing_ai_model_records_uncertain_without_fake_confidence(tmp_path):
    client = build_client(tmp_path)
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["predicted_problem"] == "uncertain"
    assert report["confidence"] is None
    assert report["ai_status"] == "unavailable"


def test_photo_mime_type_is_validated(tmp_path):
    response = build_client(tmp_path).post(
        "/api/reports",
        files={"image": ("rose.gif", b"GIF89a", "image/gif")},
    )
    assert response.status_code == 415


def test_photo_content_signature_is_validated(tmp_path):
    response = build_client(tmp_path).post(
        "/api/reports",
        files={"image": ("rose.jpg", b"not a jpeg", "image/jpeg")},
    )
    assert response.status_code == 400


def test_photo_size_limit_is_enforced(tmp_path):
    client = build_client(tmp_path, max_image_size_bytes=10)
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xff" + b"x" * 10, "image/jpeg")},
    )
    assert response.status_code == 413


def test_coordinates_must_be_provided_as_a_pair(tmp_path):
    response = build_client(tmp_path).post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
        data={"latitude": "-1.9"},
    )
    assert response.status_code == 422


def test_weather_failure_does_not_block_report_creation(tmp_path):
    client = build_client(
        tmp_path,
        predictor=lambda _: {
            "problem": "black_spot",
            "severity": "medium",
            "confidence": 0.8,
        },
        weather=FakeWeather(fail=True),
    )
    response = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
        data={"latitude": "-1.9", "longitude": "29.8"},
    )
    assert response.status_code == 201
    assert response.json()["weather_status"] == "unavailable"
    assert response.json()["temperature"] is None


def test_open_meteo_service_returns_unavailable_without_coordinates():
    result = OpenMeteoWeather().current(None, None)
    assert result["status"] == "unavailable"
    assert result["temperature"] is None
    assert result["humidity"] is None


def test_ussd_menu_and_observation_submission(tmp_path):
    client = build_client(tmp_path)
    menu = client.post("/api/ussd", json={"session_id": "s1", "text": ""})
    assert menu.status_code == 200
    assert menu.json()["message"].startswith("CON FloraGuard")
    response = submit_ussd_report(client)
    assert response.status_code == 200
    report = response.json()["report"]
    assert response.json()["action"] == "end"
    assert report["input_channel"] == "USSD"
    assert report["reported_problem"] == "spider_mite"
    assert report["predicted_problem"] is None
    assert report["confidence"] is None
    assert report["ai_status"] == "not_applicable"
    assert report["image_available"] is False


def test_invalid_ussd_selection_does_not_create_report(tmp_path):
    client = build_client(tmp_path)
    response = client.post(
        "/api/ussd",
        json={"session_id": "s2", "text": "1*99"},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "continue"
    assert client.get("/api/reports").json() == []


def test_ussd_latest_alert_response(tmp_path):
    client = build_client(tmp_path)
    for _ in range(5):
        submit_ussd_report(client)
    response = client.post(
        "/api/ussd",
        json={"session_id": "s3", "text": "3"},
    )
    assert response.status_code == 200
    assert response.json()["message"].startswith("END Spider mite risk is HIGH")


def test_ivr_keypad_flow_creates_observation(tmp_path):
    client = build_client(tmp_path)
    response = submit_ivr_report(client)
    assert response.status_code == 200
    report = response.json()["report"]
    assert response.json()["state"] == "done"
    assert report["input_channel"] == "IVR"
    assert report["reported_problem"] == "spider_mite"
    assert report["confidence"] is None
    assert report["image_available"] is False


def test_ivr_welcome_and_latest_alert_voice_response(tmp_path):
    client = build_client(tmp_path)
    welcome = client.post("/api/ivr", json={"session_id": "voice-1"})
    assert welcome.status_code == 200
    assert "Welcome to FloraGuard" in welcome.json()["message"]
    for _ in range(5):
        submit_ussd_report(client)
    alert = client.post(
        "/api/ivr",
        json={"session_id": "voice-alert", "digit": "2"},
    )
    assert alert.status_code == 200
    assert alert.json()["action"] == "end"
    assert "High risk alert" in alert.json()["message"]


def test_three_channels_share_risk_and_generate_high_alert(tmp_path):
    client = build_client(
        tmp_path,
        predictor=lambda _: {
            "problem": "spider_mite",
            "severity": "high",
            "confidence": 0.9,
        },
    )
    photo = client.post(
        "/api/reports",
        files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
    )
    assert photo.status_code == 201
    assert submit_ussd_report(client).status_code == 200
    assert submit_ussd_report(client).status_code == 200
    assert submit_ivr_report(client, session="voice-mixed-1").status_code == 200
    final_report = submit_ivr_report(client, session="voice-mixed-2").json()["report"]
    assert final_report["risk_level"] == "HIGH"
    assert final_report["risk_score"] >= 65
    assert final_report["alert_generated"] is True
    reports = client.get("/api/reports").json()
    assert {report["input_channel"] for report in reports} == {"SMARTPHONE", "USSD", "IVR"}
    assert client.get("/api/alerts").json()


def test_area_risk_endpoint_aggregates_recent_observations(tmp_path):
    client = build_client(tmp_path)
    for _ in range(3):
        submit_ussd_report(client, severity="2")
    response = client.get("/api/risk", params={"area": "Gishari Flower Park"})
    assert response.status_code == 200
    assert response.json()["risk_level"] == "MEDIUM"
    assert response.json()["report_count"] == 3
    assert "prototype rule-based" in response.json()["prototype_notice"].lower()


def test_map_endpoint_returns_coarse_area_only_data(tmp_path):
    client = build_client(tmp_path)
    for _ in range(2):
        client.post(
            "/api/reports",
            files={"image": ("rose.jpg", b"\xff\xd8\xffphoto", "image/jpeg")},
            data={
                "latitude": "-1.91234",
                "longitude": "29.81234",
                "area": "Gishari Flower Park",
            },
        )
    response = client.get("/api/map/reports")
    assert response.status_code == 200
    area = response.json()["areas"][0]
    assert area["report_count"] == 2
    assert area["latitude"] == -1.91
    assert area["longitude"] == 29.81
    assert "report_id" not in area
    assert "farmer_name" not in area


def test_report_not_found_and_invalid_area_are_explicit(tmp_path):
    client = build_client(tmp_path)
    assert client.get("/api/reports/999").status_code == 404
    assert client.get("/api/risk", params={"area": "Unconfigured Area"}).status_code == 422


def test_seeded_demo_records_are_explicitly_sample_data(tmp_path):
    from app.database import Database
    from app.seed_demo import seed_demo

    database = Database(tmp_path / "sample.sqlite")
    count = seed_demo(database)
    samples = database.list_reports(limit=100)
    assert count == 11
    assert all(report["is_sample"] for report in samples)
    assert {report["risk_level"] for report in samples} >= {"LOW", "MEDIUM", "HIGH"}
    assert seed_demo(database) == 0

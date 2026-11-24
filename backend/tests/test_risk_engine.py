from datetime import datetime, timezone

from app.risk_engine import RiskEngine


def report(channel="USSD", severity="medium", latitude=None, longitude=None):
    return {
        "input_channel": channel,
        "reported_problem": "spider_mite",
        "predicted_problem": None,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "area": "Test Area",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def evaluate(current, history):
    return RiskEngine(window_days=7, radius_km=5).evaluate(
        current,
        history,
        {"temperature": None, "humidity": None},
    )


def test_one_low_severity_case_stays_low():
    current = report(severity="low")
    result = evaluate(current, [current])
    assert result["risk_level"] == "LOW"
    assert result["risk_score"] == 2


def test_multiple_medium_cases_raise_medium_risk():
    current = report()
    history = [report("SMARTPHONE"), report("USSD"), report("IVR"), current]
    result = evaluate(current, history)
    assert result["risk_level"] == "MEDIUM"
    assert any("4 similar reports" in reason for reason in result["reasons"])


def test_five_high_cases_raise_high_risk():
    current = report(severity="high")
    result = evaluate(current, [report(severity="high") for _ in range(4)] + [current])
    assert result["risk_level"] == "HIGH"
    assert result["risk_score"] >= 65


def test_all_reporting_channels_contribute_to_shared_risk():
    current = report("IVR")
    history = [report("SMARTPHONE"), report("USSD"), current]
    result = evaluate(current, history)
    assert result["risk_level"] == "MEDIUM"


def test_gps_reports_beyond_radius_do_not_cluster_even_with_same_area_label():
    current = report(latitude=0, longitude=0)
    far_reports = [
        report(latitude=1, longitude=1),
        report(latitude=1.1, longitude=1.1),
        report(latitude=1.2, longitude=1.2),
    ]
    result = evaluate(current, far_reports)
    assert result["risk_level"] == "LOW"
    assert result["risk_score"] == 0

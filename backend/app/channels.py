from datetime import timedelta
from typing import Any

from .config import Settings
from .database import Database
from .services import ReportService, utc_now

PROBLEMS = {
    "1": "spider_mite",
    "2": "thrips",
    "3": "powdery_mildew",
    "4": "downy_mildew",
    "5": "grey_mould",
    "6": "black_spot",
    "7": "uncertain",
}
SEVERITIES = {"1": "low", "2": "medium", "3": "high", "4": "unknown"}


def _continue(message: str, **extra: Any) -> dict[str, Any]:
    return {"action": "continue", "message": f"CON {message}", **extra}


def _end(message: str, **extra: Any) -> dict[str, Any]:
    return {"action": "end", "message": f"END {message}", **extra}


def _main_menu() -> str:
    return "FloraGuard\\n1. Report a problem\\n2. Check area risk\\n3. Latest alert\\n4. Help"


def _problem_menu() -> str:
    return (
        "Select observed problem:\\n1. Spider mite\\n2. Thrips\\n3. Powdery mildew"
        "\\n4. Downy mildew\\n5. Grey mould\\n6. Black spot\\n7. Not sure"
    )


def _severity_menu() -> str:
    return "Select severity:\\n1. Low\\n2. Medium\\n3. High\\n4. Not sure"


def _area_menu(areas: tuple[str, ...]) -> str:
    return "Select area:\\n" + "\\n".join(
        f"{index}. {area}" for index, area in enumerate(areas, start=1)
    )


def _risk_text(result: dict[str, Any]) -> str:
    return (
        f"Risk in {result['area']}: {result['risk_level']} "
        f"({result['risk_score']}/100). {result['reasons'][0]}"
    )


def handle_ussd(
    request: dict[str, Any],
    settings: Settings,
    database: Database,
    reports: ReportService,
) -> dict[str, Any]:
    text = request.get("text", "").strip()
    parts = text.split("*") if text else []
    area = request.get("area") or (settings.areas[0] if settings.areas else None)

    if not parts:
        return _continue(_main_menu(), ussd_code=settings.ussd_code)
    if parts[0] == "4":
        return _end(
            "FloraGuard helps rose growers report crop problems and check community warnings."
        )
    if parts[0] == "2":
        if not area:
            return _end("No reporting area is configured.")
        return _end(_risk_text(reports.area_risk(area)))
    if parts[0] == "3":
        alerts = database.list_alerts(area=area, limit=1)
        if not alerts:
            return _end("There are no high-risk alerts recorded for this area.")
        alert = alerts[0]
        return _end(f"{alert['problem'].replace('_', ' ').capitalize()} risk is HIGH in {alert['area']}.")
    if parts[0] != "1":
        return _continue("Invalid choice.\\n" + _main_menu())
    if len(parts) == 1:
        return _continue(_problem_menu())
    problem = PROBLEMS.get(parts[1])
    if not problem:
        return _continue("Invalid problem.\\n" + _problem_menu())
    if len(parts) == 2:
        return _continue(_severity_menu())
    severity = SEVERITIES.get(parts[2])
    if not severity:
        return _continue("Invalid severity.\\n" + _severity_menu())
    if len(parts) == 3:
        if not settings.areas:
            return _end("No reporting areas are configured.")
        return _continue(_area_menu(settings.areas))
    if len(parts) != 4 or not parts[3].isdigit():
        return _continue("Invalid area.\\n" + _area_menu(settings.areas))

    index = int(parts[3]) - 1
    if index < 0 or index >= len(settings.areas):
        return _continue("Invalid area.\\n" + _area_menu(settings.areas))
    selected_area = settings.areas[index]
    report = reports.create_observation(
        input_channel="USSD",
        problem=problem,
        severity=severity,
        area=selected_area,
    )
    return _end(
        f"Report {report['id']} received. Area risk: {report['risk_level']}.",
        report=report,
    )


def handle_ivr(
    request: dict[str, Any],
    settings: Settings,
    database: Database,
    reports: ReportService,
) -> dict[str, Any]:
    session_id = request["session_id"]
    session = database.get_ivr_session(session_id) or {
        "session_id": session_id,
        "state": "main",
        "selected_problem": None,
        "selected_severity": None,
        "selected_area": None,
    }
    digit = request.get("digit")
    if digit is None:
        return _continue(
            "Welcome to FloraGuard. Press 1 to report a flower problem, "
            "2 to hear the latest alert, or 3 to hear area risk.",
            state="main",
        )

    state = session["state"]
    response = ""
    next_state = state
    report = None

    if state == "main":
        if digit == "1":
            next_state = "problem"
            response = (
                "Press 1 for spider mites, 2 for thrips, 3 for powdery mildew, "
                "4 for downy mildew, 5 for grey mould, 6 for black spot, "
                "or 7 if you are not sure."
            )
        elif digit == "2":
            area = request.get("area") or (settings.areas[0] if settings.areas else None)
            alerts = database.list_alerts(area=area, limit=1)
            if alerts:
                alert = alerts[0]
                response = (
                    f"High risk alert for {alert['area']}: "
                    f"{alert['problem'].replace('_', ' ')}. {alert['guidance']}"
                )
            else:
                response = "There are no high-risk alerts recorded for this area."
            next_state = "done"
        elif digit == "3":
            area = request.get("area") or (settings.areas[0] if settings.areas else None)
            if not area:
                response = "No reporting area is configured."
            else:
                response = _risk_text(reports.area_risk(area))
            next_state = "done"
        else:
            response = "That option is not available. Press 1 to report, 2 for the latest alert, or 3 for area risk."
    elif state == "problem":
        problem = PROBLEMS.get(digit)
        if problem:
            session["selected_problem"] = problem
            next_state = "severity"
            response = "Press 1 for low severity, 2 for medium, 3 for high, or 4 if you are not sure."
        else:
            response = "That option is not available. " + _problem_menu().replace("\\n", " ")
    elif state == "severity":
        severity = SEVERITIES.get(digit)
        if severity:
            session["selected_severity"] = severity
            if settings.areas:
                next_state = "area"
                response = "Choose your area. " + _area_menu(settings.areas).replace("\\n", " ")
            else:
                response = "No reporting areas are configured. Goodbye."
                next_state = "done"
        else:
            response = "That severity is not available. Press 1 for low, 2 for medium, 3 for high, or 4 if unsure."
    elif state == "area":
        if digit.isdigit() and 1 <= int(digit) <= len(settings.areas):
            selected_area = settings.areas[int(digit) - 1]
            session["selected_area"] = selected_area
            report = reports.create_observation(
                input_channel="IVR",
                problem=session["selected_problem"],
                severity=session["selected_severity"],
                area=selected_area,
                latitude=request.get("latitude"),
                longitude=request.get("longitude"),
            )
            response = (
                f"Your report {report['id']} was received. "
                f"Current area risk is {report['risk_level']}. Goodbye."
            )
            next_state = "done"
        else:
            response = "That area is not available. " + _area_menu(settings.areas).replace("\\n", " ")
    else:
        return _end("This call has already finished. Goodbye.", state="done")

    session["state"] = next_state
    session["updated_at"] = utc_now().isoformat()
    database.save_ivr_session(session)
    if next_state == "done":
        return _end(response, state=next_state, report=report)
    return _continue(response, state=next_state)

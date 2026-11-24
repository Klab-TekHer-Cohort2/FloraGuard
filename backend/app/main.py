import logging
import secrets
from pathlib import Path
from typing import Literal

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .channels import handle_ivr, handle_ussd
from .config import Settings
from .database import Database
from .predictor import Predictor
from .schemas import AlertResponse, IVRRequest, ReportResponse, RiskResponse, USSDRequest
from .services import ReportService
from .weather import OpenMeteoWeather

logger = logging.getLogger("floraguard.api")

IMAGE_TYPES = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (
        ".webp",
        lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    ),
}


def create_app(
    settings: Settings | None = None,
    predictor_function=None,
    weather_service: OpenMeteoWeather | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
    database = Database(config.database_path)
    database.initialize()
    config.upload_dir.mkdir(parents=True, exist_ok=True)
    predictor = Predictor(config, predict_function=predictor_function)
    weather = weather_service or OpenMeteoWeather(config.weather_timeout_seconds)
    report_service = ReportService(database, config, predictor, weather)

    app = FastAPI(
        title="FloraGuard API",
        description=(
            "Prototype rose health reporting and transparent, rule-based community risk indicators. "
            "Risk levels are not scientifically validated outbreak predictions."
        ),
        version="1.0.0",
    )
    app.state.settings = config
    app.state.database = database
    app.state.predictor = predictor
    app.state.weather = weather
    app.state.report_service = report_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.mount("/uploads", StaticFiles(directory=str(config.upload_dir)), name="uploads")

    @app.get("/", tags=["Health"], summary="Backend service information")
    def root():
        return {
            "project": "FloraGuard",
            "api": "/api",
            "docs": "/docs",
            "status": "online",
        }

    @app.get("/api/health", tags=["Health"], summary="Check backend and database health")
    def health():
        try:
            database_ok = database.health()
        except Exception:
            logger.exception("FloraGuard database health check failed.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable.",
            )
        return {
            "status": "healthy" if database_ok else "unavailable",
            "database": "connected" if database_ok else "unavailable",
            "ai_model": "configured" if predictor.available else "unavailable",
            "weather_provider": "Open-Meteo",
            "weather_lookup": "on demand; unavailable weather does not block reports",
            "risk_engine": "prototype rule-based",
        }

    @app.post(
        "/api/reports",
        response_model=ReportResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Reports"],
        summary="Submit and analyze a smartphone rose photo",
        description=(
            "Accepts JPEG, PNG, or WebP multipart image, runs the configured computer-vision "
            "adapter, stores the report, attempts weather lookup, computes area risk, and "
            "creates an alert when risk is HIGH. Missing model/weather does not fabricate data."
        ),
    )
    async def create_smartphone_report(
        image: UploadFile = File(..., description="Rose leaf, flower, bud, stem, or pest photo"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        area: str | None = Form(default=None, max_length=100),
        timestamp: str | None = Form(default=None, max_length=40),
    ):
        if (latitude is None) != (longitude is None):
            raise HTTPException(
                status_code=422,
                detail="Latitude and longitude must be supplied together.",
            )
        mime_type = image.content_type or ""
        image_type = IMAGE_TYPES.get(mime_type)
        if image_type is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Image must be JPEG, PNG, or WebP.",
            )
        content = await image.read(config.max_image_size_bytes + 1)
        if len(content) > config.max_image_size_bytes:
            raise HTTPException(
                status_code=413,
                detail="Image exceeds the configured size limit.",
            )
        extension, signature_check = image_type
        if not signature_check(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image content does not match its declared image type.",
            )
        file_path = config.upload_dir / f"{secrets.token_hex(16)}{extension}"
        try:
            file_path.write_bytes(content)
            return await run_in_threadpool(
                report_service.create_smartphone_report,
                file_path,
                latitude,
                longitude,
                area,
                timestamp,
            )
        except ValueError as exc:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception:
            file_path.unlink(missing_ok=True)
            logger.exception("Smartphone report could not be stored.")
            raise HTTPException(
                status_code=500,
                detail="Report could not be stored. Please try again.",
            )

    @app.get(
        "/api/reports",
        response_model=list[ReportResponse],
        tags=["Reports"],
        summary="List reports",
    )
    def list_reports(
        area: str | None = Query(default=None, max_length=100),
        input_channel: Literal["SMARTPHONE", "USSD", "IVR"] | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ):
        return database.list_reports(area=area, input_channel=input_channel, limit=limit)

    @app.get(
        "/api/reports/{report_id}",
        response_model=ReportResponse,
        tags=["Reports"],
        summary="Get one report",
    )
    def get_report(report_id: int):
        report = database.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")
        return report

    @app.get(
        "/api/map/reports",
        tags=["Map data"],
        summary="Return privacy-preserving area aggregates",
        description="Returns only configured area aggregates, rounded centroids, counts, and risk. No report or farm identifiers are returned.",
    )
    def map_reports():
        reports = database.list_reports(limit=5000)
        areas = []
        for area in config.areas:
            area_reports = [report for report in reports if report["area"] == area]
            if not area_reports:
                continue
            observed = [
                report["reported_problem"] or report["predicted_problem"]
                for report in area_reports
            ]
            observed = [
                problem for problem in observed if problem and problem not in {"healthy", "uncertain"}
            ]
            dominant_problem = (
                max(set(observed), key=observed.count) if observed else None
            )
            points = [
                report
                for report in area_reports
                if report["latitude"] is not None and report["longitude"] is not None
            ]
            configured_coords = config.coordinates_for_area(area)
            if points:
                latitude = round(sum(item["latitude"] for item in points) / len(points), 2)
                longitude = round(sum(item["longitude"] for item in points) / len(points), 2)
            elif configured_coords:
                latitude, longitude = configured_coords
            else:
                latitude = longitude = None
            area_risk = report_service.area_risk(area, dominant_problem)
            areas.append(
                {
                    "area": area,
                    "latitude": latitude,
                    "longitude": longitude,
                    "risk_level": area_risk["risk_level"],
                    "risk_score": area_risk["risk_score"],
                    "problem": dominant_problem,
                    "report_count": len(area_reports),
                    "is_sample": all(report["is_sample"] for report in area_reports),
                    "contains_sample_data": any(report["is_sample"] for report in area_reports),
                }
            )
        return {
            "areas": areas,
            "sample_data": bool(reports) and all(report["is_sample"] for report in reports),
            "contains_sample_data": any(report["is_sample"] for report in reports),
        }

    @app.get(
        "/api/risk",
        response_model=RiskResponse,
        tags=["Risk"],
        summary="Calculate the current prototype risk indicator for an area",
    )
    def get_area_risk(
        area: str | None = Query(default=None, max_length=100),
        problem: str | None = Query(default=None, max_length=40),
    ):
        selected_area = area or (config.areas[0] if config.areas else None)
        if not selected_area:
            raise HTTPException(status_code=503, detail="No reporting area is configured.")
        if problem and problem not in {
            "healthy", "spider_mite", "thrips", "powdery_mildew", "downy_mildew",
            "grey_mould", "black_spot", "uncertain",
        }:
            raise HTTPException(status_code=422, detail="Unsupported problem type.")
        try:
            return report_service.area_risk(selected_area, problem)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/alerts",
        response_model=list[AlertResponse],
        tags=["Alerts"],
        summary="List high-risk alerts",
    )
    def list_alerts(
        area: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        return database.list_alerts(area=area, limit=limit)

    @app.post("/api/ussd", tags=["USSD"], summary="Process a provider-independent USSD callback")
    def ussd_callback(payload: USSDRequest, request: Request):
        try:
            return handle_ussd(
                payload.model_dump(),
                request.app.state.settings,
                request.app.state.database,
                request.app.state.report_service,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/ivr", tags=["IVR"], summary="Process one provider-independent IVR keypad event")
    def ivr_callback(payload: IVRRequest, request: Request):
        try:
            return handle_ivr(
                payload.model_dump(),
                request.app.state.settings,
                request.app.state.database,
                request.app.state.report_service,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()

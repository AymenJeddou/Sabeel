"""GET /map?bbox= — Sprint1_Action_Plan.md Section 4.5. Stub sample data for Sprint 1."""

import uuid

from fastapi import APIRouter, Query

from backend.app.schemas import MapReport
from backend.app.status import ReportStatus

router = APIRouter(tags=["map"])

_SAMPLE_REPORTS = [
    MapReport(report_id=uuid.uuid4(), lat=36.8065, lon=10.1815, score=4, status=ReportStatus.CONFIRMED, cluster_id=None),
    MapReport(report_id=uuid.uuid4(), lat=36.8100, lon=10.1900, score=2, status=ReportStatus.NEW, cluster_id=None),
]


@router.get("/map", response_model=list[MapReport])
async def get_map(bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat")) -> list[MapReport]:
    return _SAMPLE_REPORTS

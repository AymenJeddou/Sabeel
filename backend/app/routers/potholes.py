"""Potholes: detail, officer actions, citizen confirmations, work-sheet review.

Citizen (no token):   GET /potholes/{id}, POST /potholes/{id}/confirmations
Officer (Bearer):     PATCH /potholes/{id}, POST /potholes/{id}/fix,
                      POST /potholes/{id}/feedback, /potholes/{id}/sheet*
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi import status as http
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import jobs, privacy, storage
from backend.app.auth import can_see, ensure_scope, optional_office, require_office
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.db_models import Office, Pothole, Report
from backend.app.feedback import label_pothole
from backend.app.geo.enrichment import haversine_m
from backend.app.pdf import render_sheet_pdf, sheet_fingerprint
from backend.app.potholes import InvalidTransition, add_confirmation, record_event, set_status
from backend.app.ratelimit import limit
from backend.app.routers.reports import read_photo
from backend.app.schemas import (
    ConfirmationIn,
    ConfirmationOut,
    FeedbackIn,
    SheetEdit,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from backend.app.serialize import office_map, officer_pothole, public_pothole
from backend.app.status import ReportStatus as S
from backend.app.vision_client import run_inference_async

router = APIRouter(prefix="/potholes", tags=["potholes"])
officer_limit = Depends(limit("officer", 120, 60, by="token"))


async def get_pothole(db: AsyncSession, pothole_id: uuid.UUID) -> Pothole:
    p = await db.get(Pothole, pothole_id)
    if p is None:
        raise HTTPException(http.HTTP_404_NOT_FOUND, "Unknown pothole")
    return p


async def get_scoped(db: AsyncSession, pothole_id: uuid.UUID, office: Office) -> Pothole:
    p = await get_pothole(db, pothole_id)
    ensure_scope(office, p)
    return p


def actor(office: Office) -> str:
    return f"office:{office.code}"


@router.get("/{pothole_id}")
async def pothole_detail(
    pothole_id: uuid.UUID, db: AsyncSession = Depends(get_db), office: Office | None = Depends(optional_office)
) -> dict:
    """Public-safe detail; an officer in scope also gets photos, events, sheet and priority."""
    p = await get_pothole(db, pothole_id)
    offices = await office_map(db)
    if office and can_see(office, p):
        return await officer_pothole(db, p, offices)
    from backend.app.schemas import PublicPothole

    return PublicPothole(**public_pothole(p, offices)).model_dump()


@router.patch("/{pothole_id}", response_model=StatusUpdateResponse, dependencies=[officer_limit])
async def update_status(
    pothole_id: uuid.UUID,
    body: StatusUpdateRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    office: Office = Depends(require_office),
) -> dict:
    """Officer moves a pothole: `confirmed` (manual confirmation of a pothole the
    model or the citizens could not confirm) or `rejected` (false positive).
    `sheet_sent` only happens through sheet approval and `fixed` only with a
    proof photo (POST /fix); `reopened` only through citizens."""
    p = await get_scoped(db, pothole_id, office)
    if body.status not in (S.CONFIRMED, S.REJECTED):
        hint = {S.SHEET_SENT: "approve the sheet", S.FIXED: "use POST /potholes/{id}/fix with a proof photo"}
        raise HTTPException(http.HTTP_409_CONFLICT, f"Cannot set '{body.status.value}' here: " + hint.get(body.status, "not an officer action"))
    try:
        await set_status(db, p, body.status, actor(office), body.note)
    except InvalidTransition as exc:
        raise HTTPException(http.HTTP_409_CONFLICT, str(exc)) from exc
    p.needs_review = False
    if body.status == S.REJECTED:
        await label_pothole(db, p, "not_pothole", "officer", note=body.note)
    await db.commit()
    background.add_task(jobs.kick)
    return {"pothole_id": p.pothole_id, "status": p.status, "updated_at": p.updated_at}


@router.post("/{pothole_id}/fix", dependencies=[officer_limit])
async def mark_fixed(
    pothole_id: uuid.UUID,
    proof: UploadFile = File(..., description="Photo of the repaired spot"),
    note: str = Form(..., min_length=3, max_length=1000),
    db: AsyncSession = Depends(get_db),
    office: Office = Depends(require_office),
) -> dict:
    """Marks a pothole fixed. A proof photo and a note are mandatory. The
    vision model re-checks the proof photo: if it still sees a pothole, the
    repair is flagged for review (`fix_check.detected = true`)."""
    p = await get_scoped(db, pothole_id, office)
    raw = await read_photo(proof)
    check = await run_inference_async(raw, "manual")
    still_there = check.get("score") is not None and (check.get("confidence") or 0) >= settings.min_confidence
    try:
        await set_status(db, p, S.FIXED, actor(office), note)
    except InvalidTransition as exc:
        raise HTTPException(http.HTTP_409_CONFLICT, str(exc)) from exc
    clean, _ = privacy.anonymize(raw)
    p.fixed_proof_url = await storage.save(f"proof/{p.pothole_id}-{uuid.uuid4().hex[:8]}.jpg", clean)
    p.fixed_note = note
    p.fix_check = {
        "detected": still_there,
        "confidence": check.get("confidence"),
        "score": check.get("score"),
        "boxes": check.get("boxes") or [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    p.fix_verified = not still_there
    p.needs_review = still_there
    await record_event(db, p, "system", "fix_check_failed" if still_there else "fix_check_passed", data=p.fix_check)
    await db.commit()
    return {"pothole_id": p.pothole_id, "status": p.status, "fix_check": p.fix_check, "fix_verified": p.fix_verified}


@router.post(
    "/{pothole_id}/confirmations",
    response_model=ConfirmationOut,
    dependencies=[Depends(limit("confirm_device", 30, 86400, by="device"))],
)
async def confirm(
    pothole_id: uuid.UUID, body: ConfirmationIn, response: Response, background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """"I see it too" (`seen`), "still there" (`not_fixed`), "well repaired"
    (`fixed_ok`), "not a pothole" (`not_pothole`). One per device and kind;
    the phone must be within CONFIRM_RADIUS_M of the pothole."""
    p = await get_pothole(db, pothole_id)
    if body.gps_accuracy_m > settings.max_confirm_gps_accuracy_m:
        raise HTTPException(http.HTTP_403_FORBIDDEN, f"Position trop imprécise (±{body.gps_accuracy_m:.0f} m)")
    distance = haversine_m(body.lat, body.lon, p.lat, p.lon)
    if distance - body.gps_accuracy_m > settings.confirm_radius_m:
        raise HTTPException(http.HTTP_403_FORBIDDEN, f"Rapprochez-vous du nid-de-poule (à {distance:.0f} m)")
    allowed = {
        "seen": p.status in (S.NEW, S.CONFIRMED, S.SHEET_SENT, S.REOPENED),
        "not_fixed": p.status == S.FIXED,
        "fixed_ok": p.status == S.FIXED,
        "not_pothole": p.status != S.REJECTED,
    }[body.kind]
    if not allowed:
        raise HTTPException(http.HTTP_409_CONFLICT, f"'{body.kind}' is not possible on a '{p.status}' pothole")
    created = await add_confirmation(db, p, body.device_id, body.kind, body.lat, body.lon, body.gps_accuracy_m)
    await db.commit()
    if not created:
        response.status_code = http.HTTP_200_OK
    else:
        response.status_code = http.HTTP_201_CREATED
        background.add_task(jobs.kick)
    return {
        "pothole_id": p.pothole_id,
        "kind": body.kind,
        "created": created,
        **{k: getattr(p, k) for k in ("status", "confirm_count", "device_count", "fixed_ok_count", "not_fixed_count", "not_pothole_count")},
    }


@router.post("/{pothole_id}/feedback", dependencies=[officer_limit])
async def feedback(
    pothole_id: uuid.UUID, body: FeedbackIn, db: AsyncSession = Depends(get_db), office: Office = Depends(require_office)
) -> dict:
    """Officer label for the model feedback loop ("Pas un nid-de-poule")."""
    p = await get_scoped(db, pothole_id, office)
    n = await label_pothole(db, p, body.label, "officer", note=body.note)
    if body.label == "not_pothole":
        p.needs_review = True
    await record_event(db, p, actor(office), f"feedback_{body.label}", note=body.note)
    await db.commit()
    return {"pothole_id": p.pothole_id, "labels_created": n, "needs_review": p.needs_review}


# --- Work sheet review (issue #25) -----------------------------------------

@router.get("/{pothole_id}/sheet", dependencies=[officer_limit])
async def get_sheet(pothole_id: uuid.UUID, db: AsyncSession = Depends(get_db), office: Office = Depends(require_office)) -> dict:
    p = await get_scoped(db, pothole_id, office)
    full = await officer_pothole(db, p, await office_map(db))
    keys = ("sheet_status", "sheet_text", "sheet_edited", "sheet_citations", "sheet_generated_at", "sheet_approved_at",
            "sheet_approved_by", "sheet_hash", "sheet_job", "repair_method")
    return {"pothole_id": p.pothole_id, "ref": p.ref, **{k: full[k] for k in keys}}


@router.patch("/{pothole_id}/sheet", dependencies=[officer_limit])
async def edit_sheet(
    pothole_id: uuid.UUID, body: SheetEdit, db: AsyncSession = Depends(get_db), office: Office = Depends(require_office)
) -> dict:
    """Edit the draft before approval. The LLM's original text stays in
    `sheet_text_original` and the previous text goes into the audit log."""
    p = await get_scoped(db, pothole_id, office)
    if p.sheet_status != "generated":
        raise HTTPException(http.HTTP_409_CONFLICT, "Only a generated, not yet approved sheet can be edited")
    await record_event(db, p, actor(office), "sheet_edited", data={"previous_text": p.sheet_text})
    p.sheet_text = body.sheet_text
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"pothole_id": p.pothole_id, "sheet_status": p.sheet_status, "sheet_text": p.sheet_text}


@router.post("/{pothole_id}/sheet/approve", dependencies=[officer_limit])
async def approve_sheet(
    pothole_id: uuid.UUID, db: AsyncSession = Depends(get_db), office: Office = Depends(require_office)
) -> dict:
    """Officer approval: the only way to `sheet_sent`. Stamps approver and
    time, fingerprints the sheet for the PDF/QR check, keeps the clearest photo
    as a training positive and deletes the other photos (decision 6)."""
    p = await get_scoped(db, pothole_id, office)
    if p.sheet_status != "generated":
        raise HTTPException(http.HTTP_409_CONFLICT, f"Sheet is '{p.sheet_status}', not ready for approval")
    try:
        await set_status(db, p, S.SHEET_SENT, actor(office), "fiche approuvée")
    except InvalidTransition as exc:
        raise HTTPException(http.HTTP_409_CONFLICT, str(exc)) from exc
    p.sheet_status = "approved"
    p.sheet_approved_at = datetime.now(timezone.utc)
    p.sheet_approved_by = office.name
    p.sheet_hash = sheet_fingerprint(p, office.code)
    p.needs_review = False
    await label_pothole(db, p, "confirmed_pothole", "officer", only_best=True)
    await record_event(db, p, actor(office), "sheet_approved", data={"fingerprint": p.sheet_hash[:16]})
    await _delete_unlabelled_photos(db, p)
    await db.commit()
    return {"pothole_id": p.pothole_id, "status": p.status, "sheet_status": p.sheet_status, "fingerprint": p.sheet_hash[:16]}


async def _delete_unlabelled_photos(db: AsyncSession, p: Pothole) -> None:
    from backend.app.db_models import FeedbackLabel

    keep = set((await db.execute(select(FeedbackLabel.report_id).where(FeedbackLabel.pothole_id == p.pothole_id))).scalars())
    reports = (await db.execute(select(Report).where(Report.pothole_id == p.pothole_id, Report.photo_url.is_not(None)))).scalars()
    for r in reports:
        if r.report_id not in keep:
            await storage.delete(r.photo_url)
            r.photo_url = None


@router.post("/{pothole_id}/sheet/retry", dependencies=[officer_limit])
async def retry_sheet(
    pothole_id: uuid.UUID, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
    office: Office = Depends(require_office),
) -> dict:
    """Re-queues a failed sheet (or regenerates a not yet approved draft)."""
    p = await get_scoped(db, pothole_id, office)
    if p.sheet_status not in ("failed", "generated") or p.status not in (S.CONFIRMED, S.REOPENED):
        raise HTTPException(http.HTTP_409_CONFLICT, "Nothing to retry")
    p.sheet_status = "queued"
    await jobs.enqueue(db, p.pothole_id, "sheet")
    await record_event(db, p, actor(office), "sheet_retry")
    await db.commit()
    background.add_task(jobs.kick)
    return {"pothole_id": p.pothole_id, "sheet_status": p.sheet_status}


@router.get("/{pothole_id}/sheet.pdf", dependencies=[officer_limit])
async def sheet_pdf(pothole_id: uuid.UUID, db: AsyncSession = Depends(get_db), office: Office = Depends(require_office)) -> Response:
    p = await get_scoped(db, pothole_id, office)
    if not p.sheet_text:
        raise HTTPException(http.HTTP_404_NOT_FOUND, "No sheet yet")
    target = (await office_map(db)).get(p.target_office_id) if p.target_office_id else None
    return Response(
        render_sheet_pdf(p, target),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fiche-{p.ref}.pdf"'},
    )

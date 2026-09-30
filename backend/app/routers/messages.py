"""Citizen <-> authority support chat: one thread per device, polled by both apps."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.db_models import Message, Report
from backend.app.schemas import Conversation, MessageIn, MessageOut

router = APIRouter(tags=["messages"])


@router.get("/messages", response_model=list[MessageOut])
async def list_messages(device_id: str, db: AsyncSession = Depends(get_db)) -> list[Message]:
    rows = await db.execute(select(Message).where(Message.device_id == device_id).order_by(Message.created_at))
    return list(rows.scalars())


@router.post("/messages", response_model=MessageOut, status_code=201)
async def send_message(body: MessageIn, db: AsyncSession = Depends(get_db)) -> Message:
    message = Message(**body.model_dump())
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/conversations", response_model=list[Conversation])
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Newest thread first, with the device's report count for context."""
    messages = list((await db.execute(select(Message).order_by(Message.created_at))).scalars())
    report_counts = dict(
        (await db.execute(select(Report.device_id, func.count()).group_by(Report.device_id))).all()
    )
    threads: dict[str, dict] = {}
    for m in messages:
        t = threads.setdefault(m.device_id, {"device_id": m.device_id, "count": 0})
        t.update(count=t["count"] + 1, last_body=m.body, last_sender=m.sender, last_at=m.created_at)
    for t in threads.values():
        t["reports"] = report_counts.get(t["device_id"], 0)
    return sorted(threads.values(), key=lambda t: t["last_at"], reverse=True)

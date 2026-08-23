from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Topic
from app.schemas import TopicIn, TopicListOut, TopicOut, TopicPatch

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=TopicListOut)
def list_topics(drive_type: str | None = None, enabled: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Topic)
    if drive_type:
        q = q.filter(Topic.drive_type == drive_type)
    if enabled is not None:
        q = q.filter(Topic.enabled == enabled)
    items = q.order_by(Topic.id).all()
    return {"total": len(items), "items": items}


@router.post("", response_model=TopicOut)
def create_topic(data: TopicIn, db: Session = Depends(get_db)):
    topic = Topic(**data.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, data: TopicPatch, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "主题不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(topic, k, v)
    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=204)
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "主题不存在")
    db.delete(topic)
    db.commit()

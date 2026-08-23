from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TopicIn(BaseModel):
    drive_type: str = Field(min_length=1, max_length=20)
    category: str = Field(min_length=1, max_length=50)
    conflict: str = Field(min_length=1)


class TopicPatch(BaseModel):
    drive_type: str | None = None
    category: str | None = None
    conflict: str | None = None
    enabled: bool | None = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_type: str
    category: str
    conflict: str
    enabled: bool
    use_count: int


class TopicListOut(BaseModel):
    total: int
    items: list[TopicOut]


class Candidate(BaseModel):
    conflict: str
    titles: list[str]


class ConflictsOut(BaseModel):
    candidates: list[Candidate]


class BodyOut(BaseModel):
    body: str
    mood: str


class ImagePromptOut(BaseModel):
    image_prompt: str


class DraftConflictsIn(BaseModel):
    topic_id: int | None = None
    idea: str = ""


class BuildIn(BaseModel):
    topic_id: int | None = None
    conflict: str
    title: str
    image_size: str | None = None
    image_count: int | None = None


class ArticlePatch(BaseModel):
    title: str | None = None
    body: str | None = None
    image_prompt: str | None = None
    image_size: str | None = None


class StatusIn(BaseModel):
    status: str


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int | None
    title: str
    title_candidates: list
    body: str
    mood: str
    image_prompt: str
    image_paths: list
    image_size: str
    status: str
    created_at: datetime
    updated_at: datetime


class ArticleListOut(BaseModel):
    total: int
    items: list[ArticleOut]


class TitleCandidatesOut(BaseModel):
    candidates: list[str]

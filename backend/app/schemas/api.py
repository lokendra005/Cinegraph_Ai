from pydantic import BaseModel, Field


class StoryCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    input: str = Field(..., min_length=10, description="Raw narrative text")
    input_type: str = Field(default="text", pattern="^(text|voice_transcript)$")
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    use_llm: bool = Field(default=True, description="If false, use deterministic offline pipeline")


class StoryCreateResponse(BaseModel):
    story_id: str
    job_id: str
    status: str


class RegenerateRequest(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    use_llm: bool = True


class JobStatusResponse(BaseModel):
    id: str
    story_id: str
    status: str
    attempts: int
    max_attempts: int
    use_llm: bool
    last_error: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None


class JobActionResponse(BaseModel):
    job_id: str
    status: str


class StoryRegenerateResponse(BaseModel):
    story_id: str
    job_id: str
    status: str

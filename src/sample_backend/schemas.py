from pydantic import BaseModel


class JobsPayload(BaseModel):
    payload: str


class JobsOutput(BaseModel):
    job_id: str
    status: str


class JobsOutputCompleted(JobsOutput):
    result: str | None = None

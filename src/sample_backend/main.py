import json
from asyncio import sleep
from hashlib import sha256
from typing import Annotated
from uuid import uuid4

from config import REDIS_HOST, REDIS_PORT
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Security,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from redis.asyncio import Redis
from schemas import JobsOutput, JobsOutputCompleted, JobsPayload

app = FastAPI()
r = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def verify_token(
    authorization: str | None = Security(APIKeyHeader(name="Authorization")),
) -> None:
    print(authorization)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or bad Bearer token")

    token = authorization.split(" ")[1]

    if token != "luarc-token-123":  # luarc specific token
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str:
    print(idempotency_key)
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key header")
    return idempotency_key


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def start_job(payload: str, job_id: str) -> None:
    await sleep(7)
    payload_hash = sha256(payload.encode("utf-8")).hexdigest()

    completed_job = JobsOutputCompleted(
        job_id=job_id, status="completed", result=payload_hash
    )
    await r.set(f"jobs:{job_id}", completed_job.model_dump_json(), ex=86400)


@app.post("/api/v1/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    input_data: JobsPayload,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_token),
    idempotency_key: str = Depends(verify_idempotency_key),
) -> JobsOutput:

    if job_id := await r.get(f"idemp_keys:{idempotency_key}"):
        job_data = await r.get(f"jobs:{job_id}")
        return JobsOutput(
            **json.loads(job_data),
        )

    job = JobsOutput(job_id=uuid4().hex, status="pending")
    await r.set(f"idemp_keys:{idempotency_key}", job.job_id, ex=86400, nx=True)
    await r.set(f"jobs:{job.job_id}", job.model_dump_json(), ex=86400, nx=True)

    background_tasks.add_task(start_job, input_data.payload, job.job_id)

    return job


@app.get("/api/v1/{job_id}")
async def fetch_job(job_id: str) -> JobsOutputCompleted:
    job_data = await r.get(f"jobs:{job_id}")
    return JobsOutputCompleted(**json.loads(job_data))

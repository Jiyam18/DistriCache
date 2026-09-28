"""
REST API for DistriCache.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.store import Store, KeyNotFound


class SetRequest(BaseModel):
    value: str
    ttl_seconds: Optional[float] = None


app = FastAPI(
    title="DistriCache REST API",
    description="HTTP interface for the DistriCache storage engine",
    version="1.0.0",
)

store = Store()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/keys/{key}")
def get_key(key: str):
    try:
        value = store.get(key)
    except KeyNotFound:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "key": key,
        "value": value,
    }


@app.put("/keys/{key}")
def set_key(key: str, request: SetRequest):
    store.set(
        key,
        request.value,
        ttl_seconds=request.ttl_seconds,
    )

    return {
        "key": key,
        "value": request.value,
        "status": "stored",
    }


@app.delete("/keys/{key}")
def delete_key(key: str):
    deleted = store.delete(key)

    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "key": key,
        "status": "deleted",
    }


@app.get("/keys/{key}/exists")
def key_exists(key: str):
    return {
        "key": key,
        "exists": store.exists(key),
    }


@app.get("/keys/{key}/ttl")
def get_ttl(key: str):
    try:
        ttl = store.ttl(key)
    except KeyNotFound:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "key": key,
        "ttl_seconds": ttl,
    }


@app.post("/keys/{key}/expire")
def expire_key(key: str, ttl_seconds: float):
    success = store.expire(key, ttl_seconds)

    if not success:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "key": key,
        "ttl_seconds": ttl_seconds,
        "status": "updated",
    }


@app.get("/stats")
def get_stats():
    return store.stats()


@app.get("/keys")
def get_keys():
    return {
        "keys": store.keys(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.rest_api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
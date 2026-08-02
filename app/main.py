import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.executor import CodeExecutor

API_KEY = os.getenv("API_KEY", "dify-sandbox")
MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "100"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))
WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT", "15"))

executor = CodeExecutor(timeout=WORKER_TIMEOUT, max_workers=MAX_WORKERS)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await executor.shutdown()


app = FastAPI(lifespan=lifespan)


class CodeRequest(BaseModel):
    language: str
    code: str
    preload: str = ""
    enable_network: bool = False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path.startswith("/v1/sandbox"):
            api_key = request.headers.get("X-Api-Key")
            if not api_key or api_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": -401,
                        "message": "Unauthorized",
                        "data": None,
                    },
                )
        return await call_next(request)


class ConcurrencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(MAX_WORKERS)
        self.current_requests: int = 0

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path.startswith("/v1/sandbox/run"):
            if self.current_requests >= MAX_REQUESTS:
                return JSONResponse(
                    status_code=503,
                    content={
                        "code": -503,
                        "message": "Too many requests",
                        "data": None,
                    },
                )

            self.current_requests += 1
            try:
                async with self.semaphore:
                    return await call_next(request)
            finally:
                self.current_requests -= 1
        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(ConcurrencyMiddleware)


@app.get("/health")
async def health_check() -> str:
    return "ok"


@app.post("/v1/sandbox/run")
async def execute_code(request: CodeRequest) -> dict[str, object]:
    if request.language not in {"python3", "nodejs"}:
        return {
            "code": -400,
            "message": "unsupported language",
            "data": None,
        }

    code = "\n".join(part for part in (request.preload, request.code) if part)
    result = await executor.execute(code, request.language)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "error": result["error"] or "",
            "stdout": result["output"] or "",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8194)  # noqa: S104

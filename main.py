
import time
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


# The only website origin allowed by the assignment
ALLOWED_ORIGIN = "https://dash-m32mu3.example.com"

# Verify that this matches your logged-in grader email
EMAIL = "24f2003391@ds.study.iitm.ac.in"


# Create the FastAPI application
api = FastAPI()


# Configure CORS with the exact allowed origin
api.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


class RequestMetadataMiddleware:
    """Add a unique request ID and processing time to HTTP responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Ignore non-HTTP traffic
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        async def send_with_metrics(message):
            if message["type"] == "http.response.start":
                elapsed = max(0.0, time.perf_counter() - start_time)

                # Preserve existing headers and add our two headers
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", request_id.encode("ascii"))
                )
                headers.append(
                    (
                        b"x-process-time",
                        f"{elapsed:.6f}".encode("ascii"),
                    )
                )

                message["headers"] = headers

            await send(message)

        # Wrap the whole application so even error responses get the headers
        await self.app(scope, receive, send_with_metrics)


@api.get("/stats")
def get_stats(
    values: str = Query(..., description="Comma-separated integers")
):
    # Convert a string such as "1,2,3" into [1, 2, 3]
    try:
        numbers = [int(part.strip()) for part in values.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="values must contain comma-separated integers",
        )

    if not numbers:
        raise HTTPException(
            status_code=400,
            detail="At least one integer is required",
        )

    total = sum(numbers)
    count = len(numbers)

    return {
        "email": EMAIL,
        "count": count,
        "sum": total,
        "min": min(numbers),
        "max": max(numbers),
        "mean": round(total / count, 6),
    }


# Expose the middleware-wrapped app for the production web server
app = RequestMetadataMiddleware(api)

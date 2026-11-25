import os
import base64
import binascii
from io import BytesIO

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="Hamooti Image API", version="1.0.0")

OVH_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/images/generations"
MODEL = "stable-diffusion-xl-base-v10"
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "").strip()


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=1800)
    size: str = Field(default="1024x1024", pattern=r"^(1024x1024|1024x768|768x1024)$")


@app.get("/")
async def root():
    return {
        "service": "Hamooti Image API",
        "status": "online",
        "model": MODEL,
        "routes": ["/health", "/generate"]
    }


@app.get("/health")
async def health():
    return {"ok": True, "model": MODEL}


@app.post("/generate")
async def generate(
    body: GenerateRequest,
    x_api_key: str = Header(default="")
):
    # Protect the public Render endpoint. The key is configured in Render,
    # then stored privately in Hamooti's .env file.
    if not SERVICE_API_KEY:
        raise HTTPException(status_code=503, detail="Service API key is not configured")
    if x_api_key != SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = {
        "model": MODEL,
        "prompt": body.prompt,
        "size": body.size,
        "n": 1
    }

    timeout = httpx.Timeout(180.0, connect=20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.post(
                OVH_URL,
                headers={"Content-Type": "application/json"},
                json=payload
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image provider timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not contact image provider")

    if upstream.status_code == 429:
        raise HTTPException(status_code=429, detail="OVHcloud anonymous rate limit reached; wait and retry")
    if upstream.status_code in (401, 403):
        raise HTTPException(status_code=502, detail="Image provider requires authentication or rejected the request")
    if upstream.status_code >= 400:
        # Avoid returning upstream internals or secrets to WhatsApp users.
        raise HTTPException(status_code=502, detail=f"Image provider error ({upstream.status_code})")

    try:
        data = upstream.json()
        encoded = data["data"][0]["b64_json"]
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, KeyError, IndexError, TypeError, binascii.Error):
        raise HTTPException(status_code=502, detail="Image provider returned an unexpected response")

    # Validate that the response is a real image before sending it onward.
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.verify()
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            output = BytesIO()
            img.save(output, format="PNG", optimize=True)
            clean_image = output.getvalue()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=502, detail="Provider response was not a valid image")

    return Response(
        content=clean_image,
        media_type="image/png",
        headers={"Cache-Control": "no-store"}
    )

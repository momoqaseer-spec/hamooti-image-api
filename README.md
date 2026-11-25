# Hamooti Image API

A small FastAPI service for Hamooti. Render hosts this API; OVHcloud AI Endpoints performs the actual image generation.

## Important free-tier note

This project uses OVHcloud's anonymous Stable Diffusion XL endpoint (no OVH API key). OVHcloud currently documents an anonymous limit of **2 requests per minute per IP and model**. This is a low-volume trial path, not a guaranteed unlimited free production plan. Anonymous access and model availability can change.

Endpoint:
`https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/images/generations`

Model:
`stable-diffusion-xl-base-v10`

## Deploy on Render

1. Push these files to a GitHub repository named `hamooti-image-api`.
2. In Render, choose **New +** → **Web Service** and connect the repository.
3. Select **Python** as the runtime.
4. Build Command:
   `pip install -r requirements.txt`
5. Start Command:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Choose the **Free** instance type.
7. Add an Environment Variable:
   - Key: `SERVICE_API_KEY`
   - Value: generate a long random secret (do not use the example text and do not commit it to GitHub).
8. Deploy.

## Test

Open:
`https://YOUR-RENDER-SERVICE.onrender.com/health`

Expected:
`{"ok":true,"model":"stable-diffusion-xl-base-v10"}`

Generate an image with a POST request to `/generate`:

Headers:
`X-API-Key: YOUR_SERVICE_API_KEY`
`Content-Type: application/json`

Body:
```json
{
  "prompt": "A cinematic photorealistic view of an ancient Arabian city at golden hour, highly detailed",
  "size": "1024x1024"
}
```

The response is binary PNG image data, not JSON.

## Connect from Hamooti (Node.js)

```js
const response = await axios.post(
  `${process.env.HAMOOTI_IMAGE_API_URL}/generate`,
  { prompt, size: "1024x1024" },
  {
    headers: { "X-API-Key": process.env.HAMOOTI_IMAGE_API_KEY },
    responseType: "arraybuffer",
    timeout: 240000
  }
);

const imageBuffer = Buffer.from(response.data);
```

Add to Hamooti's private `.env`:
```env
HAMOOTI_IMAGE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
HAMOOTI_IMAGE_API_KEY=the_same_secret_you_set_in_render
```

Never share or commit either secret. Keep the existing Hamooti 7.0 files and Baileys auth session untouched while testing this service separately.

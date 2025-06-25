import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from app.constants import PRODUCER_URL
import httpx
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class CameraRequest(BaseModel):
    camera_name: str
    rtsp_url: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/start-camera")
async def start_camera(data: CameraRequest):
    camera_name = data.camera_name
    rtsp_url = data.rtsp_url

    async with httpx.AsyncClient() as client:
        await client.post(f"{PRODUCER_URL}/connect-camera", json={
            "camera_name": camera_name,
            "rtsp_url": rtsp_url
        })

    return JSONResponse(content={"status": "started"}, status_code=200)

@app.websocket("/ws/{camera_name}")
async def websocket_endpoint(websocket: WebSocket, camera_name: str):
    await websocket.accept()

    try:
        data = await websocket.receive_text()
        message = json.loads(data)

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PRODUCER_URL}/negotiate", json={
                "camera_name": camera_name,
                "sdp": message["sdp"],
                "type": message["type"]
            })

        answer = response.json()
        await websocket.send_text(json.dumps(answer))

        while True:
            msg = await websocket.receive_text()
            if msg.strip().lower() == "bye":
                print(f"👋 BYE desde frontend: {camera_name}")
                break

    except WebSocketDisconnect:
        print(f"⚠️ WebSocket desconectado: {camera_name}")
    except Exception as e:
        print(f"❌ Error en señalización: {e}")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print(f"🔌 Conexión cerrada: {camera_name}")

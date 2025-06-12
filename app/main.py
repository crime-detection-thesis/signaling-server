import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import requests
from starlette.websockets import WebSocketState
from app.constants import PRODUCER_URL

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

@app.websocket("/ws/{camera_name}")
async def websocket_endpoint(websocket: WebSocket, camera_name: str):
    print("ws://{camera_name} conectado")
    await websocket.accept()
    print(f"📡 WebSocket conectado: {camera_name}")

    try:
        data = await websocket.receive_text()
        message = json.loads(data)

        print("📨 Oferta recibida. Reenviando al productor...")

        response = requests.post(f"{PRODUCER_URL}/negotiate", json={
            "camera_name": camera_name,
            "sdp": message["sdp"],
            "type": message["type"]
        })
        print('🔄 Respuesta del productor recibida.')

        answer = response.json()
        await websocket.send_text(json.dumps(answer))

        print(f"✅ Respuesta enviada al cliente: {camera_name}")

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

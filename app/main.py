import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
import websockets
import httpx

from app.config import VIDEO_PRODUCER_WS_URL

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
async def start_camera(data: dict):
    timeout = httpx.Timeout(60.0, connect=60.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{data['video_gateway_url']}/connect-camera",
                json={"camera_id": data["camera_id"],
                      "rtsp_url": data["rtsp_url"]},
                timeout=60.0
            )
            response.raise_for_status()
            return {"status": "started"}
        except httpx.RequestError as e:
            print(f"Error al conectar con el productor: {e}")
            return {"status": "error", "message": str(e)}, 500
        except Exception as e:
            print(f"Error inesperado: {e}")
            return {"status": "error", "message": "Error interno del servidor"}, 500

@app.websocket("/ws/{camera_id}")
async def websocket_endpoint(sign_ws: WebSocket, camera_id: int):
    await sign_ws.accept()

    prod_ws = None
    max_retries = 10
    for attempt in range(max_retries):
        try:
            prod_ws = await websockets.connect(f"{VIDEO_PRODUCER_WS_URL}/camera/ws/{camera_id}")

            try:
                peek = await asyncio.wait_for(prod_ws.recv(), timeout=2.0)
                parsed = json.loads(peek)
                if parsed.get("error"):
                    await prod_ws.close()
                    print(f"Cámara {camera_id} aún no disponible. Reintentando...")
                    await asyncio.sleep(0.5)
                    continue
                else:
                    async def prepend_msg(msg):
                        yield msg
                        async for m in prod_ws:
                            yield m
                    prod_ws_iter = prepend_msg(peek)
                    break
            except asyncio.TimeoutError:
                break
        except Exception as e:
            print(f"❌ Fallo conectando al productor (intento {attempt + 1}): {e}")
            await asyncio.sleep(0.5)
    else:
        await sign_ws.send_text(json.dumps({"error": "Cámara no disponible"}))
        await sign_ws.close()
        return

    async def client_to_producer():
        try:
            async for message in sign_ws.iter_text():
                await prod_ws.send(message)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Error forwarding client→producer: {e}")

    async def producer_to_client():
        try:
            if 'prod_ws_iter' in locals():
                async for message in prod_ws_iter:
                    await sign_ws.send_text(message)
            else:
                async for message in prod_ws:
                    await sign_ws.send_text(message)
        except Exception as e:
            print(f"Error forwarding producer→client: {e}")

    client_task = asyncio.create_task(client_to_producer())
    producer_task = asyncio.create_task(producer_to_client())
    done, pending = await asyncio.wait(
        [client_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    try:
        await prod_ws.send(json.dumps({"type": "bye"}))
    except Exception:
        pass

    if sign_ws.client_state != WebSocketState.DISCONNECTED:
        await sign_ws.close()
    await prod_ws.close()
    print(f"🔌 Signaling WS closed for camera {camera_id}")

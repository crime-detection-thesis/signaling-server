import asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import websockets
import httpx

from app.constants import PRODUCER_WS_URL, PRODUCER_HTTP_URL

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
                f"{PRODUCER_HTTP_URL}/connect-camera",
                json={"camera_id": data["camera_id"], "rtsp_url": data["rtsp_url"]},
                timeout=60.0
            )
            response.raise_for_status()  # Lanza excepción para códigos 4XX/5XX
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
    prod_ws = await websockets.connect(f"{PRODUCER_WS_URL}/ws/{camera_id}")

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
            async for message in prod_ws:
                await sign_ws.send_text(message)
        except Exception as e:
            print(f"Error forwarding producer→client: {e}")

    # # Proxy bidireccional: cliente ⇄ producer
    # try:
    #     await asyncio.gather(client_to_producer(), producer_to_client())
    # except WebSocketDisconnect:
    #     pass
    # finally:
    #     try:
    #         await prod_ws.send(json.dumps("bye"))
    #     except Exception:
    #         pass

    #     if sign_ws.client_state != WebSocketState.DISCONNECTED:
    #         await sign_ws.close()
    #     await prod_ws.close()
    #     print(f"🔌 Signaling WS closed for camera {camera_id}")

    # ── Aquí sustituimos gather por wait(FIRST_COMPLETED) ──
    client_task   = asyncio.create_task(client_to_producer())
    producer_task = asyncio.create_task(producer_to_client())
    done, pending = await asyncio.wait(
        [client_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    # Cancelamos la tarea que quedó pendiente (para salir del bucle)
    for task in pending:
        task.cancel()

    # ── Notificamos al productor que cierre su WebSocket ──
    try:
        await prod_ws.send(json.dumps({"type": "bye"}))
    except Exception:
        pass

    # ── Ahora cerramos ambas conexiones ──
    if sign_ws.client_state != WebSocketState.DISCONNECTED:
        await sign_ws.close()
    await prod_ws.close()
    print(f"🔌 Signaling WS closed for camera {camera_id}")


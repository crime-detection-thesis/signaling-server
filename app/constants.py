from dotenv import load_dotenv
import os

load_dotenv()

VIDEO_GATEWAY_URL = os.getenv("VIDEO_GATEWAY_URL")
VIDEO_PRODUCER_WS_URL = os.getenv("VIDEO_PRODUCER_WS_URL")


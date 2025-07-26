from dotenv import load_dotenv
import os

load_dotenv()

PRODUCER_HTTP_URL = os.getenv("PRODUCER_HTTP_URL")
PRODUCER_WS_URL = os.getenv("PRODUCER_WS_URL")


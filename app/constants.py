from dotenv import load_dotenv
import os

load_dotenv()

PRODUCER_HTTP_URL = f'http://{os.getenv("PRODUCER_URL")}'
PRODUCER_WS_URL = f'ws://{os.getenv("PRODUCER_URL")}'


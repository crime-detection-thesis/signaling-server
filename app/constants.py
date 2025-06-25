from dotenv import load_dotenv
import os

load_dotenv()

PRODUCER_URL = os.getenv("PRODUCER_URL")

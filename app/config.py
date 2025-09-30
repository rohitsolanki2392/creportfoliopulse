import os
from dotenv import load_dotenv

# agar .env file use kar rahe ho
load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

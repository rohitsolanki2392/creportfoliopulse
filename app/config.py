import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from google import genai
import google.generativeai as gen

load_dotenv()


google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not set in environment")

client = genai.Client(api_key=google_api_key) 
model = gen.GenerativeModel(model_name="gemini-2.5-pro")
import google.generativeai as genai
MODEL = "gemini-2.5-pro"
SUPPORTED_EXT = ['.pdf', '.docx', '.txt', '.xlsx', '.csv']
llm_model = genai.GenerativeModel(MODEL)
UPLOAD_DIR = os.path.join("uploads", "profile_photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_SIZE = 3 * 1024 * 1024  

SECRET_KEY = os.getenv("SECRET_KEY", "x" * 32)
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

LLM_CONCURRENCY = 5
EMBED_BATCH_SIZE = 100
LLM_BATCH_SIZE = 20 
model = os.getenv("GEMINI_EMBEDDING_MODEL")
api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX")

dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
FIRESTORE_SECRET_KEY=os.getenv("FIRESTORE_SECRET_KEY")
cloud = os.getenv("PINECONE_CLOUD")
region = os.getenv("PINECONE_REGION")
EMBED_BATCH_SIZE = 100
MAX_CHUNK_SIZE = 1200
OVERLAP = 100


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("KMS_LOCATION", "global")
KEYRING = os.getenv("KMS_KEYRING")
KEY_NAME = os.getenv("KMS_KEY_NAME")
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "120"))

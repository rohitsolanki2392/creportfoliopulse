import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from google import genai


load_dotenv()


google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not set in environment")

client = genai.Client(api_key=google_api_key) 

SUPPORTED_EXT = ['.pdf', '.docx', '.txt', '.xlsx', '.csv']

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


model = os.getenv("GEMINI_EMBEDDING_MODEL")
api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX")
dimension = os.getenv("EMBEDDING_DIMENSION")
cloud = os.getenv("PINECONE_CLOUD")
region = os.getenv("PINECONE_REGION")


import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.models.models import Base
from app.database.db import engine
from app.router import admin_user_chat, auth, buildings, chatbot, dashborad, feeedback, invite_user,  user_chat_bot,gen_lease
from fastapi.staticfiles import StaticFiles


import os
os.environ["GRPC_VERBOSITY"] = "ERROR"

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Building Management API",
    version="1.0.0",
    timeout=300,
    description="API for managing buildings, leases, and user interactions with chatbots.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(invite_user.router, prefix="/invite_user", tags=["Invite User"])
app.include_router(dashborad.router, prefix="/admin", tags=["Dashboard"])
app.include_router(gen_lease.router,prefix="/generate_lease", tags=["Generate Lease"])
app.include_router(user_chat_bot.router, prefix="/user",tags=["Portfolio Chatbot"])
app.include_router(admin_user_chat.router, prefix="/admin_user_chat", tags=["Data categories chatbot"])
app.include_router(buildings.router, prefix="/building_operations", tags=["Building Operations"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["Building Chatbot"])
app.include_router(feeedback.router,prefix="/feedback",tags=["feedback"])


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}, 
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Invalid request payload",
            "errors": exc.errors()  
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

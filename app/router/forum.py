
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.models import User
from app.database.firestore import db
from app.utils.auth_utils import get_current_user
from google.cloud.firestore_v1 import Increment 


router = APIRouter(tags=["Portfolio Forum"])


class ThreadCreate(BaseModel):
    title: str

class ThoughtCreate(BaseModel):
    content: str

class ThoughtOut(BaseModel):
    id: str
    author_name: str
    content: str
    created_at: datetime
    deleted: bool = False

class ThreadOut(BaseModel):
    id: str
    title: str
    author_name: str
    created_at: datetime
    last_thought_at: Optional[datetime] = None
    thought_count: int = 0
    thoughts: List[ThoughtOut] = []


@router.post("/threads", response_model=dict)
async def create_thread(
    thread: ThreadCreate,
    current_user: User = Depends(get_current_user),
):
    company_id = str(current_user.company_id)
    ref = db.collection("companies").document(company_id).collection("forum").document()

    data = {
        "title": thread.title,
        "author_uid": str(current_user.id),
        "author_name": current_user.name or current_user.email.split("@")[0],
        "created_at": datetime.utcnow(),
        "last_thought_at": datetime.utcnow(),
        "thought_count": 0,
        "deleted": False,
    }
    ref.set(data)
    return {"id": ref.id, **data}


@router.get("/threads", response_model=List[ThreadOut])
async def list_threads(current_user: User = Depends(get_current_user)):
    company_id = str(current_user.company_id)
    docs = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .where("deleted", "==", False)
        .order_by("last_thought_at", direction="DESCENDING")
        .stream()
    )

    threads = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        threads.append(data)
    return threads


@router.get("/threads/{thread_id}", response_model=ThreadOut)
async def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    company_id = str(current_user.company_id)
    thread_ref = db.collection("companies").document(company_id).collection("forum").document(thread_id)
    thread = thread_ref.get()

    if not thread.exists or thread.to_dict().get("deleted"):
        raise HTTPException(status_code=404, detail="Thread not found")

    data = thread.to_dict()
    data["id"] = thread_id

    thoughts_snap = thread_ref.collection("thoughts").order_by("created_at").stream()
    thoughts = [
        {**t.to_dict(), "id": t.id}
        for t in thoughts_snap
        if not t.to_dict().get("deleted", False)
    ]

    data["thoughts"] = thoughts
    return data


@router.post("/threads/{thread_id}/thoughts")
async def add_thought(
    thread_id: str,
    thought: ThoughtCreate,
    current_user: User = Depends(get_current_user),
):
    company_id = str(current_user.company_id)
    thread_ref = db.collection("companies").document(company_id).collection("forum").document(thread_id)

    if not thread_ref.get().exists:
        raise HTTPException(status_code=404, detail="Thread not found")

    thought_ref = thread_ref.collection("thoughts").document()
    thought_data = {
        "content": thought.content,
        "author_uid": str(current_user.id),
        "author_name": current_user.name or current_user.email.split("@")[0],
        "created_at": datetime.utcnow(),
        "deleted": False,
    }
    thought_ref.set(thought_data)

    
    thread_ref.update({
        "last_thought_at": datetime.utcnow(),
        "thought_count": Increment(1),
    })

    return {"id": thought_ref.id, **thought_data}


@router.delete("/threads/{thread_id}/thoughts/{thought_id}")
async def delete_thought(
    thread_id: str,
    thought_id: str,
    current_user: User = Depends(get_current_user),
):
    company_id = str(current_user.company_id)
    ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
        .collection("thoughts")
        .document(thought_id)
    )

    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Thought not found")

    data = doc.to_dict()
    is_owner = str(data.get("author_uid")) == str(current_user.id)
    is_admin = getattr(current_user, "role", "") == "admin"

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")

    ref.update({"deleted": True})
    return {"success": True}
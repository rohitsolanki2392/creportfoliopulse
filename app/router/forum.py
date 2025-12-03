
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from app.database.db import get_db
from app.models.models import User
from app.database.firestore import db
from app.schema.forum import ThoughtCreate, ThreadCreate, ThreadOut
from app.utils.auth_utils import get_current_user
from google.cloud.firestore_v1 import Increment 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
router = APIRouter(tags=["Portfolio Forum"])




@router.post("/threads", response_model=dict)
async def create_thread(
    thread: ThreadCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(status_code=403, detail="Forum feature is disabled for your account.")

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
    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(status_code=403, detail="Forum feature is disabled for your account.")

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


@router.post("/threads/{thread_id}/thoughts")
async def add_thought(
    thread_id: str,
    thought: ThoughtCreate,
    current_user: User = Depends(get_current_user),
):
 
    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(
            status_code=403, detail="Forum feature is disabled for your account."
        )

    company_id = str(current_user.company_id)
    thread_ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
    )

    if not thread_ref.get().exists:
        raise HTTPException(status_code=404, detail="Thread not found")

    thought_ref = thread_ref.collection("thoughts").document()

    thought_data = {
        "content": thought.content.strip(),
        "author_uid": str(current_user.id),  
        "author_name": current_user.name or current_user.email.split("@")[0],
        "author_role": current_user.role,
        "created_at": datetime.utcnow(),
        "deleted": False,
    }

    thought_ref.set(thought_data)


    thread_ref.update({
        "last_thought_at": datetime.utcnow(),
        "thought_count": Increment(1),
    })

    return {"id": thought_ref.id, **thought_data}



@router.get("/threads/{thread_id}", response_model=ThreadOut)
async def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(status_code=403, detail="Forum feature is disabled for your account.")

    company_id = str(current_user.company_id)
    thread_ref = db.collection("companies").document(company_id).collection("forum").document(thread_id)
    thread_doc = thread_ref.get()

    if not thread_doc.exists or thread_doc.to_dict().get("deleted", False):
        raise HTTPException(status_code=404, detail="Thread not found")

    data = thread_doc.to_dict()
    data["id"] = thread_id

    thoughts_snap = thread_ref.collection("thoughts").order_by("created_at").stream()

    thoughts = []
    for t in thoughts_snap:
        t_data = t.to_dict()
        if not t_data.get("deleted", False):
            thoughts.append({
                "id": t.id,
                "author_name": t_data.get("author_name"),
                "author_uid": t_data.get("author_uid"),  
                "content": t_data.get("content"),
                "created_at": t_data.get("created_at"),
                "deleted": t_data.get("deleted", False),
            })

    data["thoughts"] = thoughts
    return data

@router.delete("/threads/{thread_id}/thoughts/{thought_id}")
async def delete_thought(
    thread_id: str,
    thought_id: str,
    current_user: User = Depends(get_current_user),
):

    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(
            status_code=403,
            detail="Forum feature is disabled for your account."
        )

    company_id = str(current_user.company_id)

    thought_ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
        .collection("thoughts")
        .document(thought_id)
    )

    thought_doc = thought_ref.get()

    if not thought_doc.exists:
        raise HTTPException(status_code=404, detail="Thought not found")

    thought_data = thought_doc.to_dict()

    is_owner = str(thought_data.get("author_uid")) == str(current_user.id)
    is_admin = current_user.role == "admin"

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to delete this thought")

 
    thought_ref.update({
        "deleted": True,
        "deleted_at": datetime.utcnow(),
        "deleted_by_uid": str(current_user.id),
        "deleted_by_name": current_user.name or current_user.email.split("@")[0],
    })

    return {"success": True, "message": "Thought deleted successfully"}


@router.patch("/threads/{thread_id}/thoughts/{thought_id}")
async def update_thought(
    thread_id: str,
    thought_id: str,
    thought: ThoughtCreate,
    current_user: User = Depends(get_current_user),
):

    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(
            status_code=403, 
            detail="Forum feature is disabled for your account."
        )

    company_id = str(current_user.company_id)

    thought_ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
        .collection("thoughts")
        .document(thought_id)
    )

    thought_doc = thought_ref.get()

    if not thought_doc.exists:
        raise HTTPException(status_code=404, detail="Thought not found")

    thought_data = thought_doc.to_dict()

    if thought_data.get("deleted", False):
        raise HTTPException(status_code=410, detail="Thought has been deleted")


    is_owner = str(thought_data.get("author_uid")) == str(current_user.id)
    is_admin = current_user.role == "admin"

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to edit this thought")

    update_data = {
        "content": thought.content.strip(),
        "edited_at": datetime.utcnow(),
        "edited_by_uid": str(current_user.id),
        "edited_by_name": current_user.name or current_user.email.split("@")[0],
    }

    thought_ref.update(update_data)


    thread_ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
    )
    thread_ref.update({"last_thought_at": datetime.utcnow()})

    return {
        "success": True,
        "message": "Thought updated successfully",
        "updated_at": update_data["edited_at"],
        "edited_by": update_data["edited_by_name"]
    }

@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not current_user.forum_enabled:
        raise HTTPException(status_code=403, detail="Forum feature is disabled for your account.")

    company_id = str(current_user.company_id)

    thread_ref = (
        db.collection("companies")
        .document(company_id)
        .collection("forum")
        .document(thread_id)
    )

    thread_doc = thread_ref.get()

    if not thread_doc.exists:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread_data = thread_doc.to_dict()
    is_owner = str(thread_data.get("author_uid")) == str(current_user.id)
    is_admin = getattr(current_user, "role", "") == "admin"

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to delete thread")

 
    thread_ref.update({"deleted": True})


    thoughts_ref = thread_ref.collection("thoughts").stream()
    batch = db.batch()
    for thought in thoughts_ref:
        batch.update(
            thought.reference,
            {"deleted": True}
        )
    batch.commit()

    return {
        "success": True,
        "message": "Thread and all thoughts deleted successfully",
        "thread_id": thread_id
    }



@router.patch("/forum-toggle")
async def toggle_forum_feature(
    email: str,
    enable: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can toggle forum feature")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.forum_enabled = enable
    await db.commit()
    await db.refresh(user)

    return {"message": f"Forum feature {'enabled' if enable else 'disabled'} for {user.email}"}


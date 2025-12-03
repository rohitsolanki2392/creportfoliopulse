from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.db import get_db
from app.models.models import User, UserNote
from app.schema.note import NoteCreate, NoteInDB, NoteUpdate
from app.utils.auth_utils import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
router = APIRouter(
    prefix="/notes",
    tags=["notes"],
)


@router.post("/", response_model=NoteInDB, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_in: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_note = UserNote(
        user_id=current_user.id,
        title=note_in.title,
        content=note_in.content
    )
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note


@router.get("/", response_model=List[NoteInDB])
async def get_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserNote)
        .filter(UserNote.user_id == current_user.id)
        .order_by(UserNote.updated_at.desc())
    )
    notes = result.scalars().all()
    return notes


@router.get("/{note_id}", response_model=NoteInDB)
async def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserNote)
        .filter(UserNote.id == note_id, UserNote.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return note


@router.put("/{note_id}", response_model=NoteInDB)
async def update_note(
    note_id: int,
    note_update: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserNote)
        .filter(UserNote.id == note_id, UserNote.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = note_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)

    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserNote)
        .filter(UserNote.id == note_id, UserNote.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.commit()
    return {"message":"Notes Deleted Successfully"} 
import uuid
import enum
from datetime import datetime, timedelta
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Float,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    owner_name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship(
        "User",
        back_populates="owned_company",
        uselist=False,
        foreign_keys=[owner_id]
    )
    users = relationship(
        "User",
        back_populates="company",
        foreign_keys="User.company_id"
    )
    

class Status(enum.Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class FileCategory(enum.Enum):
    Broker = "Broker"
    Market = "Market"
    Building = "Building"
    Colleague = "Colleague"


class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    user = relationship("User", back_populates="tokens")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(Integer, ForeignKey("building.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    category = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False) 


    user = relationship("User", back_populates="chat_sessions", foreign_keys=[user_id])
    messages = relationship(
        "ChatHistory",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    building = relationship("Building", backref="chat_sessions", foreign_keys=[building_id])


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    file_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    response_time = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    response_json = Column(JSON)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False) 


    session = relationship("ChatSession", back_populates="messages", foreign_keys=[chat_session_id])
    user = relationship("User", foreign_keys=[user_id])


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    number = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="user", nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    buildings = relationship(
        "Building",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Building.owner_id"
    )
    permissions = relationship(
        "BuildingPermission",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="BuildingPermission.user_id"
    )
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="ChatSession.user_id"
    )
    standalone_files = relationship(
        "StandaloneFile",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="StandaloneFile.user_id"
    )
    categorized_files = relationship(
        "CategorizedFile",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="CategorizedFile.user_id"
    )
    company = relationship(
        "Company",
        back_populates="users",
        foreign_keys=[company_id]
    )
    owned_company = relationship(
        "Company",
        back_populates="owner",
        uselist=False,
        foreign_keys=[Company.owner_id]
    )
    tokens = relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Token.user_id"
    )


class OTP(Base):
    __tablename__ = "otp"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))


class UserLogin(Base):
    __tablename__ = "user_logins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    login_timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", foreign_keys=[user_id])


class Building(Base):
    __tablename__ = "building"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False) 
    owner = relationship("User", back_populates="buildings", foreign_keys=[owner_id])
    files = relationship("BuildingFile", back_populates="building", foreign_keys="BuildingFile.building_id", cascade="all, delete-orphan")
    permissions = relationship("BuildingPermission",back_populates="building",cascade="all, delete-orphan",foreign_keys="BuildingPermission.building_id")


class BuildingFile(Base):
    __tablename__ = "building_file"
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("building.id"), nullable=False)
    file_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_file_name = Column(String, nullable=False)
    building_data = Column(JSON, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=True)
    building = relationship("Building", back_populates="files", foreign_keys=[building_id])


class StandaloneFile(Base):
    __tablename__ = "standalone_files"
    file_id = Column(String, primary_key=True)
    original_file_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    building_id = Column(Integer, ForeignKey("building.id", ondelete="SET NULL"), nullable=True)
    category = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    gcs_path = Column(String, nullable=False)
    file_size = Column(String, nullable=False, default="0")
    structured_metadata = Column(String, nullable=True) 
    company_id = Column(Integer, ForeignKey("companies.id",ondelete="CASCADE"), nullable=False) 
    user = relationship("User", back_populates="standalone_files", foreign_keys=[user_id])
    building = relationship("Building", foreign_keys=[building_id])

class CategorizedFile(Base):
    __tablename__ = "categorized_files"
    file_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_file_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)  
    category = Column(SQLEnum(FileCategory, name="file_category_enum"), nullable=False)
    user = relationship("User", back_populates="categorized_files", foreign_keys=[user_id])


class BuildingPermission(Base):
    __tablename__ = "building_permission"
    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("building.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    building = relationship("Building", back_populates="permissions", foreign_keys=[building_id])
    user = relationship("User", back_populates="permissions", foreign_keys=[user_id])


class BuildingAccessRequest(Base):
    __tablename__ = "building_access_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(Integer, ForeignKey("building.id", ondelete="CASCADE"), nullable=True)
    status = Column(SQLEnum(Status, name="status_enum"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", foreign_keys=[user_id])
    building = relationship("Building", foreign_keys=[building_id])


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    feedback = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # optional: 1–5 rating scale
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])



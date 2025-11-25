import uuid
import enum
from datetime import datetime, timedelta, timezone
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Float,
    func,
)
from sqlalchemy.orm import relationship, declarative_base

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
        foreign_keys="User.company_id",
        cascade="all, delete-orphan"
    )

    tours = relationship(
        "Tour",
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    det_expense_submissions = relationship(
        "DETExpenseSubmission",
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True
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

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(Integer, ForeignKey("building.id", ondelete="SET NULL"))
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

    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")



class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    number = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="user", nullable=False)
    gemini_chat_enabled = Column(Boolean, default=False)

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    photo_url = Column(String, nullable=True)
    bg_photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


    company = relationship("Company", back_populates="users", foreign_keys=[company_id])

    owned_company = relationship(
        "Company",
        back_populates="owner",
        uselist=False,
        foreign_keys=[Company.owner_id]
    )

    buildings = relationship(
        "Building",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    standalone_files = relationship(
        "StandaloneFile",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    email_templates = relationship("EmailTemplate", back_populates="user", cascade="all, delete-orphan")
    tenants = relationship("Tenant", back_populates="user", cascade="all, delete-orphan")

    tours = relationship(
        "Tour",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class DETExpenseSubmission(Base):
    __tablename__ = "det_expense_submissions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)            
    

    building_sf_band = Column(String, index=True)
    submarket_geo = Column(String, index=True)
    building_class = Column(String, index=True)
    building_sf = Column(String)

    realestate_taxes_psf = Column(Numeric)
    property_insurance_psf = Column(Numeric)
    utilities_psf = Column(Numeric)
    janitorial_psf = Column(Numeric)
    prop_mgmt_fees_psf = Column(Numeric)
    security_psf = Column(Numeric)
    admin_charges_psf = Column(Numeric)
    ti_buildout_psf = Column(Numeric)
    capex_major_psf = Column(Numeric)
    commission_advert_psf = Column(Numeric)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())

    company = relationship("Company", back_populates="det_expense_submissions")

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

    user = relationship("User")



class Building(Base):
    __tablename__ = "building"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    category = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"))
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("User", back_populates="buildings")
    files = relationship(
        "BuildingFile",
        back_populates="building",
        cascade="all, delete-orphan"
    )



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

    building = relationship("Building", back_populates="files")



class StandaloneFile(Base):
    __tablename__ = "standalone_files"

    file_id = Column(String, primary_key=True)
    original_file_name = Column(String, nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"))
    building_id = Column(Integer, ForeignKey("building.id", ondelete="SET NULL"))
    category = Column(String, nullable=False)

    uploaded_at = Column(DateTime, default=datetime.utcnow)
    gcs_path = Column(String, nullable=True)
    file_size = Column(String, nullable=True, default="0")
    structured_metadata = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="standalone_files")
    building = relationship("Building")



class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    feedback = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    company = relationship("Company")



class Tour(Base):
    __tablename__ = "tours"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False)

    building = Column(String, nullable=False)
    floor_suite = Column(String, nullable=True)
    tenant = Column(String, nullable=True)
    broker = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="tours")
    company = relationship("Company", back_populates="tours")



class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    user = relationship("User", back_populates="email_templates")



class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    name = Column(String(255), nullable=False)
    data = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="tenants")

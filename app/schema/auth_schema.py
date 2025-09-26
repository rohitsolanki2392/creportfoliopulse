
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    message: str
    role: str  

class UserRegister(BaseModel):
    name: str
    number: str
    email: EmailStr
    confirm_password: str
    password: str
    role: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = None  


class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class UserProfile(BaseModel):
    id: int
    name: str
    number: str
    email: str
    role: str
    photo_url: Optional[str] = None
    photo_base64: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class UserUpdateProfile(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None

class InviteAdminRequest(BaseModel):
    company_name: str
    admin_name: str
    email: EmailStr
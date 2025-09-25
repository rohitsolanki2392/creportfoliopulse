import os
import random
import string
from email.message import EmailMessage
import smtplib
from datetime import datetime
from fastapi.security import OAuth2PasswordBearer
from app.database.db import SessionLocal
from app.models.models import OTP



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")



def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

async def send_otp_email(email: str, otp: str, subject: str):
    try:
        msg = EmailMessage()
        msg.set_content(f"""
        Hello,
        Your OTP for verification is: {otp}
        This OTP will expire in 10 minutes.
        If you didn't request this, please ignore this email.
        Best regards,
        Your App Team
        """)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")


def cleanup_expired_otps():
    current_time = datetime.utcnow()
    db = SessionLocal()
    try:
        expired_otps = db.query(OTP).filter(OTP.expires_at < current_time).all()
        for otp in expired_otps:
            db.delete(otp)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
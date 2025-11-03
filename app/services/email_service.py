import logging
import random
import string
from email.message import EmailMessage
import aiosmtplib  
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import OTP
from fastapi import HTTPException
from app.config import EMAIL_PASSWORD, EMAIL_SENDER, SMTP_PORT, SMTP_SERVER
from sqlalchemy.ext.asyncio import AsyncSession
def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


async def send_otp_email(email: str, otp: str):
    try:
        msg = EmailMessage()
        subject = "Your Code for Verification"
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

        await aiosmtplib.send(
            msg,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=EMAIL_SENDER,
            password=EMAIL_PASSWORD
        )
    except Exception as e:
        print(f"Error sending email: {e}")



logger = logging.getLogger(__name__)

async def cleanup_expired_otps(db: AsyncSession):
    """Clean up expired OTP records safely."""
    current_time = datetime.utcnow()

    try:
        result = await db.execute(select(OTP).where(OTP.expires_at < current_time))
        expired_otps = result.scalars().all()

        if expired_otps:
            for otp in expired_otps:
                await db.delete(otp)
            await db.commit()
            logger.info(f"Deleted {len(expired_otps)} expired OTP(s) successfully.")
        else:
            logger.info("No expired OTPs found during cleanup.")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to clean expired OTPs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            message=f"Failed to clean expired OTPs: {str(e)}"
        )


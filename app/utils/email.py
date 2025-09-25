

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def send_email(to_email: str, subject: str, body: str):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        raise Exception("Missing EMAIL_SENDER or EMAIL_PASSWORD in environment variables")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

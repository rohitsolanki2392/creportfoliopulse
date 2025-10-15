

import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from app.config import SMTP_SERVER,SMTP_PORT,EMAIL_SENDER,EMAIL_PASSWORD
load_dotenv()

def send_email(to_email: str, subject: str, body: str):
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    sender_email =EMAIL_SENDER
    sender_password =EMAIL_PASSWORD

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

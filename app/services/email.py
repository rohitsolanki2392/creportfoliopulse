# import smtplib
# from email.mime.text import MIMEText
# import os 
# from dotenv import load_dotenv  

# load_dotenv()

# def send_otp_email(to_email: str, body: str, subject: str):
#     smtp_server = "smtp.gmail.com"
#     smtp_port = 587
#     sender_email = os.getenv("EMAIL_SENDER")
#     sender_password = os.getenv("EMAIL_PASSWORD")
#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = sender_email
#     msg["To"] = to_email
    
#     try:
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(sender_email, sender_password)
#             server.sendmail(sender_email, to_email, msg.as_string())
#     except Exception as e:
#         raise Exception(f"Failed to send email: {str(e)}")

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Email configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

def send_otp_email(email: str, otp: str) -> bool:
    """
    Send OTP email to the user.
    Returns True if successful, False otherwise.
    
    Note: This is a synchronous implementation. In production, consider
    using background tasks (e.g., Celery) to avoid blocking the request.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Email configuration missing. Would send OTP {otp} to {email}")
        # In development, you might want to just print the OTP
        # In production, this should raise an error or use a proper email service
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = email
        msg["Subject"] = "Your password reset OTP"
        
        # Email body
        body = f"""Your password reset OTP is {otp}. It will expire in 10 minutes.
        
If you did not request this password reset, please ignore this email.
"""
        
        msg.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"Failed to send OTP email to {email}: {str(e)}")
        # In production, you might want to log this to a proper logging service
        return False


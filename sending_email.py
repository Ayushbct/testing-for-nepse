import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()
def send_email(subject = 'Default Subject',body = 'Default Body'):
    
    USER_EMAIL = os.environ.get("USER_EMAIL")
    USER_PASSWORD = os.environ.get("USER_PASSWORD")

    # Email configuration
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = USER_EMAIL
    sender_password = USER_PASSWORD
    recipient_email = USER_EMAIL
    # subject = 'Hello from Python'
    # body = 'This is a test message sent using Python and SMTP.'
    
    # Create the email message
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.set_content(body)
    
    # Send the email via SMTP
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print('Email sent successfully!')
    except Exception as e:
        print(f'Error sending email: {e}')


    

if __name__ == "__main__":
    
    send_email()
    
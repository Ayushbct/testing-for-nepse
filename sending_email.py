import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()
def send_email(subject = 'Default Subject', body = 'Default Body', attachment_path = None):
    
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
    
    # Add attachment if provided
    if attachment_path and os.path.isfile(attachment_path):
        try:
            with open(attachment_path, 'rb') as attachment:
                file_name = os.path.basename(attachment_path)
                # Determine the MIME type based on file extension
                if attachment_path.endswith('.csv'):
                    maintype, subtype = 'text', 'csv'
                elif attachment_path.endswith('.txt'):
                    maintype, subtype = 'text', 'plain'
                elif attachment_path.endswith('.xlsx') or attachment_path.endswith('.xls'):
                    maintype, subtype = 'application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif attachment_path.endswith('.pdf'):
                    maintype, subtype = 'application', 'pdf'
                else:
                    maintype, subtype = 'application', 'octet-stream'
                
                msg.add_attachment(
                    attachment.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=file_name
                )
                print(f'Attachment added: {file_name}')
        except Exception as e:
            print(f'Error adding attachment: {e}')
    
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
    
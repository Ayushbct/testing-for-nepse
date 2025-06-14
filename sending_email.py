import smtplib, ssl
import os
from dotenv import load_dotenv
load_dotenv()
def send_email():
    

    port = 465
    smtp_server = "smtp.gmail.com"
    # USER_EMAIL = os.environ.get("USER_EMAIL")
    
    # USER_PASSWORD = os.environ.get("USER_PASSWORD")
    

    message = """\
        Subject: Welcome Ubaydah

        This is your welcome email running 
    """

    context = ssl.create_default_context()

    server = smtplib.SMTP_SSL(smtp_server, port, context=context)

    server.login(USER_EMAIL, USER_PASSWORD)
    server.sendmail(USER_EMAIL, USER_EMAIL, message)

    print("Email Sucessfully Sent")

if __name__ == "__main__":
    
    # send_email()
    USER_EMAIL = os.environ.get("USER_EMAIL")
    
    USER_PASSWORD = os.environ.get("DATABASE_NAME")
    
    print(USER_EMAIL,USER_PASSWORD)
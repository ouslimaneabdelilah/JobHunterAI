import smtplib
from email.message import EmailMessage
import os

def send_email_with_attachments(sender_email, sender_password, recipient_email, subject, body, resume_path, letter_path):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content(body)
    
    files_to_attach = [resume_path, letter_path]
    
    for fpath in files_to_attach:
        if fpath and os.path.exists(fpath):
            with open(fpath, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(fpath)
                msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

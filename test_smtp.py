import smtplib, ssl
from email.message import EmailMessage

smtp_user = "tuser1595@gmail.com"
smtp_pass = "hpjkdyjfkvvgtyfy"   # use the password WITHOUT spaces

msg = EmailMessage()
msg["Subject"] = "SMTP Test — Keycloak Email Project"
msg["From"] = smtp_user
msg["To"] = smtp_user
msg.set_content("Hello — SMTP test from Keycloak Email project is working.")

context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    print("SMTP test email sent successfully!")
except Exception as e:
    print("SMTP test failed:", e)

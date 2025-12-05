import smtplib, ssl
from email.message import EmailMessage

msg = EmailMessage()
msg["From"] = "you@example.com"
msg["To"] = "approver@example.com"
msg["Subject"] = "Test email from SendGrid setup"
msg.set_content("This is just a test message from our Python app.")

server = smtplib.SMTP("smtp.sendgrid.net", 587)
server.starttls()
server.login("apikey", "YOUR_SENDGRID_API_KEY")
server.send_message(msg)
server.quit()
print("Mail sent!")

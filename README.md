


---

# **Keycloak Email Approval System (with MailerSend & Tailwind Email Templates)**

A production-ready automated **Access Request Approval System** integrating:

* **Keycloak IAM** (for users & roles)
* **MailerSend** (for email delivery)
* **FastAPI + SQLite/Postgres** backend
* **Tailwind-styled HTML email templates**
* **Approve / Reject flow with secure tokens**
* **Automatic confirmation emails to requester**
* **48-hour reminder scheduler**

This README explains how to install, configure, run, and test the entire project.

---

## ⭐ **1. Project Overview**

This system allows users to request roles in Keycloak.
Approvers receive an email containing:

* **Approve** link
* **Reject** link

When the approver clicks:

* The callback validates a JWT token
* Keycloak role is assigned (for Approve)
* A **confirmation email is sent to the requester**
* Audit logs are recorded
* Token is marked as used

Emails are styled using **Tailwind CSS** (lightweight, modern design).

---

## 🚀 **2. Key Features**

### **Core Functionality**

✔ Create access request
✔ Send approval email with Tailwind styling
✔ Approve / Reject request via email link
✔ Update user roles in Keycloak
✔ Send confirmation email back to requester
✔ Store audit logs
✔ Secure JWT tokens, single-use
✔ 48-hour reminder emails (APScheduler)

### **Email Delivery**

✔ Works with **MailerSend** (default)
✔ Supports SMTP fallback (Gmail/Outlook/etc.)
✔ Uses mailer factory (`MAILER_BACKEND`) to switch providers easily

### **Templates**

✔ Beautiful Tailwind-styled HTML emails
✔ Plain-text fallback templates
✔ Separate confirmation email templates

---

## 🏗 **3. Architecture Diagram**

```
         +---------------------+
         |      Requester      |
         +----------+----------+
                    |
      POST /api/v1/requests
                    |
                    v
         +---------------------+
         |     FastAPI API     |
         |  (Access Request)   |
         +----------+----------+
                    |
                    | Create tokens (approve/reject)
                    v
         +---------------------+
         |    Mailer Backend   |
         |  MailerSend / SMTP  |
         +----------+----------+
                    |
               Send Email
                    |
                    v
        +-----------------------+
        |       Approver        |
        +-------------+---------+
                      |
                Click Approve /
                    Reject
                      |
                      v
         +---------------------+
         |     /callback       |
         +----------+----------+
                    |
      Validate token, update Keycloak,
      mark token used, send notification
                    |
                    v
         +---------------------+
         |      Requester      |
         | Confirmation Email  |
         +---------------------+
```

---

## 📂 **4. Project Folder Structure**

```
keycloak-mailersend/
├─ .env.example
├─ requirements.txt
├─ README.md
├─ run_dev.bat
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ db.py
│  ├─ models.py
│  ├─ schemas.py
│  ├─ tokens.py
│  ├─ keycloak_client.py
│  ├─ tasks.py
│  ├─ mailer_factory.py
│  ├─ mailer_smtp.py
│  ├─ mailer_utils.py
│  ├─ mailers/
│  │   └─ mailersend_adapter.py
│  └─ templates/
│      ├─ approve_email.html
│      ├─ approve_email.txt
│      ├─ response_email.html
│      └─ response_email.txt
└─ tests/
   ├─ test_token.py
   └─ test_mailersend_adapter.py
```

---

## 🔧 **5. Setup Guide**

### **Install dependencies**

```sh
python -m venv .venv
source .venv/bin/activate     # Mac/Linux
.venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### **Copy environment file**

```sh
cp .env.example .env   # or copy manually
```

Fill values in `.env`:

```
KEYCLOAK_CLIENT_SECRET=...
MAILERSEND_API_KEY=...
MAILERSEND_FROM_EMAIL=...
MAILER_BACKEND=mailersend
APP_BASE=http://localhost:8081
```

---

## 🔐 **6. Configure Keycloak**

### Steps:

1. Login to Keycloak Admin Console
2. Create realm (optional)
3. Create client:

```
client_id = email-automation-client
access_type = confidential
service accounts enabled = ON
```

4. Add realm-management roles to service account:

* manage-users
* view-users
* view-realm

5. Create test users:

   * requester (ex: [alice@example.com](mailto:alice@example.com))
   * approver (ex: [approver@example.com](mailto:approver@example.com))

6. Create role:

   * project_access

7. **Copy client secret** into `.env`

---

## 📧 **7. Configure MailerSend**

1. Create account at [https://app.mailersend.com](https://app.mailersend.com)
2. Create API key
3. Add verified sender domain/email
4. Enter values into `.env`:

```
MAILERSEND_API_KEY=...
MAILERSEND_FROM_EMAIL=noreply@yourdomain.com
MAILER_BACKEND=mailersend
```

MailerSend is now ready.

---

## ▶ **8. Running the Project**

Start the server:

```sh
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

Check:

```
http://localhost:8081/health
```

---

## 📌 **9. API Usage**

### **Create a request**

```
POST /api/v1/requests
```

Body:

```json
{
  "keycloak_user_id": "alice",
  "requester_email": "alice@example.com",
  "requested_role": "project_access"
}
```

Response:

```json
{
  "request_id": "uuid-here",
  "status": "pending"
}
```

---

## 📨 **10. Email Flow Explanation**

### Step 1 — User requests access

Tailwind-styled email is sent to the approver.

### Step 2 — Approver clicks Approve/Reject

➡ Token validated
➡ Keycloak updated
➡ Token marked used

### Step 3 — Requester gets confirmation email

Example:

> Your request for role *project_access* has been **approved**.

### Step 4 — Audit logs are recorded

Stored in `audit_logs` table.

### Step 5 — Reminder scheduler

After 48 hours, if no action → reminder email sent.

---

## 🎨 **11. Tailwind Email Templates**

Templates used:

* `approve_email.html` → sent to approver
* `response_email.html` → sent back to requester

These use Tailwind CDN for styling.

> Some strict email clients block external JS (Tailwind CDN).
> If you want **maximum email compatibility**, ask for an **inline CSS version**, I can generate it.

---

## 🔁 **12. Switching Email Backends**

`.env`:

```
MAILER_BACKEND=mailersend
```

OR fallback to SMTP:

```
MAILER_BACKEND=smtp
SMTP_USER=...
SMTP_PASS=...
```

No code changes needed — factory auto-selects backend.

---

## 🧪 **13. Testing**

Run all tests:

```sh
pytest -q
```

Command to Send Request email : 
```
curl -s -X POST http://127.0.0.1:8081/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"keycloak_user_id":"madman","requester_email":"mad571869@gmail.com","requested_role":"project_access","metadata":{}}' | jq

```
This tests:

* token creation
* token expiry
* mailersend adapter
* retry logic
* rate-limiting handling

---

## 🛠 **14. Troubleshooting**

| Issue                                 | Cause                            | Fix                              |
| ------------------------------------- | -------------------------------- | -------------------------------- |
| No email received                     | Invalid sender / DNS             | Verify MailerSend domain         |
| Callback returns “token already used” | Link clicked twice               | Normal behavior                  |
| Keycloak error                        | Wrong client secret or role name | Recheck `.env` and Keycloak role |
| Tailwind not loading                  | Email client blocked JS          | Ask for inline-CSS version       |

---

## 🚀 **15. Future Enhancements**

* Inline CSS for 100% email client compatibility
* Approver comments in approval UI
* Dashboard for admins
* Slack or Teams integration
* Multi-step approval chain

---

## 🏁 **16. License**

MIT License – free for personal or enterprise use.

---

If you'd like, I can also generate:
✅ A **PDF** version of this README
✅ Inline-CSS email templates
✅ A GitHub README badge pack
✅ Complete Postman collection for testing

Just tell me!

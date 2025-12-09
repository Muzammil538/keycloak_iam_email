# API Email Workflow Guide

## Overview
This guide shows how to use the API to:
1. Create an access request from `madman531@gmail.com`
2. Approve/reject the request
3. Receive confirmation emails at `madman531@gmail.com`

## Prerequisites
- Server running on `http://localhost:8081`
- Gmail SMTP configured (already set up)
- `curl` or similar HTTP client

## Server Status
Start the server with:
```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

Check if server is running:
```bash
curl http://localhost:8081/health
# Expected response: {"status":"ok"}
```

---

## Complete Workflow

### Option 1: Run the Full Demo Script (Easiest)

```bash
./demo_workflow.sh
```

This script will:
1. ✅ Create a request from `madman531@gmail.com`
2. ✅ Approve the request
3. ✅ Display the request ID and UI links

### Option 2: Manual API Calls (Full Control)

#### Step 1: Create Access Request

```bash
curl -X POST "http://localhost:8081/api/v1/requests" \
  -H "Content-Type: application/json" \
  -d '{
    "keycloak_user_id": "madman531",
    "requester_email": "madman531@gmail.com",
    "requested_role": "admin_access",
    "metadata": {"reason": "Testing email workflow"}
  }'
```

**Expected Response:**
```json
{
  "request_id": "a091f8e9-f3c1-4720-b0ae-7a91dba6745a",
  "status": "pending"
}
```

**What happens:**
- ✅ Request is created in the database
- ✅ Status is set to `pending`
- 📧 Initial approval request email sent to `approver@example.com` (hardcoded in the system)
- 💾 Save the `request_id` for the next step

---

#### Step 2: Approve the Request

Replace `{REQUEST_ID}` with the ID from Step 1:

```bash
curl -X POST "http://localhost:8081/admin/requests/{REQUEST_ID}/action" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

**Example:**
```bash
curl -X POST "http://localhost:8081/admin/requests/a091f8e9-f3c1-4720-b0ae-7a91dba6745a/action" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

**Expected Response (if Keycloak running):**
```json
{"ok": true, "status": "approved"}
```

**Expected Response (Keycloak not running):**
```
Keycloak error: 401: b'{"error":"HTTP 401 Unauthorized"}'
```

**What happens:**
- 📧 Confirmation email sent to `madman531@gmail.com`
  - Subject: `Your access request for admin_access has been approved`
  - Email body shows the decision and details

---

#### Step 3: (Alternative) Reject the Request

If you want to reject instead of approve:

```bash
curl -X POST "http://localhost:8081/admin/requests/{REQUEST_ID}/action" \
  -H "Content-Type: application/json" \
  -d '{"action": "reject"}'
```

**What happens:**
- 📧 Rejection email sent to `madman531@gmail.com`
  - Subject: `Your access request for admin_access has been rejected`

---

## View Request Status

### In the Browser
Visit the admin UI:
```
http://localhost:8081/admin/requests
```

Click "View" on any request to see full details including:
- Email preview
- Request ID
- Requester email: `madman531@gmail.com`
- Requested role
- Current status
- Approve/Reject buttons

### Via API
Get all requests:
```bash
curl "http://localhost:8081/admin/requests"
```

Get specific request:
```bash
curl "http://localhost:8081/admin/requests/{REQUEST_ID}"
```

---

## Email Flow

### Initial Request Email (When request is created)
**To:** `approver@example.com` (hardcoded)  
**Subject:** `[Action Required] Access request for madman531@gmail.com`  
**Body:** Shows approval/rejection links with tokens

### Approval Confirmation Email (When approved)
**To:** `madman531@gmail.com` (requester)  
**Subject:** `Your access request for admin_access has been approved`  
**Body:** Confirmation message

### Rejection Email (When rejected)
**To:** `madman531@gmail.com` (requester)  
**Subject:** `Your access request for admin_access has been rejected`  
**Body:** Rejection message

---

## Quick Copy-Paste Commands

### Create a request and get the ID
```bash
curl -s -X POST "http://localhost:8081/api/v1/requests" \
  -H "Content-Type: application/json" \
  -d '{"keycloak_user_id":"madman531","requester_email":"madman531@gmail.com","requested_role":"admin_access","metadata":{}}' \
  | grep -o '"request_id":"[^"]*' | cut -d'"' -f4
```

### Approve a request (replace REQUEST_ID)
```bash
REQUEST_ID="a091f8e9-f3c1-4720-b0ae-7a91dba6745a"
curl -X POST "http://localhost:8081/admin/requests/$REQUEST_ID/action" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve"}'
```

### Check inbox (admin UI)
```
http://localhost:8081/admin/requests
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Server not running" | Start server: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8081` |
| Email not received | Check SMTP credentials in `.env`: `SMTP_USER`, `SMTP_PASS` |
| 404 on API calls | Verify port is 8081, not 8080 |
| Keycloak error on approve | Keycloak service not running (expected for testing) |
| "approver@example.com" hardcoded | Edit `app/tasks.py` line 41 to change approver email |

---

## Modifying Approver Email

Currently, the approver email is hardcoded to `approver@example.com`.  
To change it, edit `app/tasks.py`:

```python
# Line ~41 in send_initial_email()
approver_email = "your-email@gmail.com"  # Change this
```

Or in `app/main.py` (line ~82):
```python
# Change this line
approver_email = "approver@example.com"
# To:
approver_email = "your-email@gmail.com"
```

---

## What's Working ✅

- Creating requests via API
- Storing requests in SQLite database
- Sending confirmation emails via Gmail SMTP
- Admin UI to view and manage requests
- Approve/reject workflow (except Keycloak role assignment if Keycloak not running)

## What Requires Keycloak ⚙️

- Actual role assignment to users
- User authentication (currently no auth on admin pages)

---

## Next Steps

1. **Test the workflow:** Run `./demo_workflow.sh`
2. **Check email:** Look for emails in `madman531@gmail.com` inbox
3. **Modify approver:** Change approver email if needed
4. **Deploy:** When ready, use production settings and enable authentication

---

## Contact & Support

For issues or questions, check:
- Server logs: Terminal output
- Database: `sqlite3 data/iam.db`
- API docs: `http://localhost:8081/docs`

#!/usr/bin/env python3
"""
Simple script to test inbound email webhook by posting sample payloads.
Simulates Gmail messages arriving via the MailerSend inbound webhook.

Usage:
    python test_inbound_email.py [--host localhost] [--port 8080]

Examples:
    # Local testing
    python test_inbound_email.py

    # Remote testing via ngrok
    python test_inbound_email.py --host abcd1234.ngrok.io --port 443
"""

import requests
import json
import argparse
from datetime import datetime

def send_test_email(host="localhost", port=8080, use_https=False):
    """Send a test inbound email payload to the webhook."""
    
    protocol = "https" if use_https else "http"
    url = f"{protocol}://{host}:{port}/webhook/mailersend/inbound"
    
    # Sample email payload (matches MailerSend inbound format)
    payload = {
        "from": {
            "email": "friend@gmail.com",
            "name": "Gmail Friend"
        },
        "to": [
            {
                "email": "noreply@example.com"
            }
        ],
        "subject": "Test email from Gmail",
        "text": "This is a test message sent from Gmail to test the inbound webhook.",
        "html": "<p>This is a <strong>test message</strong> sent from Gmail.</p>",
        "message_id": f"<test-msg-{datetime.now().timestamp()}@gmail.com>"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"📧 Sending test email to {url}")
    print(f"   From: {payload['from']['email']}")
    print(f"   Subject: {payload['subject']}")
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n✓ Response: {resp.status_code}")
        print(f"  Body: {resp.text}")
        
        if resp.status_code in (200, 201):
            print("\n✅ Email received successfully!")
            data = resp.json()
            if data.get("id"):
                print(f"   Stored with ID: {data['id']}")
        else:
            print("\n❌ Email not accepted. Check server logs.")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {url}")
        print("   Is the server running?")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def send_multiple_test_emails(host="localhost", port=8080, use_https=False, count=3):
    """Send multiple test emails with different content."""
    
    test_emails = [
        {
            "from_email": "alice@gmail.com",
            "from_name": "Alice",
            "subject": "Access Request Test",
            "text": "I would like to request access to the project management role."
        },
        {
            "from_email": "bob@example.com",
            "from_name": "Bob",
            "subject": "Need Admin Access",
            "text": "Please approve my request for admin access to the system."
        },
        {
            "from_email": "charlie@company.com",
            "from_name": "Charlie",
            "subject": "Role Escalation Request",
            "text": "Requesting elevation to the team lead role for Project X."
        }
    ]
    
    for i, email_data in enumerate(test_emails[:count], 1):
        payload = {
            "from": {
                "email": email_data["from_email"],
                "name": email_data["from_name"]
            },
            "to": [{"email": "approver@example.com"}],
            "subject": email_data["subject"],
            "text": email_data["text"],
            "html": f"<p>{email_data['text']}</p>",
            "message_id": f"<msg-{i}-{datetime.now().timestamp()}@example.com>"
        }
        
        protocol = "https" if use_https else "http"
        url = f"{protocol}://{host}:{port}/webhook/mailersend/inbound"
        
        print(f"\n[{i}/{count}] Sending: {email_data['subject']}")
        
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code in (200, 201):
                print(f"     ✓ Accepted")
            else:
                print(f"     ✗ Failed ({resp.status_code})")
        except Exception as e:
            print(f"     ✗ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send test inbound emails to the IAM webhook")
    parser.add_argument("--host", default="localhost", help="Host (default: localhost)")
    parser.add_argument("--port", type=int, default=8081, help="Port (default: 8081)")
    parser.add_argument("--https", action="store_true", help="Use HTTPS (for ngrok)")
    parser.add_argument("--multiple", "-m", type=int, default=1, help="Send multiple test emails (default: 1)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("IAM Email Inbound Webhook Test")
    print("=" * 60)
    
    if args.multiple > 1:
        send_multiple_test_emails(args.host, args.port, args.https, args.multiple)
    else:
        send_test_email(args.host, args.port, args.https)
    
    print("\n" + "=" * 60)
    print("✓ Test complete. Check the database to see inbound emails:")
    print("  sqlite3 data/iam.db 'SELECT id, from_email, subject, received_at FROM inbound_emails ORDER BY received_at DESC LIMIT 10;'")
    print("=" * 60)

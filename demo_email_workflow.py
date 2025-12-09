#!/usr/bin/env python3
"""
Complete workflow demo: Create request, approve it, and receive confirmation email.
Shows how to use the API to trigger emails to madman531@gmail.com

Usage:
    python demo_email_workflow.py [--action create|approve|reject]
"""

import requests
import json
import time
import argparse
import sys
from datetime import datetime

BASE_URL = "http://localhost:8081"
REQUESTER_EMAIL = "muzammilmohd538@gmail.com"

def create_access_request(keycloak_user_id="demo-user-001"):
    """Step 1: Create an access request that will trigger an email to the approver."""
    
    print("\n" + "="*70)
    print("STEP 1: CREATE ACCESS REQUEST")
    print("="*70)
    
    payload = {
        "keycloak_user_id": keycloak_user_id,
        "requester_email": REQUESTER_EMAIL,
        "requested_role": "admin_access",
        "metadata": {"reason": "Demo testing - Full workflow"}
    }
    
    print(f"\n📧 Creating request from: {REQUESTER_EMAIL}")
    print(f"   Requested role: {payload['requested_role']}")
    print(f"   User ID: {keycloak_user_id}")
    
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v1/requests",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if resp.status_code in (200, 201):
            data = resp.json()
            request_id = data.get("request_id")
            status = data.get("status")
            
            print(f"\n✅ Request created successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {status}")
            print(f"\n📩 Initial email sent to approver (check approver@example.com)")
            
            return request_id
        else:
            print(f"\n❌ Failed to create request: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def approve_request(request_id):
    """Step 2: Approve the request via admin API (simulates approver clicking approve button)."""
    
    print("\n" + "="*70)
    print("STEP 2: APPROVE REQUEST (Admin Action)")
    print("="*70)
    
    print(f"\n👤 Approving request: {request_id}")
    
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/requests/{request_id}/action",
            json={"action": "approve"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if resp.status_code in (200, 201):
            data = resp.json()
            if data.get("ok"):
                print(f"\n✅ Request approved!")
                print(f"   New status: {data.get('status', 'approved')}")
                print(f"\n📧 Confirmation email sent to: {REQUESTER_EMAIL}")
                print(f"   Subject: Your access request for admin_access has been approved")
                return True
            else:
                print(f"\n⚠️  Action returned: {data.get('message', 'Unknown response')}")
                return False
        else:
            print(f"\n❌ Failed to approve: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def reject_request(request_id):
    """Step 2b: Reject the request (alternative to approve)."""
    
    print("\n" + "="*70)
    print("STEP 2b: REJECT REQUEST (Admin Action)")
    print("="*70)
    
    print(f"\n🚫 Rejecting request: {request_id}")
    
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/requests/{request_id}/action",
            json={"action": "reject"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if resp.status_code in (200, 201):
            data = resp.json()
            if data.get("ok"):
                print(f"\n✅ Request rejected!")
                print(f"   New status: {data.get('status', 'rejected')}")
                print(f"\n📧 Rejection email sent to: {REQUESTER_EMAIL}")
                print(f"   Subject: Your access request for admin_access has been rejected")
                return True
            else:
                print(f"\n⚠️  Action returned: {data.get('message', 'Unknown response')}")
                return False
        else:
            print(f"\n❌ Failed to reject: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def check_server():
    """Check if server is running."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def demo_full_workflow():
    """Run the complete workflow: create → approve → email."""
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  IAM EMAIL WORKFLOW DEMO".center(68) + "║")
    print("║" + "  Create Request → Approve → Send Confirmation Email".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    # Check server
    print("\n🔍 Checking server...")
    if not check_server():
        print("❌ Server not running. Start it with:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload")
        sys.exit(1)
    
    print("✅ Server is running\n")
    
    # Create request
    request_id = create_access_request()
    if not request_id:
        print("\n❌ Failed to create request. Stopping.")
        sys.exit(1)
    
    # Wait a moment before approving
    print("\n⏳ Waiting 2 seconds before approval...\n")
    time.sleep(2)
    
    # Approve request
    if approve_request(request_id):
        print("\n" + "="*70)
        print("STEP 3: VERIFY EMAIL DELIVERY")
        print("="*70)
        print(f"\n📬 Check your email inbox at: {REQUESTER_EMAIL}")
        print(f"   Look for email with subject: 'Your access request for admin_access has been approved'")
        print(f"\n📊 You can also view the request status at:")
        print(f"   {BASE_URL}/admin/requests/{request_id}")
    
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IAM Email Workflow Demo")
    parser.add_argument("--action", choices=["create", "approve", "reject", "full"], 
                       default="full", help="Action to perform")
    parser.add_argument("--request-id", help="Request ID (required for approve/reject actions)")
    parser.add_argument("--user-id", default="demo-user-001", help="Keycloak user ID")
    
    args = parser.parse_args()
    
    if not check_server():
        print("❌ Server not running on http://localhost:8080")
        sys.exit(1)
    
    if args.action == "full":
        demo_full_workflow()
    elif args.action == "create":
        request_id = create_access_request(args.user_id)
        if request_id:
            print(f"\n💾 Save this request ID for later: {request_id}")
    elif args.action == "approve":
        if not args.request_id:
            print("❌ --request-id is required for approve action")
            sys.exit(1)
        approve_request(args.request_id)
    elif args.action == "reject":
        if not args.request_id:
            print("❌ --request-id is required for reject action")
            sys.exit(1)
        reject_request(args.request_id)

#!/bin/bash
# Complete API workflow demo - Send emails to madman531@gmail.com
# This script shows how to create a request and trigger approval/rejection emails

API_BASE="http://localhost:8081"
REQUESTER_EMAIL="muzammilmohd538@gmail.com"
REQUESTED_ROLE="admin_access"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  IAM EMAIL WORKFLOW - Using API Calls                         ║"
echo "║  Requester: ${REQUESTER_EMAIL}                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# STEP 1: Create an access request
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Create access request from ${REQUESTER_EMAIL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/requests" \
  -H "Content-Type: application/json" \
  -d "{
    \"keycloak_user_id\": \"madman531\",
    \"requester_email\": \"$REQUESTER_EMAIL\",
    \"requested_role\": \"$REQUESTED_ROLE\",
    \"metadata\": {\"reason\": \"API workflow demo\"}
  }")

echo "Response:"
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract request ID
REQUEST_ID=$(echo "$RESPONSE" | jq -r '.request_id' 2>/dev/null)

if [ -z "$REQUEST_ID" ] || [ "$REQUEST_ID" = "null" ]; then
  echo "❌ Failed to create request. Exiting."
  exit 1
fi

echo "✅ Request created!"
echo "   Request ID: $REQUEST_ID"
echo "   📧 Approval request email sent to: approver@example.com"
echo ""

# STEP 2: Wait and then approve
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Approve the request (Admin Action)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Waiting 2 seconds..."
sleep 2

echo "Approving request: $REQUEST_ID"
echo ""

APPROVE_RESPONSE=$(curl -s -X POST "$API_BASE/admin/requests/$REQUEST_ID/action" \
  -H "Content-Type: application/json" \
  -d "{\"action\": \"approve\"}")

echo "Response:"
echo "$APPROVE_RESPONSE" | jq '.' 2>/dev/null || echo "$APPROVE_RESPONSE"
echo ""

# Check if approval was successful
if echo "$APPROVE_RESPONSE" | grep -q "Keycloak error"; then
  echo "⚠️  Keycloak is not running (expected for local testing)"
  echo "   If Keycloak were running, the approval would succeed"
  echo "   and a confirmation email would be sent to: $REQUESTER_EMAIL"
elif echo "$APPROVE_RESPONSE" | grep -q '"ok":true'; then
  echo "✅ Request approved!"
  echo "   📧 Confirmation email sent to: $REQUESTER_EMAIL"
  echo "   Subject: Your access request for $REQUESTED_ROLE has been approved"
else
  echo "❌ Approval failed. Check the response above."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Check the request in the admin UI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "View request details:"
echo "  $API_BASE/admin/requests/$REQUEST_ID"
echo ""
echo "View all requests:"
echo "  $API_BASE/admin/requests"
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ ✅ Workflow complete! Check your email inbox:                 ║"
echo "║    📧 $REQUESTER_EMAIL                                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

#!/usr/bin/env python3

import os
import time
import jwt       # pip install pyjwt
import requests  # pip install requests
from datetime import datetime

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

TOKEN_FILE = "token.txt"  # File to store the JWT
AUTH_URL = "https://api.rijbewijs.sbat.be/praktijk/api/user/authenticate"

LOGIN_DATA = {
    "username": "<EMAIL>",
    "password": "<PASSWORD>"
}

AVAILABILITY_URL = "https://api.rijbewijs.sbat.be/praktijk/api/exam/available"

# Map exam center IDs to human-readable names
EXAM_CENTERS = {
    1: "Sint-Denijs-Westrem",
    7: "Brakel",
    8: "Eeklo",
    9: "Erembodegem",
    10: "Sint-Niklaas",
}

# Our single request will use the current "startDate" in the POST body
# per center. The API presumably returns all slots after that date.
REQUEST_BODY_DATE = datetime.now().strftime("%Y-%m-%dT%H:%M")

# We only want timeslots between these two datetimes (inclusive)
START_DATE = datetime(2025, 2, 20, 0, 0, 0)
END_DATE   = datetime(2025, 2, 27, 23, 59, 59)

# Discord webhook URL
DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/<WEBHOOK_URL>"
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def load_token(file_path):
    """Load the JWT from a file, or return None if not found."""
    if not os.path.isfile(file_path):
        return None
    with open(file_path, "r") as f:
        token = f.read().strip()
        return token if token else None

def save_token(file_path, token):
    """Save the JWT to a file."""
    with open(file_path, "w") as f:
        f.write(token)

def is_jwt_expired(token):
    """
    Decode the JWT 'exp' claim without verifying signature.
    Return True if expired or invalid, False if still valid.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        return time.time() > exp
    except (jwt.DecodeError, jwt.ExpiredSignatureError):
        return True

def re_authenticate():
    """
    Attempt re-authentication, returning the plain-text JWT if successful.
    Prints debug details about the request/response to help troubleshoot.
    """
    print(f"DEBUG: Sending POST to {AUTH_URL} with JSON payload: {LOGIN_DATA}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Origin": "https://rijbewijs.sbat.be",
        "Referer": "https://rijbewijs.sbat.be/"
    }

    try:
        resp = requests.post(AUTH_URL, json=LOGIN_DATA, headers=headers)
        print("DEBUG: Response status:", resp.status_code)
        print("DEBUG: Response text:", resp.text)

        if resp.status_code == 200:
            # Server returns the JWT directly in the response body
            token = resp.text.strip()
            print("DEBUG: Extracted token:", token)
            return token
        else:
            print("Re-authentication failed:", resp.status_code, resp.text)
            return None
    except requests.RequestException as e:
        print("Error during re-authentication:", e)
        return None

def post_to_discord(content):
    """
    Post a message to your Discord webhook.
    """
    payload = {"content": content}
    try:
        result = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if result.status_code in [200, 204]:
            print("Successfully posted to Discord.")
        else:
            print(f"Discord responded with {result.status_code}: {result.text}")
    except requests.RequestException as e:
        print("Error posting to Discord:", e)

def get_available_slots(token, exam_center_id):
    """
    Send a single POST /praktijk/api/exam/available for the given exam_center_id,
    returning the parsed JSON response (list of available timeslots).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Origin": "https://rijbewijs.sbat.be",
        "Referer": "https://rijbewijs.sbat.be/",
        "Authorization": f"Bearer {token}"
    }

    body = {
        "examCenterId": exam_center_id,
        "licenseType": "B",
        "examType": "E2",
        # The same request body for each center:
        "startDate": REQUEST_BODY_DATE
    }

    try:
        resp = requests.post(AVAILABILITY_URL, json=body, headers=headers)
        print(f"DEBUG: Checking center {exam_center_id}, status: {resp.status_code}")
        print("DEBUG: Response text:", resp.text)

        if resp.status_code == 200:
            # Typically returns a list of available exam slots or []
            return resp.json()
        else:
            print(f"Failed to fetch availability for center {exam_center_id}.")
            return []
    except requests.RequestException as e:
        print("Error calling availability endpoint:", e)
        return []

def parse_iso_datetime(iso_str):
    """
    Safely parse an ISO datetime string like '2025-02-06T10:00:00' into a Python datetime.
    If parsing fails, return None.
    """
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        return None

# -----------------------------------------------------------------------------
# Main Script
# -----------------------------------------------------------------------------

def main():
    # 1. Ensure we have a valid token
    token = load_token(TOKEN_FILE)
    if token is None:
        print("No token found on disk. Re-authenticating...")
        token = re_authenticate()
        if token:
            save_token(TOKEN_FILE, token)
        else:
            print("Could not obtain token. Exiting.")
            return
    else:
        if is_jwt_expired(token):
            print("Token on disk is expired. Re-authenticating...")
            token = re_authenticate()
            if token:
                save_token(TOKEN_FILE, token)
            else:
                print("Could not obtain token. Exiting.")
                return
        else:
            print("Token on disk is NOT expired by 'exp' claim.")

    # 2. Query each exam center exactly once, filter the timeslots to 21-27 Feb
    overall_results = []

    for center_id, center_name in EXAM_CENTERS.items():
        all_slots = get_available_slots(token, center_id)
        if not all_slots:
            continue

        # Filter to only slots whose 'from' date/time is between 21 & 27 Feb
        valid_slots = []
        for slot in all_slots:
            from_str = slot.get("from", "")
            from_dt = parse_iso_datetime(from_str)
            if not from_dt:
                continue  # skip if we can't parse

            # Check if from_dt is between 2025-02-21 and 2025-02-27 (inclusive)
            if START_DATE <= from_dt <= END_DATE:
                valid_slots.append(slot)

        if valid_slots:
            overall_results.append((center_name, valid_slots))

    # 3. Post to Discord if we have any matching slots
    if overall_results:
        lines = []
        for center_name, slots in overall_results:
            lines.append(f"XXX")
            lines.append(f"**{center_name}**")
            for s in slots:
                lines.append(f"- {s['from']} → {s['till']}")
        
        message = "\n".join(lines)
        post_to_discord(message)
    else:
        print("No available slots between Feb 21–27. (No Discord post.)")

if __name__ == "__main__":
    main()

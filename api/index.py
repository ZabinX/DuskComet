import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

# --- Environment Variables ---
OAUTH_CLIENT_ID = os.environ.get("TS_OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.environ.get("TS_OAUTH_CLIENT_SECRET")
TAILNET = os.environ.get("TS_TAILNET")
TAG = os.environ.get("TS_TAG")

@app.route("/api/get-key", methods=["POST"])
def get_key():
    """
    Generates a temporary, ephemeral Tailscale authentication key.
    """
    # More detailed check for environment variables
    missing_vars = []
    if not OAUTH_CLIENT_ID:
        missing_vars.append("TS_OAUTH_CLIENT_ID")
    if not OAUTH_CLIENT_SECRET:
        missing_vars.append("TS_OAUTH_CLIENT_SECRET")
    if not TAILNET:
        missing_vars.append("TS_TAILNET")
    if not TAG:
        missing_vars.append("TS_TAG")

    if missing_vars:
        return jsonify({
            "error": f"Server is missing required environment variables: {', '.join(missing_vars)}"
        }), 500

    try:
        # 1. Get an access token from the Tailscale API.
        token_url = "https://api.tailscale.com/api/v2/oauth/token"
        token_data = {
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
        }
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        # 2. Use the access token to generate a new, ephemeral key.
        key_url = f"https://api.tailscale.com/api/v2/tailnet/{TAILNET}/keys"
        key_headers = {"Authorization": f"Bearer {access_token}"}
        key_data = {
            "capabilities": {
                "devices": {
                    "create": {
                        "reusable": False,
                        "ephemeral": True,
                        "preauthorized": False,
                        "tags": [TAG],
                    }
                }
            },
            "expirySeconds": 300,  # The key will be valid for 5 minutes
        }
        key_response = requests.post(key_url, headers=key_headers, json=key_data)
        key_response.raise_for_status()
        new_key = key_response.json()["key"]

        # 3. Return the new key to the client.
        return jsonify({"key": new_key})

    except requests.exceptions.RequestException as e:
        error_message = f"Error communicating with Tailscale API: {e}"
        if e.response is not None:
            error_message += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
        print(error_message)
        return jsonify({"error": "Could not generate Tailscale key", "details": error_message}), 500
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        print(error_message)
        return jsonify({"error": "An internal server error occurred", "details": error_message}), 500

# Vercel will automatically handle running the Flask app.
# The `if __name__ == "__main__":` block is not needed.


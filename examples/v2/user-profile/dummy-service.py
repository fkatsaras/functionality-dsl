#!/usr/bin/env python3
"""
Dummy Profile Storage Service
Simulates profile, preferences, and activity storage with CRUD support
"""

from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# In-memory storage (singletons - one per "user")
profile = {
    "name": "John Doe",
    "email": "john@example.com",
    "bio": "Software developer passionate about clean code",
    "location": "San Francisco, CA",
    "website": "https://johndoe.dev",
    "joined_date": "2024-01-15T10:30:00Z"
}

preferences = {
    "theme": "dark",
    "language": "en",
    "timezone": "America/Los_Angeles",
    "notifications_email": True,
    "notifications_push": False,
    "privacy_public": True
}

activity = {
    "last_login": datetime.now().isoformat() + "Z",
    "login_count": 42,
    "posts_count": 78,
    "comments_count": 156,
    "likes_count": 234
}

# ============================================
# PROFILE ENDPOINTS
# ============================================

@app.route('/profile', methods=['GET'])
def get_profile():
    return jsonify(profile)

@app.route('/profile', methods=['POST'])
def create_profile():
    global profile
    data = request.get_json()
    profile = {
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "bio": data.get("bio", ""),
        "location": data.get("location", ""),
        "website": data.get("website", ""),
        "joined_date": datetime.now().isoformat() + "Z"
    }
    return jsonify(profile)

@app.route('/profile', methods=['PUT'])
def update_profile():
    global profile
    data = request.get_json()
    profile.update({
        "name": data.get("name", profile["name"]),
        "email": data.get("email", profile["email"]),
        "bio": data.get("bio", profile["bio"]),
        "location": data.get("location", profile["location"]),
        "website": data.get("website", profile["website"])
    })
    return jsonify(profile)

@app.route('/profile', methods=['DELETE'])
def delete_profile():
    global profile
    profile = {
        "name": "",
        "email": "",
        "bio": "",
        "location": "",
        "website": "",
        "joined_date": profile["joined_date"]  # Keep join date
    }
    return '', 204

# ============================================
# PREFERENCES ENDPOINTS
# ============================================

@app.route('/preferences', methods=['GET'])
def get_preferences():
    return jsonify(preferences)

@app.route('/preferences', methods=['PUT'])
def update_preferences():
    global preferences
    data = request.get_json()
    preferences.update({
        "theme": data.get("theme", preferences["theme"]),
        "language": data.get("language", preferences["language"]),
        "timezone": data.get("timezone", preferences["timezone"]),
        "notifications_email": data.get("notifications_email", preferences["notifications_email"]),
        "notifications_push": data.get("notifications_push", preferences["notifications_push"]),
        "privacy_public": data.get("privacy_public", preferences["privacy_public"])
    })
    return jsonify(preferences)

# ============================================
# ACTIVITY ENDPOINTS (Read-only)
# ============================================

@app.route('/activity', methods=['GET'])
def get_activity():
    # Update last_login timestamp on each request
    activity["last_login"] = datetime.now().isoformat() + "Z"
    return jsonify(activity)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "profile-storage"})

if __name__ == '__main__':
    print("👤 Profile Storage Service starting on port 9001...")
    print("   • Profile: /profile (GET, POST, PUT, DELETE)")
    print("   • Preferences: /preferences (GET, PUT)")
    print("   • Activity: /activity (GET - readonly)")
    app.run(host='0.0.0.0', port=9001, debug=True)

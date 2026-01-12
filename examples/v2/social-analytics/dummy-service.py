#!/usr/bin/env python3
"""
Dummy Social Media Analytics Service
Simulates campaigns, posts, audiences, and platform metrics for Twitter/Instagram.
"""

from flask import Flask, jsonify, request
from flask_sock import Sock
import random
import time
import json
from datetime import datetime, timedelta

app = Flask(__name__)
sock = Sock(app)

# ============================================
# IN-MEMORY DATA STORES
# ============================================

campaigns = [
    {
        "campaign_id": "CAMP-001",
        "name": "Summer Sale 2024",
        "description": "Promotional campaign for summer products",
        "platform": "all",
        "budget": 5000.00,
        "start_date": datetime.now().isoformat()[:10],
        "end_date": (datetime.now() + timedelta(days=30)).isoformat()[:10],
        "status": "active",
        "created_at": datetime.now().isoformat() + "Z"
    }
]

scheduled_posts = [
    {
        "post_id": "POST-001",
        "campaign_id": "CAMP-001",
        "content": "Check out our amazing summer deals! #SummerSale #Deals",
        "media_url": "https://example.com/images/summer-sale.jpg",
        "platforms": ["twitter", "instagram"],
        "scheduled_time": (datetime.now() + timedelta(hours=2)).isoformat() + "Z",
        "status": "scheduled",
        "hashtags": ["SummerSale", "Deals", "Shopping"]
    }
]

audience_segments = [
    {
        "segment_id": "AUD-001",
        "name": "Young Adults",
        "criteria": {"age_min": 18, "age_max": 35, "interests": ["tech", "fashion"]},
        "estimated_reach": 125000,
        "created_at": datetime.now().isoformat() + "Z"
    }
]

# Simulated platform metrics (updated periodically)
twitter_metrics = {
    "followers": 45230,
    "following": 892,
    "tweets_count": 3421,
    "impressions": 287500,
    "engagements": 12340,
    "likes": 8920,
    "retweets": 2150,
    "replies": 1270,
    "profile_visits": 4560,
    "period": "this_week"
}

instagram_metrics = {
    "followers": 67890,
    "following": 1245,
    "posts_count": 892,
    "impressions": 456000,
    "reach": 312000,
    "likes": 34500,
    "comments": 2890,
    "saves": 1560,
    "shares": 890,
    "period": "this_week"
}

# ID counters
id_counters = {
    "campaign": 2,
    "post": 2,
    "audience": 2
}

# ============================================
# HELPER FUNCTIONS
# ============================================

def vary_metric(base, variance_pct=5):
    """Add some random variance to metrics"""
    variance = base * (variance_pct / 100)
    return int(base + random.uniform(-variance, variance))

def get_twitter_metrics():
    """Return Twitter metrics with slight variation"""
    return {
        "followers": vary_metric(twitter_metrics["followers"], 1),
        "following": twitter_metrics["following"],
        "tweets_count": twitter_metrics["tweets_count"],
        "impressions": vary_metric(twitter_metrics["impressions"], 3),
        "engagements": vary_metric(twitter_metrics["engagements"], 5),
        "likes": vary_metric(twitter_metrics["likes"], 5),
        "retweets": vary_metric(twitter_metrics["retweets"], 8),
        "replies": vary_metric(twitter_metrics["replies"], 10),
        "profile_visits": vary_metric(twitter_metrics["profile_visits"], 5),
        "period": twitter_metrics["period"]
    }

def get_instagram_metrics():
    """Return Instagram metrics with slight variation"""
    return {
        "followers": vary_metric(instagram_metrics["followers"], 1),
        "following": instagram_metrics["following"],
        "posts_count": instagram_metrics["posts_count"],
        "impressions": vary_metric(instagram_metrics["impressions"], 3),
        "reach": vary_metric(instagram_metrics["reach"], 3),
        "likes": vary_metric(instagram_metrics["likes"], 5),
        "comments": vary_metric(instagram_metrics["comments"], 10),
        "saves": vary_metric(instagram_metrics["saves"], 8),
        "shares": vary_metric(instagram_metrics["shares"], 12),
        "period": instagram_metrics["period"]
    }

# ============================================
# CAMPAIGN ENDPOINTS (CRUD)
# ============================================

@app.route('/campaigns', methods=['GET'])
def get_campaign():
    if campaigns:
        return jsonify(campaigns[0])
    return jsonify({})

@app.route('/campaigns', methods=['POST'])
def create_campaign():
    data = request.get_json()

    new_campaign = {
        "campaign_id": f"CAMP-{id_counters['campaign']:03d}",
        "name": data.get("name", "Untitled Campaign"),
        "description": data.get("description"),
        "platform": data.get("platform", "all"),
        "budget": data.get("budget", 0),
        "start_date": data.get("start_date", datetime.now().isoformat()[:10]),
        "end_date": data.get("end_date"),
        "status": "draft",
        "created_at": datetime.now().isoformat() + "Z"
    }

    id_counters['campaign'] += 1
    campaigns.insert(0, new_campaign)

    return jsonify(new_campaign), 201

@app.route('/campaigns', methods=['PUT'])
def update_campaign():
    data = request.get_json()

    if campaigns:
        campaign = campaigns[0]
        for field in ['name', 'description', 'platform', 'budget', 'start_date', 'end_date', 'status']:
            if field in data:
                campaign[field] = data[field]
        return jsonify(campaign)

    return jsonify({"error": "No campaign found"}), 404

@app.route('/campaigns', methods=['DELETE'])
def delete_campaign():
    if campaigns:
        campaigns.pop(0)
        return '', 204
    return jsonify({"error": "No campaign found"}), 404

# ============================================
# SCHEDULED POSTS ENDPOINTS (CRUD)
# ============================================

@app.route('/posts', methods=['GET'])
def get_post():
    if scheduled_posts:
        return jsonify(scheduled_posts[0])
    return jsonify({})

@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()

    new_post = {
        "post_id": f"POST-{id_counters['post']:03d}",
        "campaign_id": data.get("campaign_id"),
        "content": data.get("content", ""),
        "media_url": data.get("media_url"),
        "platforms": data.get("platforms", ["twitter"]),
        "scheduled_time": data.get("scheduled_time"),
        "status": "scheduled",
        "hashtags": data.get("hashtags", [])
    }

    id_counters['post'] += 1
    scheduled_posts.insert(0, new_post)

    return jsonify(new_post), 201

@app.route('/posts', methods=['PUT'])
def update_post():
    data = request.get_json()

    if scheduled_posts:
        post = scheduled_posts[0]
        for field in ['campaign_id', 'content', 'media_url', 'platforms', 'scheduled_time', 'hashtags']:
            if field in data:
                post[field] = data[field]
        return jsonify(post)

    return jsonify({"error": "No post found"}), 404

@app.route('/posts', methods=['DELETE'])
def delete_post():
    if scheduled_posts:
        scheduled_posts.pop(0)
        return '', 204
    return jsonify({"error": "No post found"}), 404

# ============================================
# AUDIENCE SEGMENTS ENDPOINTS (Create/Read/Delete)
# ============================================

@app.route('/audiences', methods=['GET'])
def get_audience():
    if audience_segments:
        return jsonify(audience_segments[0])
    return jsonify({})

@app.route('/audiences', methods=['POST'])
def create_audience():
    data = request.get_json()

    new_audience = {
        "segment_id": f"AUD-{id_counters['audience']:03d}",
        "name": data.get("name", "Untitled Segment"),
        "criteria": data.get("criteria", {}),
        "estimated_reach": random.randint(10000, 500000),
        "created_at": datetime.now().isoformat() + "Z"
    }

    id_counters['audience'] += 1
    audience_segments.insert(0, new_audience)

    return jsonify(new_audience), 201

@app.route('/audiences', methods=['DELETE'])
def delete_audience():
    if audience_segments:
        audience_segments.pop(0)
        return '', 204
    return jsonify({"error": "No audience segment found"}), 404

# ============================================
# METRICS ENDPOINTS (Read-only)
# ============================================

@app.route('/metrics/twitter', methods=['GET'])
def get_twitter():
    return jsonify(get_twitter_metrics())

@app.route('/metrics/instagram', methods=['GET'])
def get_instagram():
    return jsonify(get_instagram_metrics())

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "social-analytics-dummy",
        "campaigns_count": len(campaigns),
        "posts_count": len(scheduled_posts),
        "audiences_count": len(audience_segments)
    })

# ============================================
# WEBSOCKET: Engagement Stream (Inbound to FDSL)
# ============================================

@sock.route('/ws/engagement')
def engagement_stream(ws):
    """Simulates real-time engagement events from social platforms"""
    print("Client connected to /ws/engagement")

    event_types = ["like", "comment", "share", "mention", "retweet", "save"]
    platforms = ["twitter", "instagram"]
    sample_handles = ["@user123", "@socialfan", "@marketguru", "@techie2024", "@fashionista"]

    try:
        while True:
            # Generate random engagement event
            event = {
                "event_type": random.choice(event_types),
                "platform": random.choice(platforms),
                "post_id": f"POST-{random.randint(1, 100):03d}",
                "user_handle": random.choice(sample_handles),
                "timestamp": int(time.time() * 1000)
            }

            ws.send(json.dumps(event))

            # Random interval between events (0.5 to 3 seconds)
            time.sleep(random.uniform(0.5, 3))

    except Exception as e:
        print(f"Engagement stream error: {e}")

# ============================================
# WEBSOCKET: Publish Channel (Outbound from FDSL)
# ============================================

@sock.route('/ws/publish')
def publish_receiver(ws):
    """Receives quick publish commands from marketers"""
    print("Publish channel connected")

    try:
        while True:
            message = ws.receive()
            if message is None:
                break

            try:
                data = json.loads(message)
                print(f"PUBLISH COMMAND RECEIVED:")
                print(f"  Content: {data.get('content', '')[:50]}...")
                print(f"  Platform: {data.get('platform', 'unknown')}")
                print(f"  Media: {data.get('media_url', 'none')}")
                print(f"  Hashtags: {data.get('hashtags', [])}")
                print(f"  Timestamp: {datetime.now().isoformat()}")

                # Simulate publishing delay
                time.sleep(0.5)

                # Send success acknowledgment
                ack = {
                    "status": "published",
                    "post_id": f"LIVE-{int(time.time())}",
                    "platform": data.get("platform", "unknown"),
                    "timestamp": int(time.time() * 1000),
                    "message": "Post published successfully"
                }
                ws.send(json.dumps(ack))

                # Update metrics slightly (simulate engagement from new post)
                twitter_metrics["tweets_count"] += 1
                twitter_metrics["impressions"] += random.randint(100, 500)

            except json.JSONDecodeError as e:
                print(f"Invalid JSON in publish command: {e}")
                ws.send(json.dumps({"status": "error", "message": "Invalid JSON"}))

    except Exception as e:
        print(f"Publish channel error: {e}")

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("Social Analytics Dummy Service starting on port 9001...")
    print("REST Endpoints:")
    print("  • /campaigns (GET, POST, PUT, DELETE)")
    print("  • /posts (GET, POST, PUT, DELETE)")
    print("  • /audiences (GET, POST, DELETE)")
    print("  • /metrics/twitter (GET)")
    print("  • /metrics/instagram (GET)")
    print("WebSocket Endpoints:")
    print("  • /ws/engagement (streams engagement events)")
    print("  • /ws/publish (receives publish commands)")
    app.run(host='0.0.0.0', port=9001, debug=True)

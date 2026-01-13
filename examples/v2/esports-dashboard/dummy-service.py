#!/usr/bin/env python3
"""
Dummy Esports Service - Simulates live match data for the Esports Dashboard example.

Provides:
- REST endpoints for teams, players, matches, leaderboard, predictions
- WebSocket endpoints for live match events and score updates
- WebSocket endpoint for receiving predictions
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, date
from typing import Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Dummy Esports Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Sample Data
# =============================================================================

# Fixed UUIDs for consistent data
TEAM_IDS = {
    "c9": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "tl": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    "g2": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    "t1": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
}

TEAMS = [
    {
        "team_id": TEAM_IDS["c9"],
        "name": "Cloud9",
        "tag": "C9",
        "logo_url": "https://example.com/logos/c9.png",
        "region": "NA",
        "founded_date": "2013-05-01",
        "wins": 156,
        "losses": 78,
        "winrate": 0.67
    },
    {
        "team_id": TEAM_IDS["tl"],
        "name": "Team Liquid",
        "tag": "TL",
        "logo_url": "https://example.com/logos/tl.png",
        "region": "NA",
        "founded_date": "2000-01-01",
        "wins": 189,
        "losses": 92,
        "winrate": 0.67
    },
    {
        "team_id": TEAM_IDS["g2"],
        "name": "G2 Esports",
        "tag": "G2",
        "logo_url": "https://example.com/logos/g2.png",
        "region": "EU",
        "founded_date": "2014-02-24",
        "wins": 210,
        "losses": 85,
        "winrate": 0.71
    },
    {
        "team_id": TEAM_IDS["t1"],
        "name": "T1",
        "tag": "T1",
        "logo_url": "https://example.com/logos/t1.png",
        "region": "KR",
        "founded_date": "2003-12-17",
        "wins": 320,
        "losses": 110,
        "winrate": 0.74
    }
]

PLAYER_IDS = {
    "faker": "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b",
    "caps": "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b0c",
    "corejj": "a7b8c9d0-e1f2-4a3b-4c5d-6e7f8a9b0c1d",
    "blaber": "b8c9d0e1-f2a3-4b4c-5d6e-7f8a9b0c1d2e",
    "jankos": "c9d0e1f2-a3b4-4c5d-6e7f-8a9b0c1d2e3f",
}

PLAYERS = [
    {"player_id": PLAYER_IDS["faker"], "username": "Faker", "real_name": "Lee Sang-hyeok", "team_id": TEAM_IDS["t1"], "role": "Mid", "country": "KR", "avatar_url": "https://example.com/avatars/faker.png", "career_kills": 5200, "career_deaths": 1800, "career_assists": 4100},
    {"player_id": PLAYER_IDS["caps"], "username": "Caps", "real_name": "Rasmus Winther", "team_id": TEAM_IDS["g2"], "role": "Mid", "country": "DK", "avatar_url": "https://example.com/avatars/caps.png", "career_kills": 3800, "career_deaths": 1500, "career_assists": 3200},
    {"player_id": PLAYER_IDS["corejj"], "username": "CoreJJ", "real_name": "Jo Yong-in", "team_id": TEAM_IDS["tl"], "role": "Support", "country": "KR", "avatar_url": "https://example.com/avatars/corejj.png", "career_kills": 1200, "career_deaths": 1100, "career_assists": 5800},
    {"player_id": PLAYER_IDS["blaber"], "username": "Blaber", "real_name": "Robert Huang", "team_id": TEAM_IDS["c9"], "role": "Jungle", "country": "US", "avatar_url": "https://example.com/avatars/blaber.png", "career_kills": 2900, "career_deaths": 1400, "career_assists": 3500},
    {"player_id": PLAYER_IDS["jankos"], "username": "Jankos", "real_name": "Marcin Jankowski", "team_id": TEAM_IDS["g2"], "role": "Jungle", "country": "PL", "avatar_url": "https://example.com/avatars/jankos.png", "career_kills": 3100, "career_deaths": 1600, "career_assists": 4200},
]

MATCH_IDS = {
    "m1": "d0e1f2a3-b4c5-4d6e-7f8a-9b0c1d2e3f4a",
    "m2": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b",
    "m3": "f2a3b4c5-d6e7-4f8a-9b0c-1d2e3f4a5b6c",
}

MATCHES = [
    {"match_id": MATCH_IDS["m1"], "tournament": "Worlds 2024", "team1_id": TEAM_IDS["t1"], "team2_id": TEAM_IDS["g2"], "team1_score": 3, "team2_score": 1, "winner_id": TEAM_IDS["t1"], "match_date": "2024-11-15", "duration_minutes": 142, "vod_url": "https://youtube.com/watch?v=abc123"},
    {"match_id": MATCH_IDS["m2"], "tournament": "LCS Spring 2024", "team1_id": TEAM_IDS["c9"], "team2_id": TEAM_IDS["tl"], "team1_score": 2, "team2_score": 3, "winner_id": TEAM_IDS["tl"], "match_date": "2024-03-20", "duration_minutes": 185, "vod_url": "https://youtube.com/watch?v=def456"},
    {"match_id": MATCH_IDS["m3"], "tournament": "MSI 2024", "team1_id": TEAM_IDS["g2"], "team2_id": TEAM_IDS["c9"], "team1_score": 3, "team2_score": 0, "winner_id": TEAM_IDS["g2"], "match_date": "2024-05-10", "duration_minutes": 98, "vod_url": "https://youtube.com/watch?v=ghi789"},
]

LEADERBOARD = [
    {"rank": 1, "team_id": TEAM_IDS["t1"], "team_name": "T1", "points": 2850, "matches_played": 45, "win_streak": 8},
    {"rank": 2, "team_id": TEAM_IDS["g2"], "team_name": "G2 Esports", "points": 2680, "matches_played": 42, "win_streak": 5},
    {"rank": 3, "team_id": TEAM_IDS["tl"], "team_name": "Team Liquid", "points": 2420, "matches_played": 40, "win_streak": 3},
    {"rank": 4, "team_id": TEAM_IDS["c9"], "team_name": "Cloud9", "points": 2180, "matches_played": 38, "win_streak": 0},
]

# In-memory predictions storage
predictions_db: List[Dict] = []

# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/health")
def health():
    return {"status": "ok", "service": "dummy-esports"}

@app.get("/teams")
def get_teams():
    return TEAMS[0]  # Return single team (snapshot pattern)

@app.get("/players")
def get_players():
    return PLAYERS[0]  # Return single player (snapshot pattern)

@app.get("/matches")
def get_matches():
    return MATCHES[0]  # Return single match (snapshot pattern)

@app.get("/leaderboard")
def get_leaderboard():
    # Return full leaderboard as a snapshot with array field (for Table component)
    return {"rankings": LEADERBOARD}

@app.get("/predictions")
def get_predictions():
    if predictions_db:
        return predictions_db[-1]  # Return latest prediction
    return {
        "prediction_id": "none",
        "match_id": "",
        "predicted_winner": "",
        "predicted_score": "",
        "confidence": 0,
        "placed_at": "",
        "result": "pending",
        "points_earned": 0
    }

@app.post("/predictions")
def create_prediction(prediction: dict):
    new_prediction = {
        "prediction_id": str(uuid.uuid4()),
        "match_id": prediction.get("match_id", ""),
        "predicted_winner": prediction.get("predicted_winner", ""),
        "predicted_score": prediction.get("predicted_score", ""),
        "confidence": prediction.get("confidence", 50),
        "placed_at": datetime.now().isoformat(),
        "result": "pending",
        "points_earned": 0
    }
    predictions_db.append(new_prediction)
    print(f"[PREDICTION] New prediction created: {new_prediction}")
    return new_prediction

# =============================================================================
# WebSocket - Live Match Events
# =============================================================================

match_event_clients: Set[WebSocket] = set()

EVENT_TYPES = ["kill", "assist", "death", "tower", "dragon", "baron", "headshot"]
# Map player names to their UUIDs
PLAYER_NAME_TO_ID = {
    "Faker": PLAYER_IDS["faker"],
    "Caps": PLAYER_IDS["caps"],
    "CoreJJ": PLAYER_IDS["corejj"],
    "Blaber": PLAYER_IDS["blaber"],
    "Jankos": PLAYER_IDS["jankos"],
}
PLAYER_NAMES = list(PLAYER_NAME_TO_ID.keys())

# Fixed UUID for live match
LIVE_MATCH_ID = "a0b1c2d3-e4f5-4a6b-7c8d-9e0f1a2b3c4d"

@app.websocket("/ws/match-events")
async def match_events_ws(websocket: WebSocket):
    await websocket.accept()
    match_event_clients.add(websocket)
    print(f"[WS] Match events client connected. Total: {len(match_event_clients)}")

    try:
        # Send simulated match events
        game_time = 0
        while True:
            await asyncio.sleep(random.uniform(1.5, 4.0))
            game_time += random.randint(5, 15)

            event_type = random.choice(EVENT_TYPES)
            player = random.choice(PLAYER_NAMES)
            target = random.choice([p for p in PLAYER_NAMES if p != player]) if event_type in ["kill", "headshot"] else None

            event = {
                "match_id": LIVE_MATCH_ID,
                "event_type": event_type,
                "timestamp": game_time,
                "player_id": PLAYER_NAME_TO_ID[player],
                "player_name": player,
                "team_id": TEAM_IDS["t1"] if random.random() > 0.5 else TEAM_IDS["g2"],
                "target_id": PLAYER_NAME_TO_ID[target] if target else "",
                "target_name": target if target else "",
                "details": {"weapon": "ability" if event_type == "kill" else None}
            }

            await websocket.send_json(event)
            print(f"[WS] Sent match event: {event_type} by {player}")

    except WebSocketDisconnect:
        match_event_clients.discard(websocket)
        print(f"[WS] Match events client disconnected. Total: {len(match_event_clients)}")

# =============================================================================
# WebSocket - Live Score Updates
# =============================================================================

score_clients: Set[WebSocket] = set()

@app.websocket("/ws/scores")
async def scores_ws(websocket: WebSocket):
    await websocket.accept()
    score_clients.add(websocket)
    print(f"[WS] Score client connected. Total: {len(score_clients)}")

    try:
        team1_score = 0
        team2_score = 0
        game_time = 0

        while True:
            await asyncio.sleep(random.uniform(2.0, 5.0))
            game_time += random.randint(10, 30)

            # Randomly increment scores
            if random.random() > 0.6:
                if random.random() > 0.5:
                    team1_score += 1
                else:
                    team2_score += 1

            status = "in_progress"
            if game_time > 1800:  # 30 minutes
                status = "late_game"
            if team1_score >= 15 or team2_score >= 15:
                status = "finished"

            score_update = {
                "match_id": LIVE_MATCH_ID,
                "team1_score": team1_score,
                "team2_score": team2_score,
                "game_time": game_time,
                "status": status
            }

            await websocket.send_json(score_update)
            print(f"[WS] Sent score update: {team1_score} - {team2_score} @ {game_time}s")

            if status == "finished":
                break

    except WebSocketDisconnect:
        score_clients.discard(websocket)
        print(f"[WS] Score client disconnected. Total: {len(score_clients)}")

# =============================================================================
# WebSocket - Predictions (Outbound from client)
# =============================================================================

prediction_clients: Set[WebSocket] = set()

@app.websocket("/ws/predictions")
async def predictions_ws(websocket: WebSocket):
    await websocket.accept()
    prediction_clients.add(websocket)
    print(f"[WS] Prediction client connected. Total: {len(prediction_clients)}")

    try:
        while True:
            # Receive predictions from client
            data = await websocket.receive_json()
            print(f"[WS] Received prediction: {data}")

            # Process the prediction
            prediction = {
                "prediction_id": str(uuid.uuid4()),
                "match_id": data.get("match_id", ""),
                "predicted_winner": data.get("predicted_winner", ""),
                "predicted_score": data.get("predicted_score", ""),
                "confidence": data.get("confidence", 50),
                "placed_at": datetime.now().isoformat(),
                "result": "pending",
                "points_earned": 0
            }
            predictions_db.append(prediction)

            # Send confirmation back
            await websocket.send_json({
                "status": "accepted",
                "prediction_id": prediction["prediction_id"],
                "message": "Prediction received successfully"
            })

    except WebSocketDisconnect:
        prediction_clients.discard(websocket)
        print(f"[WS] Prediction client disconnected. Total: {len(prediction_clients)}")

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)

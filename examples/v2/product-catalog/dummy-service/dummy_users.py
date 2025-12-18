"""
Dummy User Service - Mock user database
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
from datetime import datetime

app = FastAPI(title="Dummy User Service")

# In-memory database
users_db = {
    "user-1": {
        "id": "user-1",
        "email": "alice@example.com",
        "name": "Alice Johnson",
        "memberSince": "2023-01-15T00:00:00Z"
    },
    "user-2": {
        "id": "user-2",
        "email": "bob@example.com",
        "name": "Bob Smith",
        "memberSince": "2023-06-20T00:00:00Z"
    },
    "user-3": {
        "id": "user-3",
        "email": "carol@example.com",
        "name": "Carol White",
        "memberSince": "2024-02-10T00:00:00Z"
    }
}

class User(BaseModel):
    id: str
    email: str
    name: str
    memberSince: str

@app.get("/")
def root():
    return {"service": "Dummy User Service", "status": "running"}

@app.get("/users/", response_model=List[User])
def list_users():
    print(f"[{datetime.now()}] LIST users - returning {len(users_db)} items")
    return list(users_db.values())

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    print(f"[{datetime.now()}] GET user: {user_id}")
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DUMMY USER SERVICE (Read-Only)")
    print("="*60)
    print(f"  Running on: http://localhost:9002")
    print(f"  Users: {len(users_db)}")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=9002, log_level="info")

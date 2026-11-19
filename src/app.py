"""
High School Management System API

A super simple FastAPI application that allows students to view activities and
teachers to manage signups for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing activities and managing student signups")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_COOKIE_NAME = "teacher_session"
SESSION_DURATION_SECONDS = 8 * 60 * 60


class TeacherLogin(BaseModel):
    username: str
    password: str


def _get_teacher_config() -> tuple[str, str, bytes]:
    username = os.environ.get("TEACHER_USERNAME")
    password = os.environ.get("TEACHER_PASSWORD")
    secret = os.environ.get("SESSION_SECRET")

    if not username or not password or not secret or len(secret.encode()) < 32:
        raise HTTPException(
            status_code=503,
            detail=(
                "Teacher login is not configured. Set TEACHER_USERNAME, "
                "TEACHER_PASSWORD, and a SESSION_SECRET of at least 32 bytes."
            ),
        )

    return username, password, secret.encode()


def _create_session_token(username: str, secret: bytes) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + SESSION_DURATION_SECONDS},
        separators=(",", ":"),
    ).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(secret, encoded_payload.encode(), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def _is_teacher_authenticated(token: str | None) -> bool:
    if not token:
        return False

    username, _, secret = _get_teacher_config()
    try:
        encoded_payload, signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            secret, encoded_payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
        return (
            hmac.compare_digest(payload["username"].encode(), username.encode())
            and isinstance(payload["expires"], int)
            and payload["expires"] > time.time()
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _require_teacher(request: Request) -> None:
    if not _is_teacher_authenticated(request.cookies.get(SESSION_COOKIE_NAME)):
        raise HTTPException(status_code=401, detail="Teacher login required")


def _secure_cookie_enabled() -> bool:
    return os.environ.get("SESSION_COOKIE_SECURE", "true").lower() != "false"


@app.post("/auth/login")
def login(credentials: TeacherLogin, response: Response):
    username, password, secret = _get_teacher_config()
    if not (
        hmac.compare_digest(credentials.username.encode(), username.encode())
        and hmac.compare_digest(credentials.password.encode(), password.encode())
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_create_session_token(username, secret),
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        secure=_secure_cookie_enabled(),
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@app.get("/auth/session")
def get_session(request: Request):
    authenticated = _is_teacher_authenticated(
        request.cookies.get(SESSION_COOKIE_NAME)
    )
    return {"authenticated": authenticated}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_secure_cookie_enabled(),
        samesite="lax",
        path="/",
    )
    return {"authenticated": False}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Allow a student to sign up for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(_require_teacher)],
)
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}

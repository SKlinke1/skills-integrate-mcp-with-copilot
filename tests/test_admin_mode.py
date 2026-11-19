import asyncio
import json
import os
import unittest
from copy import deepcopy
from http.cookies import SimpleCookie
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from src.app import SESSION_COOKIE_NAME, activities, app


class ASGITestClient:
    def __init__(self):
        self.cookies = {}

    def request(self, method, path, json_body=None):
        parsed_path = urlsplit(path)
        body = json.dumps(json_body).encode() if json_body is not None else b""
        headers = [(b"host", b"testserver")]
        if json_body is not None:
            headers.append((b"content-type", b"application/json"))
        if self.cookies:
            cookie_header = "; ".join(
                f"{name}={value}" for name, value in self.cookies.items()
            )
            headers.append((b"cookie", cookie_header.encode()))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": unquote(parsed_path.path),
            "raw_path": parsed_path.path.encode(),
            "query_string": parsed_path.query.encode(),
            "root_path": "",
            "headers": headers,
            "server": ("testserver", 80),
            "client": ("testclient", 12345),
        }
        messages = []
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        asyncio.run(app(scope, receive, send))
        response_headers = dict(messages[0]["headers"])
        set_cookie = response_headers.get(b"set-cookie")
        if set_cookie:
            cookie = SimpleCookie()
            cookie.load(set_cookie.decode())
            morsel = cookie[SESSION_COOKIE_NAME]
            if morsel["max-age"] == "0":
                self.cookies.pop(SESSION_COOKIE_NAME, None)
            else:
                self.cookies[SESSION_COOKIE_NAME] = morsel.value

        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return messages[0]["status"], response_headers, response_body


class AdminModeTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            "os.environ",
            {
                "TEACHER_USERNAME": "teacher",
                "TEACHER_PASSWORD": "correct-password",
                "SESSION_SECRET": "test-secret-with-at-least-32-bytes",
                "SESSION_COOKIE_SECURE": "false",
            },
        )
        self.environment.start()
        self.client = ASGITestClient()
        self.original_participants = {
            name: deepcopy(activity["participants"])
            for name, activity in activities.items()
        }

    def tearDown(self):
        for name, participants in self.original_participants.items():
            activities[name]["participants"] = participants
        self.environment.stop()

    def test_students_can_view_activities_and_participants(self):
        status, _, body = self.client.request("GET", "/activities")
        self.assertEqual(status, 200)
        self.assertIn(b"michael@mergington.edu", body)

        status, _, body = self.client.request("GET", "/auth/session")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["authenticated"])

    def test_signup_is_public_but_unregister_requires_teacher_login(self):
        status, _, _ = self.client.request(
            "POST",
            "/activities/Chess%20Club/signup?email=new.student%40mergington.edu",
        )
        self.assertEqual(status, 200)

        status, _, _ = self.client.request(
            "DELETE",
            "/activities/Chess%20Club/unregister?email=new.student%40mergington.edu",
        )
        self.assertEqual(status, 401)
        self.assertIn(
            "new.student@mergington.edu",
            activities["Chess Club"]["participants"],
        )

    def test_teacher_can_register_unregister_and_log_out(self):
        status, _, _ = self.client.request(
            "POST",
            "/auth/login",
            {"username": "teacher", "password": "wrong-password"},
        )
        self.assertEqual(status, 401)

        status, headers, _ = self.client.request(
            "POST",
            "/auth/login",
            {"username": "teacher", "password": "correct-password"},
        )
        self.assertEqual(status, 200)
        set_cookie = headers[b"set-cookie"].decode().lower()
        self.assertIn("httponly", set_cookie)
        self.assertIn("samesite=lax", set_cookie)

        status, _, body = self.client.request("GET", "/auth/session")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["authenticated"])

        status, _, _ = self.client.request(
            "POST",
            "/activities/Chess%20Club/signup?email=new.student%40mergington.edu",
        )
        self.assertEqual(status, 200)
        self.assertIn(
            "new.student@mergington.edu",
            activities["Chess Club"]["participants"],
        )

        status, _, _ = self.client.request(
            "DELETE",
            "/activities/Chess%20Club/unregister?email=michael%40mergington.edu",
        )
        self.assertEqual(status, 200)
        self.assertNotIn(
            "michael@mergington.edu",
            activities["Chess Club"]["participants"],
        )

        status, _, _ = self.client.request("POST", "/auth/logout")
        self.assertEqual(status, 200)
        status, _, body = self.client.request("GET", "/auth/session")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["authenticated"])

    def test_login_fails_when_teacher_configuration_is_missing(self):
        os.environ.pop("TEACHER_PASSWORD")
        status, _, _ = self.client.request(
            "POST",
            "/auth/login",
            {"username": "teacher", "password": "correct-password"},
        )
        self.assertEqual(status, 503)


if __name__ == "__main__":
    unittest.main()

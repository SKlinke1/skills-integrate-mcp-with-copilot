# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Students can sign up for activities and view registered participants without logging in
- Teachers can unregister students after logging in

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - Activities website: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Teacher Login Configuration

Set these environment variables outside the repository before starting the app:

- `TEACHER_USERNAME` and `TEACHER_PASSWORD`: the assigned teacher credentials
- `SESSION_SECRET`: a randomly generated secret of at least 32 bytes
- `SESSION_COOKIE_SECURE`: defaults to `true`; set to `false` only for local HTTP development

For example, generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Do not store teacher passwords or session secrets in tracked files. In production, serve
the app over HTTPS and keep `SESSION_COOKIE_SECURE` enabled.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Log in as a teacher and create a session                            |
| GET    | `/auth/session`                                                    | Check whether the current session is authenticated                  |
| POST   | `/auth/logout`                                                     | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (no login required)                              |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required)                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.

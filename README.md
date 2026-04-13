# KanMind Backend

KanMind Backend is the server-side application for a Kanban-style task management app.
Users can register, create boards, manage tasks across different stages, and collaborate through comments.
The API supports role-based access control with board owners, members, and task creators.

## Technologies

- Python
- Django
- Django REST Framework
- SQLite

## Features

- User registration and login with token authentication
- Guest login for demo access
- Board creation and management with owner and member roles
- Task creation, editing, and deletion within boards
- Task assignment and review workflow
- Commenting on tasks
- Permission-based access control

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Create and activate a virtual environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start the development server

```bash
python manage.py runserver
```

## Database

The project uses SQLite (`db.sqlite3`), which is automatically created when running migrations for the first time.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/registration/` | Register a new user |
| POST | `/api/login/` | Login and receive token |

### Boards

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/boards/` | List user's boards |
| POST | `/api/boards/` | Create a new board |
| GET | `/api/boards/<id>/` | Board detail with tasks and members |
| PATCH | `/api/boards/<id>/` | Update board |
| DELETE | `/api/boards/<id>/` | Delete board (owner only) |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks/` | Create a task |
| PATCH | `/api/tasks/<id>/` | Update a task |
| DELETE | `/api/tasks/<id>/` | Delete a task |
| GET | `/api/tasks/assigned-to-me/` | Tasks assigned to current user |
| GET | `/api/tasks/reviewing/` | Tasks to review |

### Comments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/<id>/comments/` | List comments |
| POST | `/api/tasks/<id>/comments/` | Create comment |
| DELETE | `/api/tasks/<id>/comments/<id>/` | Delete comment |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/email-check/?email=<email>` | Look up user by email |

## Authentication

Protected endpoints require a token header:

```
Authorization: Token <your_token>
```

## Notes

- `db.sqlite3` is not included in version control.
- Frontend and backend are separate repositories.
- CORS configuration is required for cross-domain deployment.
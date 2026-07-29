# ReFrame

ReFrame is an AI-powered interior design and home planning platform built with:

- `React + Vite` for the product UI
- `Tailwind CSS` for styling
- `FastAPI` for backend APIs
- `MongoDB` for data persistence

## Project structure

- `frontend/` contains the React application with public pages and authenticated app pages
- `backend/` contains the FastAPI application, route modules, schemas, and MongoDB setup

## Frontend routes

Public:

- `/`
- `/login`
- `/signup`

Authenticated:

- `/app/dashboard`
- `/app/design-studio`
- `/app/design-studio/:roomId/chat`
- `/app/design-studio/:roomId/plan`
- `/app/design-studio/:roomId/result/:designId`
- `/app/my-home`
- `/app/inspiration`
- `/app/design-score`
- `/app/contractor-briefs`
- `/app/professionals`
- `/app/profile`
- `/app/settings`

## Backend endpoints

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard/summary`
- `GET /api/profile`
- `PUT /api/profile`
- `GET /api/homes/me`
- `PUT /api/homes/me`
- `POST /api/rooms`
- `GET /api/rooms`
- `GET /api/rooms/{room_id}`
- `POST /api/rooms/{room_id}/upload`
- `POST /api/rooms/{room_id}/chat`
- `GET /api/rooms/{room_id}/requirements`
- `PUT /api/rooms/{room_id}/requirements`
- `POST /api/rooms/{room_id}/space-check`
- `POST /api/rooms/{room_id}/generate`
- `GET /api/rooms/{room_id}/designs`
- `POST /api/rooms/{room_id}/designs/{design_id}/revise`
- `GET /api/scores/{design_id}`
- `POST /api/briefs/{design_id}/generate`
- `GET /api/briefs`
- `POST /api/briefs/{brief_id}/share`
- `GET /api/inspirations`
- `POST /api/inspirations`
- `GET /api/professionals`

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Run backend

```bash
cd backend
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Make sure MongoDB is running locally at `mongodb://localhost:27017`, or update `backend/.env` with your own connection string before starting the API.

## Strongest AI setup (recommended)

ReFrame uses the strongest available model stack automatically:

1. **Claude** (`ANTHROPIC_API_KEY`) for design chat + accurate Keep/Remove/Add briefs
2. **OpenAI Images** (`OPENAI_API_KEY`) for photoreal room redesigns
3. **Pollinations** free image fallback if OpenAI image is unavailable
4. **Local trained rules** if no API keys are set

Add keys in `backend/.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

Then restart the backend. Without keys, chat and generation still work using the local trained design engine.

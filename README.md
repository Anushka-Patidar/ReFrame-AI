# ReFrame-AI

ReFrame is an AI-powered interior design and home planning platform built with:

- `React + Vite` for the product UI
- `Tailwind CSS` for styling
- `FastAPI` for backend APIs
- `MongoDB` for data persistence

Local room redesign uses `IMAGE_PROVIDER=local` (Diffusers img2img). No paid image API is required.

## Project structure

- `frontend/` — React application (public + authenticated app pages)
- `backend/` — FastAPI application, routes, schemas, and MongoDB setup
- `docs/` — implementation notes

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

## AI architecture

See `docs/ai-architecture.md` for the modular interior-design pipeline
(RoomUnderstanding → DesignBrief → Constraints → ImageEditing → Validation → Memory).

Future optional LoRA fine-tuning notes: `docs/future-lora-finetuning.md`.

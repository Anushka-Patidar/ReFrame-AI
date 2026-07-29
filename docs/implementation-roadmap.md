# ReFrame Implementation Roadmap

## Phase 1: Foundation

Implemented:

- React + Vite frontend scaffold
- Tailwind CSS setup
- Public layout and authenticated app shell
- FastAPI backend scaffold
- MongoDB connection module
- Shared route registration

## Phase 2: Authentication and profile

Implemented:

- Landing page
- Login page
- Sign up page
- Profile page
- Auth endpoints for signup, login, and current user

Next:

- Replace demo responses with JWT-backed auth and MongoDB persistence

## Phase 3: Dashboard and room setup

Implemented:

- Dashboard UI
- Room upload and dimension entry page
- Dashboard summary endpoint
- Room creation and room detail endpoints

Next:

- Persist room uploads and room status changes in MongoDB

## Phase 4: AI Design Studio core

Implemented:

- AI chat page
- Requirements card page
- Space check presentation
- Endpoints for chat, requirements, and space check

Next:

- Connect LLM orchestration and extract structured requirements from real chats

## Phase 5: Generation and versioning

Implemented:

- Generated result page
- Version history UI
- Endpoints for generation, design listing, and revision

Next:

- Integrate an image-generation provider and image storage

## Phase 6: Supporting systems

Implemented:

- My Home page
- Inspiration page
- Design Score page
- Contractor Briefs page
- Professionals page
- Supporting API endpoints

Next:

- Add MongoDB-backed persistence, sharing actions, and seed management

## Phase 7: Polish

Implemented:

- Shared visual language across public and app flows
- Responsive card-based layouts

Next:

- Add stronger loading states, form validation, empty states, and API integration

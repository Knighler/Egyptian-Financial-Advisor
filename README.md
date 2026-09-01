# Egyptian Financial Advisor

Egyptian Financial Advisor (EFA) is an AI-powered financial guidance app focused on the Egyptian market.  
It combines a Next.js frontend, a FastAPI backend, Firebase user data, and BigQuery market datasets.

## Repository Structure

- `frontend/` – Next.js app (login, onboarding, chat/dashboard UI)
- `backend/` – FastAPI API, agent orchestration, Firebase/BigQuery integration
- `dbt/` – dbt project for analytics models and marts
- `Review EFA_PRD.md` – product and architecture reference

## Tech Stack

- Frontend: Next.js + React + Tailwind CSS
- Backend: FastAPI + Python
- AI/Orchestration: LangChain + Google Gemini
- User/Auth Data: Firebase Authentication + Firestore
- Analytics Data: Google BigQuery

## Prerequisites

- Node.js 20+
- npm
- Python 3.11+
- Access to Firebase, BigQuery, and Google GenAI credentials

## Local Setup

### 1) Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
```

Fill `frontend/.env.local` values for Firebase and API URL.

### 2) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `backend/.env` values for Firebase, BigQuery, and Google GenAI.

## Run the Application

### Start backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start frontend

```bash
cd frontend
npm run dev
```

Frontend: `http://localhost:3000`  
Backend health check: `http://localhost:8000/health`

## Available Frontend Routes

- `/login`
- `/onboarding`
- `/dashboard`
- `/chat`


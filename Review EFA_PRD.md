1. Project Overview
The Egyptian Financial Advisor (EFA) is an Agentic RAG application. It acts as a personalized, conversational financial advisor tailored to the Egyptian macro-economic environment. The system uses a Large Language Model (LLM) equipped with a "Tool Registry" to securely query pre-aggregated BigQuery financial data based on a user's unique financial profile.

2. Tech Stack Definition
Frontend UI: Next.js (React) with Tailwind CSS. (Agent Note: Prioritize clean, modern UI components like shadcn/ui if needed).

Backend API: FastAPI (Python).

AI Orchestration: LangChain to manage the ReAct Agent, Tool binding, and prompt construction.

Authentication & User State: Firebase Authentication and Firebase Firestore (NoSQL).

Analytical Database: Google BigQuery (Data is already modeled and updated via dbt/Kestra).

LLM Provider: Google Gemini Pro.

3. Existing Infrastructure (DO NOT ALTER)
The analytical data pipeline is already built and managed via dbt. The Backend should ONLY perform SELECT queries on the following existing BigQuery Marts in the de-practice-490214.efa_main dataset:

fct_daily_asset_performance: Daily stock prices merged with USD/EGP rates and Gold 24k prices.

dim_ticker_performance: Current-day snapshot containing 7-day and 30-day percentage returns and volatility metrics.

fct_historical_stats: 5-year context (All-time highs, lows, historical volatility).

4. Application Architecture & Data Flow
User Onboarding: User signs up via Firebase Auth and fills out a Profile Form (Income, Savings, Goal, Risk Tolerance). This is saved to Firestore.

Context Injection: When the user sends a message in the chat, the Next.js frontend sends the message and the Firebase uid to the FastAPI backend.

Prompt Assembly: FastAPI fetches the User Profile from Firestore and prepends it to the LLM's System Prompt (e.g., "You are advising a user with low risk tolerance saving for a car...").

Agentic Tool Use: The LLM evaluates the prompt, calls BigQuery tools to fetch relevant data from the Marts, synthesizes an answer, and streams it back to the UI.

5. Core Screens / Routes
/login: Firebase email/password or Google OAuth.

/onboarding: A form to capture financial profile (Budget, Primary Goal, Risk Tolerance [1-10 slider]).

/dashboard (or /chat): The main conversational UI. Must include a sidebar summarizing the user's current profile, and a main chat window.

6. Phased Execution Plan for AI Agent
Agent Directive: Do not execute all phases at once. Await user approval before moving to the next phase.

Phase 1: Project Scaffolding & Auth

Initialize Next.js frontend and FastAPI backend folders.

Set up Firebase configuration in both environments using .env files.

Build the /login page with basic Firebase Authentication.

Phase 2: The User Profile (Firestore)

Build the /onboarding page in Next.js.

Create the FastAPI endpoint to accept and validate profile data.

Save the user's profile to a users collection in Firestore.

Phase 3: Backend Agent & BigQuery Tools

Set up the google-cloud-bigquery client in FastAPI using local credentials.

Initialize the Gemini LLM.

Create 3 Python functions (Tools) that query the 3 BigQuery Marts.

Bind these tools to the LLM to create the Agentic RAG loop.

Phase 4: The Chat Interface & Integration

Build the main /chat interface in Next.js.

Connect the frontend chat input to the backend Agent endpoint.

Ensure the backend successfully retrieves the Firestore profile, injects the system prompt, runs the Agent loop, and returns the response.

7. Strict AI Coding Rules
Environment Variables: Never hardcode API keys, GCP project IDs, or Firebase configs. Always read from .env or .env.local.

BigQuery Read-Only: The backend must never execute INSERT, UPDATE, or DROP commands against BigQuery.

Graceful Failures: If BigQuery is unreachable or the LLM timeouts, return a user-friendly error to the frontend, not a raw stack trace.

Logs: Implement standard Python logging in FastAPI so the user can see the exact SQL queries the Agent is generating during the ReAct loop.
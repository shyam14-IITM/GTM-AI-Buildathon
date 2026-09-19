# GTM AI Buildathon: Autonomous SDR Backend

This repository contains the backend architecture for an Autonomous Sales Development Representative (SDR) platform. It is designed to integrate with a low-code frontend (DronaHQ) to automate prospect research, ICP fitment evaluation, and outreach generation.

## 🏗️ Architecture

The system is built on a highly concurrent, async-first Python stack:

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance, non-blocking REST endpoints.
- **AI Orchestration**: [LangGraph](https://python.langchain.com/docs/langgraph) & LangChain for stateful agent workflows.
- **LLM Engine**: Google Gemini 1.5 Flash (`ChatGoogleGenerativeAI`) utilizing strict Pydantic structured outputs to prevent hallucinated data.
- **Database**: PostgreSQL (via Supabase) with `pgvector`.
- **ORM**: SQLAlchemy (`AsyncSession`) for asynchronous database operations.
- **Authentication**: Custom JWT + bcrypt implementation ensuring strict multi-tenant isolation (Campaigns are locked to the authenticated human `User`).

### Core AI Pipeline (`backend/graph`)
The LangGraph workflow orchestrates multiple agents:
1. **Research Node**: Extracts prospect identifiers and structures realistic firmographic data (Name, Title, Company Size, Industry).
2. **ICP Fitment Node**: Evaluates the prospect's data against the Campaign's dynamic `icp_criteria` (JSONB) to output a strict `Qualified` or `Rejected` decision.

### Async Execution (`backend/routers/campaigns.py`)
To prevent frontend timeouts in DronaHQ, the LangGraph pipeline is triggered via a `POST /api/campaigns/{id}/execute` endpoint. This returns a `202 Accepted` response instantly, while FastAPI `BackgroundTasks` execute the LLM reasoning and persist the funnel stage changes to Postgres asynchronously.

---

## ⚙️ Environment Variables

Create a `.env` file in the `backend/` directory with the following keys:

```env
# Database (Supabase or Local Postgres)
# e.g., postgresql+asyncpg://postgres:postgres@localhost:5432/buildathon
DATABASE_URL=your_postgres_connection_string

# Authentication
SECRET_KEY=your_secure_random_jwt_string

# AI / LLM Provider
GOOGLE_API_KEY=your_gemini_api_key
```

---

## 🚀 Setup & Installation

**1. Create a Python Virtual Environment**
Ensure you are using Python 3.12+ (which provides native binary wheels to avoid Rust compilation issues).
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
```

**2. Install Dependencies**
```bash
pip install -r requirements.txt
```

**3. Database Initialization & Seeding**
We have included automated scripts to scaffold the schema and populate mock data.
```bash
# Drops all existing tables and rebuilds the clean schema
python reset_db.py

# Seeds an Admin user, mock Campaigns, and Prospects
python seed.py
```

**4. Run the Server**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. 
Interactive documentation (Swagger UI) is available at `http://localhost:8000/docs`.

---

## 🧪 Testing the Pipeline

1. Go to `http://localhost:8000/docs`.
2. Click **Authorize** and log in with the seeded credentials (`admin@company.com` / `password123`).
3. Use `GET /api/campaigns/` to fetch your mock Campaign IDs.
4. Hit `POST /api/campaigns/{campaign_id}/execute`.
5. Hit `GET /api/prospects/{campaign_id}/funnel` to watch the funnel metrics instantly update as the AI evaluates prospects!

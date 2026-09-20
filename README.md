# GTM AI Buildathon: Autonomous SDR Platform

This repository contains a full-stack application for an Autonomous Sales Development Representative (SDR) platform. It automates prospect discovery, ICP fitment evaluation, and personalized outreach generation.

## 🏗️ Architecture

The system is built as a modern, decoupled full-stack application:

### Backend (`/backend`)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance, non-blocking REST endpoints.
- **AI Orchestration**: [LangGraph](https://python.langchain.com/docs/langgraph) & LangChain for stateful agent workflows.
- **LLM Engine**: Groq for ultra-fast inference and reasoning.
- **Embeddings/RAG**: Local `HuggingFaceEmbeddings` (`all-MiniLM-L6-v2`) combined with `pgvector` for instant, cost-free knowledge retrieval.
- **Lead Discovery**: Integrated with Apollo.io to autonomously discover leads based on dynamic campaign criteria.
- **Database**: PostgreSQL (via Supabase) with `pgvector`.
- **ORM**: SQLAlchemy (`AsyncSession`) for asynchronous database operations.
- **Authentication**: Custom JWT + bcrypt implementation ensuring strict multi-tenant isolation.

### Frontend (`/frontend`)
- **Framework**: React 19 + Vite for a blazing fast Single Page Application (SPA) experience.
- **Routing**: React Router DOM.
- **Styling**: Tailwind CSS 4 for utility-first, modern UI design.
- **Icons**: Lucide React.
- **API Client**: Axios configured with environment-based routing.

---

## ⚙️ Environment Configuration

### Backend (`backend/.env`)
Create a `.env` file in the `backend/` directory:
```env
# Database Connection (Direct Connection for asyncpg)
DATABASE_URL=postgresql+asyncpg://postgres:your_password@your_host:5432/postgres

# Security
SECRET_KEY=your_secure_random_jwt_string
DRONAHQ_API_KEY=your_secure_api_key

# Third Party APIs
GROQ_API_KEY=gsk_your_key_here
RESEND_API_KEY=re_your_key_here
GOOGLE_API_KEY=your_google_key_here

# Frontend CORS
ALLOWED_ORIGINS=http://localhost:5173,https://your-production-url.com
```

### Frontend (`frontend/.env`)
Create a `.env` file in the `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🚀 Setup & Installation

### 1. Backend Setup
**Create a Python Virtual Environment (Python 3.10+)**
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
```

**Install Dependencies**
```bash
pip install -r requirements.txt
```

**Database Initialization & Seeding**
Make sure your `DATABASE_URL` is configured in the `.env` file, then run:
```bash
# Drops all existing tables and rebuilds the clean schema
python init_db.py

# Seeds an Admin user (admin@company.com / password123)
python seed_no_campaigns.py 
# Note: You can optionally use `python seed.py` instead if you want dummy campaigns/prospects too.
```

**Run the Server**
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup
Open a new terminal window.
```bash
cd frontend
npm install
npm run dev
```
The frontend will be available at `http://localhost:5173`. You can log in using `admin@company.com` and `password123`.

---

## 🧪 Testing the Pipeline
1. Log in to the frontend dashboard.
2. Create a new Campaign and define your target roles (e.g. "CTO", "VP Engineering").
3. Click **Discover Leads** to pull real prospects from Apollo into your campaign funnel.
4. Click **Execute AI Agents** to trigger the LangGraph workflow in the background, which will evaluate the new prospects against your ICP and draft emails.

# MiniProj Setup and Run Guide

This README covers the basic requirements and how to run the project locally.

## 1. Basic Requirements

Install these tools first:

- Anaconda (or Miniconda)
- Python 3.10+
- Node.js 18+ and npm
- Docker Desktop
- Ollama
- MongoDB (local service or MongoDB Atlas)

Recommended downloads:

- Anaconda: https://www.anaconda.com/download
- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Ollama: https://ollama.com/download
- Node.js: https://nodejs.org/
- MongoDB Community: https://www.mongodb.com/try/download/community

## 2. Clone and Open Project

```powershell
cd D:\
git clone <your-repo-url> miniProj
cd miniProj
```

If you already have the project folder, just open `D:\miniProj` in VS Code.

## 3. Create and Activate Virtual Environment

Option A: Conda (recommended)

From the project root:

```powershell
conda create -n miniproj python=3.10 -y
conda activate miniproj
```

Install root dependencies:

```powershell
pip install -r requirements.txt
```

## 4. Backend Environment Variables

The backend reads variables from `backend/.env`.

Minimum required values for local run:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=fastapi_db
SECRET_KEY=change-this-to-a-random-secret
FRONTEND_URL=http://localhost:3000
```

Optional for Google OAuth:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Note: keep secrets private and do not commit real credentials.

## 5. Start Docker

Make sure Docker Desktop is running before starting Qdrant.

Quick check:

```powershell
docker --version
```

## 6. Start and Stop Qdrant (Using Provided Script)

Use the script inside the `vector db` folder.

Start Qdrant:

```powershell
cd "D:\miniProj\vector db"
python qdrant_setup.py start
```

Stop Qdrant:

```powershell
cd "D:\miniProj\vector db"
python qdrant_setup.py stop
```

Notes:

- This script starts a Docker container named `qdrant_local`.
- Qdrant API runs on `http://localhost:6333`.
- Data persists in `vector db/qdrant_storage`.

## 7. Ollama Setup

Install and start Ollama, then pull at least one model:

```powershell
ollama --version
ollama pull llama3.2
```

Run a quick test:

```powershell
ollama run llama3.2 "hello"
```

Default Ollama endpoint is `http://localhost:11434`.

## 8. Run the Backend

Open a terminal at project root and activate conda env if needed:

```powershell
conda activate miniproj
cd D:\miniProj\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend URLs:

- API root: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`

## 9. Run the Frontend

Copy the example env and install dependencies:

```powershell
cd D:\miniProj\frontend
cp .env.example .env
npm install
npm run dev
```

Frontend URL:

- `http://localhost:5173` (Vite default) or the port shown in the terminal.

**Frontend environment:** Create `frontend/.env` (see `frontend/.env.example`). Set `VITE_API_URL=http://localhost:8000` so the app talks to the backend. If unset, it defaults to `http://localhost:8000`.

## 10. Suggested Startup Order

1. Start MongoDB.
2. Start Docker Desktop.
3. Start Qdrant with `python qdrant_setup.py start` from `vector db`.
4. Start backend (`uvicorn`).
5. Start frontend (`npm run dev`).
6. Start/use Ollama model if your flow needs LLM calls.

## 11. Stop Everything

1. Stop frontend: `Ctrl+C` in frontend terminal.
2. Stop backend: `Ctrl+C` in backend terminal.
3. Stop Qdrant:

```powershell
cd "D:\miniProj\vector db"
python qdrant_setup.py stop
```

4. Stop MongoDB (if running locally).
5. Docker Desktop can be closed if not needed.

## 12. Frontend Notes (Inventory)

- **Add/Edit item form:** The inventory UI only uses **name**, **quantity**, and **unit**. Category and notes fields are not shown or used in the form.
- **Category filters:** The inventory list does not include category filters; all items are listed.

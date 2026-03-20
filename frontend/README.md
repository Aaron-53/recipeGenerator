# Recipe Generator Frontend

React + Vite + Tailwind. Auth (email/username + password and Google OAuth) and inventory are wired to the backend.

## Setup

```bash
cp .env.example .env
npm install
```

Edit `frontend/.env` and set:

- `VITE_API_URL` – backend API base URL (e.g. `http://localhost:8000`). Required for API calls; defaults to `http://localhost:8000` if unset.

## Run

```bash
npm run dev
```

Open the URL shown (e.g. `http://localhost:5173`).

## Routes

- `/` – Landing
- `/signin` – Sign in (email/username + password or Google)
- `/signup` – Sign up (same options)
- `/auth/callback` – Google OAuth callback (do not open manually)
- `/inventory` – Inventory (protected; requires login)

After login or signup you are redirected to `/inventory`.

## Inventory UI

- **Add/Edit item:** The form only has **name**, **quantity**, and **unit**. Category and notes are not used in the UI.
- **Category filters:** The inventory list does not have category filters; all items are shown.

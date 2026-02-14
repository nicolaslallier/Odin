# Odin

Next.js + Convex fullstack app.

## Prerequisites

- Node.js 18+
- npm

## Quick start

### 1. Install dependencies

```bash
cd web && npm install
```

### 2. Configure Convex (one-time setup)

Run Convex dev to log in, create a project, and generate `.env.local`:

```bash
cd web && npx convex dev
```

This will:

- Open a browser to authenticate (GitHub, etc.)
- Create a Convex project
- Write `CONVEX_DEPLOYMENT` and `NEXT_PUBLIC_CONVEX_URL` to `web/.env.local`

**Important:** `.env.local` is git-ignored. Do not commit Convex credentials.

### 3. Import sample data (optional)

```bash
cd web && npx convex import --table tasks sampleData.jsonl
```

### 4. Run the app

```bash
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONVEX_DEPLOYMENT` | Yes | Set by `npx convex dev` (e.g. `dev:your-project`) |
| `NEXT_PUBLIC_CONVEX_URL` | Yes | Convex deployment URL (e.g. `https://xxx.convex.cloud`) |

Copy `web/.env.local.example` to `web/.env.local` and fill in values after running `npx convex dev`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Next.js dev server (from `web/`) |
| `npx convex dev` | Start Convex dev (syncs functions, watches for changes) |
| `npx convex deploy` | Deploy Convex backend to production |
| `npx convex import --table tasks sampleData.jsonl` | Import sample tasks |

## CI/CD (GitHub Actions)

A workflow in `.github/workflows/deploy.yml` runs on push to `main` and on manual trigger. It:

1. Deploys the Convex backend
2. Builds the Next.js app (verifies the frontend compiles)

### Required GitHub secrets

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `CONVEX_DEPLOY_KEY` | Deploy key for your Convex production deployment. Generate in [Convex Dashboard](https://dashboard.convex.dev) → Project → Settings → Deploy Key |
| `NEXT_PUBLIC_CONVEX_URL` | Production Convex URL (e.g. `https://your-prod-deployment.convex.cloud`). Found in the Convex dashboard for your production deployment. |

### Deploying the Next.js frontend

The workflow builds the app but does not deploy it. To deploy the frontend:

- **Vercel**: Connect this repo in [Vercel](https://vercel.com). Vercel will deploy on push. Add `NEXT_PUBLIC_CONVEX_URL` in Vercel’s environment variables.
- **Other hosts**: Extend the workflow or use your platform’s deployment integration.

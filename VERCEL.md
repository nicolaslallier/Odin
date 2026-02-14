# Vercel deployment

## Fixing 404 NOT_FOUND

The Next.js app lives in the `web/` subdirectory. You **must** set the Root Directory in Vercel:

1. Vercel Dashboard → Your Project → **Settings** → **General**
2. Find **Root Directory**
3. Set it to **`web`** (or `./web`)
4. Click **Save**
5. **Redeploy** (Deployments → ⋮ on latest → Redeploy)

## Environment variables

Add `NEXT_PUBLIC_CONVEX_URL` in **Settings → Environment Variables** so the app can reach your Convex backend (use your dev deployment URL).

Makwande Auto Apply (Advanced Frontend)
======================================

1) Set API base URL (if needed):
   - Open /settings.html
   - Paste your live backend base domain (e.g. https://your-api.onrender.com)
   - Save and refresh

2) Deploy:
   - Any static host works (Cloudflare Pages, Netlify, Vercel static export, GitHub Pages).
   - Ensure routes are served as static files (no SPA needed).

Expected backend endpoints:
- POST /api/auth/signup
- POST /api/auth/login   -> returns { token, user }
- GET  /api/auth/me
- GET  /api/jobs
- POST /api/apply_job
- GET  /api/applications
- POST /api/saved_jobs
- GET  /api/saved_jobs
- POST /api/cv/revamp
- POST /api/cover_letter
- GET  /api/billing/status (optional)
- POST /api/billing/verify (optional)
- POST /api/cv/upload (optional)

If your backend uses different paths, adjust assets/js/api.js accordingly.

# Deployment Guide for Heat Health Monitoring System

## Overview
This guide explains how to deploy your Flask application on Render with PostgreSQL database.

---

## Prerequisites
- GitHub repository with the latest code pushed
- Render account (https://render.com)
- PostgreSQL database on Render

---

## Step 1: Create PostgreSQL Database on Render

1. **Go to Render Dashboard** → Click "New +"
2. **Select "PostgreSQL"**
3. **Configure Database:**
   - Name: `heat_health_db`
   - Region: `Singapore` (or your preferred region)
   - Database: `heat_health_db`
   - User: Keep the default or set custom
   - Plan: `Free` (for testing) or upgrade as needed

4. **Copy the Database URL**
   - After creation, copy the internal database URL
   - Format: `postgresql://username:password@hostname/database`
   - Save this - you'll need it for environment variables

---

## Step 2: Deploy Flask App on Render

1. **Go to Render Dashboard** → Click "New +"
2. **Select "Web Service"**
3. **Connect GitHub Repository:**
   - Select your GitHub account
   - Find `heat-health-system-v2` repository
   - Click "Connect"

4. **Configure Web Service:**
   - **Name:** `heat-health-monitoring` (or your preferred name)
   - **Environment:** `Python 3`
   - **Region:** `Singapore` (same as database for better performance)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
   - **Plan:** `Free` (for testing)

---

## Step 3: Set Environment Variables in Render

In the Render dashboard, go to your web service and set these environment variables:

```
FLASK_ENV=production
PYTHON_VERSION=3.11
SECRET_KEY=<your-secret-key>
DATABASE_URL=<paste-postgresql-url-from-step-1>
OPENWEATHER_API_KEY=<your-api-key>
SENSOR_SECRET=<your-sensor-secret>
HEALTH_WORKER_CODE=<your-code>
DEFAULT_CITY=Clarin,Bohol,PH
```

**Important:** 
- For `SECRET_KEY`: Generate using: `python -c "import secrets; print(secrets.token_hex(32))"`
- For `DATABASE_URL`: Use the PostgreSQL URL from Step 1
- All other keys: Use the same values you have locally

---

## Step 4: Deploy

1. **Manual Deploy:**
   - In Render dashboard → Select your service
   - Click "Manual Deploy" → "Deploy latest commit"
   - Wait for build to complete (3-5 minutes)

2. **Auto Deploy (Recommended):**
   - Render automatically deploys when you push to `main` branch
   - Check deployment progress in the "Events" tab

---

## Step 5: Verify Deployment

1. **Check Logs:**
   - Go to your service in Render
   - Click "Logs" tab
   - Look for:
     ```
     Database connection successful
     Database tables created successfully
     Serving Flask app
     ```

2. **Test Application:**
   - Open your service URL (e.g., `https://your-service.onrender.com`)
   - You should see the login page
   - Test login/register functionality

3. **Database Connection Issues?**
   - Check that `DATABASE_URL` is set correctly
   - Verify PostgreSQL database is running
   - Check logs for specific error messages

---

## Step 6: Database Connection Verification

If database isn't connecting after deployment:

1. **Check DATABASE_URL Format:**
   - Correct: `postgresql+psycopg2://user:password@host/database`
   - Wrong: `postgres://user:password@host/database`
   - The code auto-converts `postgres://` → `postgresql+psycopg2://`

2. **Verify in Logs:**
   ```
   ERROR in app: Database initialization failed: [error details]
   ```

3. **Common Issues:**
   - **"Access denied"** → Check credentials in DATABASE_URL
   - **"Connection refused"** → Check database is running
   - **"Unresolved host"** → Check hostname in DATABASE_URL

---

## Troubleshooting

### App Won't Start
1. Check Python version is 3.11
2. Run: `pip install -r requirements.txt`
3. Check for syntax errors: `python -m py_compile app.py`

### Database Not Connecting
1. Test DATABASE_URL locally:
   ```bash
   export DATABASE_URL="your-postgresql-url"
   python app.py
   ```
2. Check if PostgreSQL is accessible from Render
3. Verify database user has necessary permissions

### Tables Not Created
1. Check logs for "Database tables created successfully"
2. If missing, manually trigger by:
   - Stopping and restarting the service
   - Pushing a new commit to trigger rebuild

### Port Issues
- Render automatically assigns a port - you don't need to specify 5000
- The app listens on `0.0.0.0:5000` locally for development

---

## Important Files for Deployment

- `requirements.txt` - Python dependencies (includes psycopg2-binary for PostgreSQL)
- `render.yaml` - Render configuration (optional, for automatic deployment)
- `config.py` - Environment-based configuration
- `app.py` - Flask application entry point
- `wsgi.py` - WSGI entry point for Gunicorn
- `.env` - Local environment variables (NOT committed to Git)

---

## Security Checklist

- [ ] SECRET_KEY is unique and secure (use `secrets.token_hex(32)`)
- [ ] Database password is secure
- [ ] SESSION_COOKIE_SECURE = True in production
- [ ] DATABASE_URL not committed to repository
- [ ] All environment variables set in Render (not in code)
- [ ] Flask debug mode is OFF in production
- [ ] CSRF protection enabled

---

## Performance Tips

1. **Database Connection Pooling:**
   - Already configured in `config.py`
   - Pool size: 10, max_overflow: 20

2. **Static Files:**
   - Serve via CDN or Render static file serving
   - Configure in `render.yaml` if needed

3. **Background Jobs:**
   - APScheduler configured for temperature fetching
   - Runs on main process (fine for free tier)

---

## Support

If deployment still fails:
1. Check Render logs for specific error messages
2. Verify all environment variables are set
3. Ensure PostgreSQL database is accessible
4. Check GitHub repository for latest code

---

## Local Testing Before Deployment

Always test locally before deploying:

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # or on Windows: .venv\Scripts\Activate

# 2. Set environment variables
export FLASK_ENV=production
export DATABASE_URL="your-postgresql-url"

# 3. Run app
python app.py

# 4. Test functionality
# - Open http://localhost:5000
# - Test login/register
# - Check database operations
```

---

**Last Updated:** April 25, 2026
**Version:** 2.0 (PostgreSQL)

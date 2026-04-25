# Deployment Guide: Render + GitHub

This guide walks you through deploying the Heat Health Monitoring System to Render.

## Prerequisites
- GitHub account
- Render account (free tier available at https://render.com)
- Your GitHub repository pushed with all code

## Step 1: Create Render Account
1. Go to https://render.com
2. Click "Sign up"
3. Sign up with GitHub (recommended)
4. Authorize Render to access your repositories

## Step 2: Create Web Service on Render
1. From the Render dashboard, click "New +"
2. Select "Web Service"
3. Click "Connect a repository"
4. Select your GitHub repository (`heat-health-monitoring-system`)
5. Click "Connect"

## Step 3: Configure the Service
Fill in the deployment settings:

| Field | Value |
|-------|-------|
| Name | `heat-health-monitoring` |
| Environment | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn wsgi:app` |
| Plan | Free (or Starter) |
| Region | Oregon (default, choose closest to users) |

## Step 4: Set Environment Variables
Click "Environment" on the left sidebar and add these variables:

### Required secrets (add to `.env` file first, then paste here):
- `FLASK_ENV` = `production`
- `SECRET_KEY` = (copy from your `.env`)
- `DB_USER` = your database user
- `DB_PASSWORD` = your database password
- `DB_NAME` = your database name
- `DATABASE_URL` = `mysql+pymysql://user:password@hostname/dbname` (optional, uses DB_USER/PASSWORD if not set)
- `OPENWEATHER_API_KEY` = your OpenWeather API key
- `SENSOR_SECRET` = your sensor secret key
- `HEALTH_WORKER_CODE` = your health worker registration code
- `DEFAULT_CITY` = `Clarin,Bohol,PH` (or your location)

### Optional:
- `RATELIMIT_STORAGE_URI` = `memory://` (free tier, consider Redis for production)

## Step 5: Add Database Connection
**Important**: You need a MySQL database accessible from Render.

### Option A: Use a hosted MySQL service
1. Sign up at:
   - AWS RDS
   - PlanetScale (free MySQL)
   - Digital Ocean Managed Databases
   - Heroku PostgreSQL (PostgreSQL alternative)

2. Get connection details:
   - Hostname/Endpoint
   - Port (usually 3306 for MySQL)
   - Username
   - Password
   - Database name

3. Update `DATABASE_URL` in Render environment:
   ```
   mysql+pymysql://username:password@hostname:3306/dbname
   ```

### Option B: Use Render PostgreSQL (recommended for simplicity)
1. In Render dashboard, go to "PostgreSQL"
2. Click "New +"
3. Create a new database
4. Copy the connection string
5. Update `DATABASE_URL` and use PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   # Add to requirements.txt: psycopg2-binary==2.9.9
   ```

## Step 6: Deploy
1. Click "Create Web Service"
2. Render will automatically:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Run migrations (if configured)
   - Start the service with `gunicorn wsgi:app`

3. Monitor deployment in "Logs" tab
4. Once it says "Build successful", your app is live!

## Step 7: Initialize Database (First Time Only)
If your database doesn't have tables yet:

1. From Render dashboard, click your web service
2. Click "Shell" tab
3. Run these commands:
   ```bash
   flask db init
   flask db migrate -m "initial schema"
   flask db upgrade
   ```

## Step 8: Access Your App
- Your app URL will be: `https://heat-health-monitoring.onrender.com`
- Visit it to test the login page

## Automatic Deployments
- Every time you push to GitHub, Render automatically:
  1. Clones the latest code
  2. Installs dependencies
  3. Builds and deploys the app
  - No manual action needed!

## Troubleshooting

### Build fails
- Check "Logs" tab for error messages
- Verify `requirements.txt` has all dependencies
- Ensure `wsgi.py` exists and has correct imports

### App crashes after deploy
- Check "Logs" for error messages
- Verify all environment variables are set
- Check database connection string

### Database connection error
- Verify `DATABASE_URL` is correct
- Check database is accessible from Render's IP
- For MySQL: whitelist Render's IP in firewall (usually allow `0.0.0.0/0` for free tier)

### Cold starts (app takes 10+ seconds to respond)
- Normal on free tier
- Upgrade to paid plan for faster response times

## Production Best Practices for Render

1. **Use a paid instance** for production traffic
2. **Configure Redis** for rate limiting:
   ```bash
   pip install redis
   RATELIMIT_STORAGE_URI=redis://redis-url:port
   ```
3. **Set up monitoring** via Render's built-in alerts
4. **Enable auto-deployments** from GitHub (already enabled)
5. **Use PostgreSQL** instead of MySQL (better free tier support)
6. **Add a custom domain**:
   - Click "Settings"
   - Go to "Custom Domain"
   - Follow DNS setup instructions

## SSL/HTTPS
- Render provides **free automatic HTTPS** ✓
- Your app is already secure over HTTPS
- No additional configuration needed

## Need Help?
- Render Support: https://render.com/docs
- Flask Documentation: https://flask.palletsprojects.com
- Check app logs in Render dashboard

# GitHub + Render Deployment: Complete Setup Guide

## What is Render?
Render is a modern cloud platform that automatically deploys your app from GitHub. Every time you push code, it automatically rebuilds and redeploys.

## Architecture
```
Your Computer → GitHub Repository → Render → Live App
                (git push)          (auto-deploy)
```

---

## Phase 1: Prepare Your GitHub Repository

### 1.1 Ensure code is committed and pushed
```powershell
# Verify git status
git status

# Add all changes
git add .

# Commit
git commit -m "Prepare for Render deployment"

# Push to GitHub
git push origin main
```

### 1.2 Verify files in GitHub
Go to your GitHub repository and confirm these files exist:
- `wsgi.py` ✓
- `app.py` ✓
- `config.py` ✓
- `requirements.txt` ✓
- `render.yaml` ✓
- `.env.example` ✓
- `.gitignore` (includes `.env`) ✓

---

## Phase 2: Create Render Account and Connect GitHub

### 2.1 Sign up on Render
1. Go to https://render.com
2. Click "Sign up"
3. Choose "Continue with GitHub" (recommended)
4. Authorize Render to access your repositories
5. Complete account setup

### 2.2 Connect Your Repository
1. From Render dashboard, click **"New +"** button
2. Select **"Web Service"**
3. Click **"Connect repository"**
4. Find your `heat-health-monitoring-system` repository
5. Click **"Connect"**

---

## Phase 3: Configure Web Service

### 3.1 Basic Settings
Fill in these fields:

| Setting | Value |
|---------|-------|
| **Name** | `heat-health-monitoring` |
| **Environment** | `Python 3` |
| **Region** | `Oregon` (choose closest to you) |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app` |

### 3.2 Instance Type
- **Free tier**: Good for testing/development (may sleep after 15 min inactivity)
- **Starter ($7/mo)**: Better for production (always on, more memory)
- Choose based on your needs

---

## Phase 4: Set Environment Variables

**Critical**: These must be set in Render, not committed to GitHub.

### 4.1 Add Environment Variables
1. On the Render service page, click **"Environment"** on left sidebar
2. Click **"Add Environment Variable"**
3. Add these variables (copy from your local `.env` file):

```
FLASK_ENV              = production
SECRET_KEY             = <your-secret-key-from-.env>
DB_USER                = <your-db-user>
DB_PASSWORD            = <your-db-password>
DB_NAME                = <your-db-name>
DATABASE_URL           = mysql+pymysql://user:pass@host:3306/dbname
OPENWEATHER_API_KEY    = <your-api-key>
SENSOR_SECRET          = <your-sensor-secret>
HEALTH_WORKER_CODE     = <your-health-worker-code>
DEFAULT_CITY           = Clarin,Bohol,PH
RATELIMIT_STORAGE_URI  = memory://
```

**⚠️ NEVER commit `.env` to GitHub!**

---

## Phase 5: Set Up Database

### Option A: Use a Hosted MySQL Database (Recommended for remote access)
1. Sign up at one of these:
   - **PlanetScale** (free MySQL): https://planetscale.com
   - **AWS RDS**: https://aws.amazon.com/rds/
   - **DigitalOcean**: https://www.digitalocean.com
   - **Railway**: https://railway.app (simple setup)

2. Create a new MySQL database
3. Get connection details:
   - Hostname/Endpoint
   - Port (3306)
   - Username
   - Password
   - Database name

4. Set `DATABASE_URL` in Render:
   ```
   mysql+pymysql://username:password@hostname:3306/database_name
   ```

### Option B: Use AWS RDS (Most Reliable)
1. Go to AWS RDS Console
2. Create MySQL database
3. Set publicly accessible to "Yes"
4. Get endpoint and port
5. Create initial database
6. Add Render's IP to security group (or allow `0.0.0.0/0`)
7. Test connection locally before deploying

---

## Phase 6: Deploy

### 6.1 Start Deployment
1. Click **"Create Web Service"** button
2. Render will:
   - Clone your repository
   - Install dependencies
   - Build the application
   - Start the service

3. Monitor in **"Logs"** tab
4. Wait for: `Build successful` + `Server running on 0.0.0.0:10000`

### 6.2 Initialize Database (First Deploy Only)
If this is your first deploy and database is empty:

1. In Render dashboard, go to your service
2. Click **"Shell"** tab at the top
3. Run these commands:
   ```bash
   flask db init
   flask db migrate -m "initial schema"
   flask db upgrade
   ```

---

## Phase 7: Access Your Live App

### Your app is now live at:
```
https://heat-health-monitoring.onrender.com
```

Replace `heat-health-monitoring` with your actual service name if different.

### Test it:
1. Visit the URL in browser
2. Try logging in with test credentials
3. Check if registration works
4. Verify data appears in dashboards

---

## Phase 8: Automatic Deployments

**Your setup is now complete!** 

Every time you push to GitHub:
1. GitHub notifies Render
2. Render automatically:
   - Pulls latest code
   - Installs dependencies
   - Rebuilds app
   - Deploys new version
3. Your app updates automatically in ~2 minutes

---

## Troubleshooting

### Deploy fails with "Build error"
1. Check **Logs** tab for specific error
2. Common issues:
   - Missing dependency in `requirements.txt`
   - Python syntax error
   - Missing import in `wsgi.py`
3. Fix locally, commit, and push again

### App crashes after deploy
1. Check **Logs** tab
2. Look for error messages
3. Common issues:
   - Database connection failed (check `DATABASE_URL`)
   - Missing environment variable
   - Database not initialized
4. Use **Shell** to debug

### "Cannot connect to database"
1. Verify `DATABASE_URL` is correct in Render environment
2. Check database allows remote connections
3. Test connection locally first
4. Verify username/password are correct
5. Check firewall allows port 3306

### App takes 10+ seconds to respond
- Normal on free tier (cold start)
- Upgrade to Starter plan for faster response
- First request after inactivity is slower

### Need to run migrations after deploy
Use **Shell** tab:
```bash
# Check current schema
flask db current

# Run pending migrations
flask db upgrade

# Create new migration if needed
flask db migrate -m "add new field"
```

---

## Monitoring & Maintenance

### View Logs
- Render dashboard → Click service → **Logs** tab
- See all requests, errors, and app output in real-time

### Set Up Alerts
- Render dashboard → Click service → **Settings** → **Alerts**
- Get notified if your app crashes

### Scale Up (when ready for production)
1. Render dashboard → Click service → **Settings**
2. Change Plan from "Free" to "Starter" or higher
3. Increase CPU/Memory if needed

---

## Next Steps

✅ **Completed:**
- GitHub repository connected to Render
- Code automatically deployed
- Live app running

🔄 **Consider for Production:**
- Add custom domain (CNAME record)
- Set up monitoring and alerts
- Upgrade to paid plan for reliability
- Add Redis for better rate limiting
- Configure automated backups for database
- Add SSL certificate (Render provides free)

---

## Quick Reference: Useful Commands

### Check deployment status
```bash
# In Render Shell
ps aux  # See running processes
```

### Restart app
- Render dashboard → Service → **Restart** button

### View environment variables
```bash
# In Render Shell
env | grep FLASK
```

### Run one-time command
```bash
# In Render Shell (runs once, then exits)
flask shell
```

---

## Support
- **Render Docs**: https://render.com/docs
- **Flask Docs**: https://flask.palletsprojects.com
- **GitHub Issues**: Report issues in your repository

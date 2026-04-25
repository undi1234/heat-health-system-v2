# Database Connection Troubleshooting Guide

## Quick Diagnosis

### Symptom 1: "Only Login/Register Forms Showing"
**Cause:** Database isn't connected, app loads but can't access other pages
**Solution:**
1. Check `DATABASE_URL` environment variable is set
2. Verify PostgreSQL database is running
3. Test connection locally first

### Symptom 2: "Access Denied for User"
**Cause:** Wrong database credentials
**Solution:**
```bash
# Verify credentials from Render PostgreSQL
# Format should be:
# postgresql://username:password@hostname:5432/database

# Test connection locally:
export DATABASE_URL="postgresql://user:pass@host/db"
python app.py
```

### Symptom 3: "Unresolved Host"
**Cause:** Database hostname is incorrect
**Solution:**
1. Go to Render dashboard → PostgreSQL database
2. Copy the "Internal Database URL"
3. Paste into Render environment variable `DATABASE_URL`

### Symptom 4: App Crashes on Startup
**Cause:** Usually a database driver issue
**Solution:**
```bash
# Verify psycopg2 is installed
python -c "import psycopg2; print('psycopg2 installed')"

# If not, install:
pip install psycopg2-binary==2.9.9
```

---

## Complete Connection Flow

```
Your App (on Render)
        ↓
DATABASE_URL env variable
        ↓
config.py reads and formats URL
        ↓
PostgreSQL driver (psycopg2)
        ↓
PostgreSQL database (on Render)
```

**Each step must work for connection to succeed.**

---

## Testing Database Connection

### Local Test 1: Connection String Format
```python
# Test the URL format
import os

DATABASE_URL = "postgresql://user:pass@dpg-xxx.render.com/heat_health_db"

# Auto-fix format if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://")

print(f"Testing URL: {DATABASE_URL}")
```

### Local Test 2: Direct Connection
```bash
# Install psycopg2 if not already
pip install psycopg2-binary

# Test direct connection with psql
psql "postgresql://user:password@dpg-xxx.render.com/heat_health_db"
```

### Local Test 3: SQLAlchemy Connection
```python
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://user:pass@host/db"
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Local Test 4: Flask App Connection
```bash
# Set environment variable
export DATABASE_URL="postgresql+psycopg2://user:pass@host/db"
export FLASK_ENV=production

# Run app and check logs
python app.py

# Should show:
# [INFO] Database connection successful
# [INFO] Database tables created successfully
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `access denied for user` | Wrong credentials | Check DATABASE_URL in Render env vars |
| `unresolved host name` | Hostname typo | Copy full URL from Render dashboard |
| `too many connections` | Connection pool issue | Check SQLALCHEMY_ENGINE_OPTIONS |
| `SSL error` | Certificate issue | Already handled in config.py |
| `no module named psycopg2` | Missing driver | `pip install psycopg2-binary==2.9.9` |
| `relation "user" does not exist` | Tables not created | Run `db.create_all()` manually |
| `connection timeout` | Network issue | Check firewall/network rules |

---

## Database URL Format Examples

### PostgreSQL (Render) ✓ CORRECT
```
postgresql+psycopg2://user:password@dpg-xxx.render.com:5432/database
```

### PostgreSQL (Render, auto-converted) ✓ CORRECT
```
postgres://user:password@dpg-xxx.render.com:5432/database
(gets converted to postgresql+psycopg2://)
```

### MySQL (fallback) ✓ CORRECT
```
mysql+pymysql://user:password@localhost/database
```

### INCORRECT Examples ❌
```
postgresql://user:password@host/db           (missing +psycopg2)
postgres://user:password@host/db             (old format, but auto-converted)
mysql://user:password@host/db                (missing +pymysql)
postgresql+psycopg2//user:password@host/db   (missing colon after driver)
```

---

## Environment Variable Checklist

Before deploying, verify in Render dashboard:

```
✓ FLASK_ENV=production
✓ PYTHON_VERSION=3.11
✓ SECRET_KEY=<long-random-string>
✓ DATABASE_URL=postgresql+psycopg2://user:pass@host/db
✓ OPENWEATHER_API_KEY=<your-key>
✓ SENSOR_SECRET=<your-secret>
✓ HEALTH_WORKER_CODE=<your-code>
✓ DEFAULT_CITY=Clarin,Bohol,PH
```

**Note:** DATABASE_URL should NOT be in your code or `.env` file committed to Git.

---

## Manual Database Initialization

If tables aren't created automatically:

```python
# In Python shell with app context
from app import app, db

with app.app_context():
    try:
        db.create_all()
        print("Tables created successfully")
    except Exception as e:
        print(f"Error: {e}")
```

---

## Logs to Check

### In Render Dashboard
1. Go to your web service
2. Click "Logs" tab
3. Look for these messages:

**Success:**
```
[INFO] Database connection successful
[INFO] Database tables created successfully
[INFO] Serving Flask app
[INFO] Running on 0.0.0.0:5000
```

**Error Examples:**
```
[ERROR] Database initialization failed: (psycopg2.OperationalError) ...
[ERROR] can't connect to server: Connection refused
[ERROR] role "user" does not exist
```

---

## Rollback If Deployment Fails

1. **Stop the service:**
   - Render dashboard → Select service → "Suspend"

2. **Check previous working commit:**
   ```bash
   git log --oneline
   git revert <commit-hash>
   git push origin main
   ```

3. **Revert DATABASE_URL:**
   - If changed, revert to previous working database URL

4. **Redeploy:**
   - Render → "Manual Deploy"

---

## Performance Considerations

### Connection Pool Settings (in config.py)
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,           # Test connection before using
    "pool_recycle": 280,              # Recycle after 280 seconds
    "pool_size": 10,                  # Keep 10 connections ready
    "max_overflow": 20                # Allow up to 20 extra connections
}
```

### Impact
- **pool_pre_ping**: Slightly slower but more reliable
- **pool_recycle**: Prevents connection timeout after long idle
- **pool_size**: Higher = more memory, better concurrency
- **max_overflow**: Handles traffic spikes gracefully

---

## Migration Issues

If you added/modified tables and database is out of sync:

```bash
# Generate migration
flask db migrate -m "Description of changes"

# Review migration file in migrations/versions/

# Apply migration
flask db upgrade
```

---

## When to Contact Support

- Unable to connect to database even after following this guide
- Credentials are correct but connection still fails
- Database shows as running but app can't reach it
- Need help with database backup/recovery

**Provide when contacting support:**
1. Full error message from logs
2. Environment variables (except passwords)
3. Database status (running/stopped)
4. Render build logs

---

**Last Updated:** April 25, 2026

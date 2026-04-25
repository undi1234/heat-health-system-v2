# heat-health-monitoring-system
Heat Health Monitoring System using Flask and MySQL. Ongoing development project.

## Deployment

### Prerequisites
- Python 3.11+ or compatible version
- MySQL server running and accessible
- `.venv` virtual environment activated
- `.env` file created from `.env.example`

### Install dependencies
```bash
pip install -r requirements.txt
```

### Environment variables
Copy `.env.example` to `.env` and fill in values:
- `FLASK_ENV=development` or `production`
- `SECRET_KEY` (strong random string)
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `DATABASE_URL` if using a hosted database
- `OPENWEATHER_API_KEY`
- `SENSOR_SECRET`
- `HEALTH_WORKER_CODE`
- `DEFAULT_CITY`
- `RATELIMIT_STORAGE_URI` (use Redis for production, e.g. `redis://localhost:6379`)

### Initialize database
Set the Flask application first, then run migrations:

On Windows PowerShell:
```powershell
$env:FLASK_APP = "wsgi.py"
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

On macOS/Linux:
```bash
export FLASK_APP=wsgi.py
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

### Run locally
```bash
python app.py
```

### Production server
Use a production WSGI server such as Gunicorn:
```bash
gunicorn wsgi:app --workers 4 --bind 0.0.0.0:5000
```

On Windows, use Waitress instead:
```bash
pip install waitress
waitress-serve --call "wsgi:app"
```

### Production best practices
- Always use `FLASK_ENV=production`
- Serve over HTTPS
- Use `SESSION_COOKIE_SECURE=True`
- Store secrets in environment variables, not in source control
- Use a reverse proxy like nginx or Apache
- Use Redis or another persistent backend for rate limiting in production
- Do not run the Flask built-in server in production

### Security notes
- `.env` is ignored by `.gitignore`
- `config.py` loads production settings from environment variables
- `README.md` includes deployment commands

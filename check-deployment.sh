#!/bin/bash
# Pre-deployment checklist for Render

echo "=== Heat Health Monitoring System - Pre-Deployment Checklist ==="
echo ""

# Check required files
echo "✓ Checking required files..."
files=("wsgi.py" "app.py" "config.py" "requirements.txt" "render.yaml" ".env.example")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing - CRITICAL"
    fi
done

echo ""
echo "✓ Checking Python syntax..."
python -m py_compile wsgi.py app.py config.py models.py routes/auth.py 2>/dev/null && echo "  ✓ All Python files valid" || echo "  ✗ Syntax errors found"

echo ""
echo "✓ Checking required dependencies in requirements.txt..."
deps=("gunicorn" "Flask" "Flask-SQLAlchemy" "Flask-Migrate")
for dep in "${deps[@]}"; do
    grep -q "$dep" requirements.txt && echo "  ✓ $dep" || echo "  ✗ $dep missing"
done

echo ""
echo "✓ Checking .env configuration..."
if [ -f ".env" ]; then
    echo "  ✓ .env file exists"
    [ ! -z "$SECRET_KEY" ] && echo "  ✓ SECRET_KEY set" || echo "  ✗ SECRET_KEY not set"
    [ ! -z "$DB_PASSWORD" ] && echo "  ✓ DB_PASSWORD set" || echo "  ✗ DB_PASSWORD not set"
else
    echo "  ⚠ .env not found - you must set environment variables in Render dashboard"
fi

echo ""
echo "=== Pre-deployment checklist complete ==="
echo ""
echo "Next steps:"
echo "1. Commit all changes: git add . && git commit -m 'Ready for Render deployment'"
echo "2. Push to GitHub: git push"
echo "3. Go to https://render.com and connect your repository"
echo "4. See DEPLOYMENT_RENDER.md for detailed instructions"

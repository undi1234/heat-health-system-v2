# Health Worker Registration Guide

## Issue Summary
The health worker code validation was failing because:
1. The code needs to match exactly what's in the `HEALTH_WORKER_CODE` environment variable
2. The form needs to properly pass the health worker code to the server
3. Error messages weren't clear about what was wrong

## Solution Implemented

### Fixed Issues:
✅ Improved code validation with proper whitespace trimming  
✅ Better error messages showing validation feedback  
✅ Form data is now preserved when validation fails  
✅ Health worker code field is now marked as required  
✅ Position field validation improved  

---

## How to Register as Health Worker

### Step-by-Step:

1. **Navigate to Register Page**
   - Click "Register" on the login page or go to `/register_page`

2. **Fill in Basic Information**
   - Full Name: Enter your first and last name (e.g., "Juan Dela Cruz")
   - Username: Create a username related to your name (e.g., "juandelacruz123")
   - Password: Must have:
     - At least 8 characters
     - At least 1 uppercase letter
     - At least 1 lowercase letter
     - At least 1 number
   - Role: **Select "HealthWorker"**

3. **Health Worker Fields Will Appear**
   Once you select "HealthWorker" role, these fields appear:
   - Position: Select your position
     - Nurse
     - Midwife
     - Barangay Health Worker
   - Contact: Your phone number (Philippine format: 09xxxxxxxxx)
   - **Health Worker Code: Enter your authorized code**

4. **Enter Health Worker Code**
   - Ask your administrator for the health worker code
   - Enter it exactly as provided (case-sensitive)
   - Current code format: `HW-YYYY-XXXX`

5. **Submit**
   - Click "Register"
   - If successful, you'll be redirected to login
   - If there's an error, check:
     - Is the code correct?
     - Is your phone number valid?
     - Is your position selected?

---

## Common Issues and Solutions

### Issue 1: "Invalid Health Worker Code"
**Cause:** The code you entered doesn't match the expected code  
**Solution:**
- Double-check the code spelling and case
- Make sure there are no extra spaces before/after the code
- Ask your administrator for the correct code

### Issue 2: "Health Worker Code is required"
**Cause:** You left the code field empty  
**Solution:**
- Make sure the Health Worker Code field is visible (it appears when you select "HealthWorker" role)
- Enter your health worker code
- Don't leave it blank

### Issue 3: "Please select a valid position"
**Cause:** No position was selected or invalid position  
**Solution:**
- Select one of these positions:
  - Nurse
  - Midwife
  - Barangay Health Worker

### Issue 4: Form Won't Submit
**Cause:** Required fields are missing or invalid  
**Solution:**
- Fill all fields (marked with red asterisks)
- Make sure password meets requirements
- Check that phone number is valid
- Verify role is selected

---

## Health Worker Code Format

**Current Code:** `HW-2026-1234`

**Components:**
- `HW` = Health Worker prefix
- `2026` = Year
- `1234` = Sequential number

**Important Notes:**
- The code is case-sensitive
- No spaces before or after
- Exact match required
- Contact your administrator if you don't have this code

---

## Environment Variable Configuration

For administrators deploying the system:

### Local Development (.env):
```
HEALTH_WORKER_CODE=HW-2026-1234
```

### Render Production:
1. Go to your Render service dashboard
2. Click "Environment" tab
3. Add/Update variable:
   - Key: `HEALTH_WORKER_CODE`
   - Value: `HW-2026-1234`
4. Save and redeploy

### Important:
- The code must be set in BOTH:
  1. `.env` file (for local development)
  2. Render environment variables (for production)
- If not set, health worker registration will fail

---

## Testing Health Worker Registration

### Local Test:
1. Ensure `.env` has `HEALTH_WORKER_CODE=HW-2026-1234`
2. Start the app: `python app.py`
3. Go to `http://localhost:5000/register_page`
4. Fill form and try registering as health worker
5. Use correct code: `HW-2026-1234`

### Production Test:
1. Ensure Render has `HEALTH_WORKER_CODE` environment variable set
2. After deployment, visit your app URL
3. Try registering as health worker
4. Code should match Render's environment variable

---

## Troubleshooting Checklist

- [ ] Is the health worker code visible? (Should appear after selecting "HealthWorker" role)
- [ ] Is the code exactly correct? (case-sensitive, no spaces)
- [ ] Is the position selected? (Nurse, Midwife, or Barangay Health Worker)
- [ ] Is the phone number valid? (09xxxxxxxxx format)
- [ ] Is the form properly submitted? (Check for JavaScript errors in browser console)
- [ ] Is the code set in environment variables? (Check Render dashboard for environment variables)

---

## For Administrators

### Setting/Changing Health Worker Code:

**Step 1: Update Local Code**
```bash
# Edit .env file
HEALTH_WORKER_CODE=HW-YOUR-NEW-CODE
```

**Step 2: Update Render Environment**
1. Go to Render dashboard
2. Select your service
3. Go to "Environment" tab
4. Update `HEALTH_WORKER_CODE` variable
5. Click "Save Changes" (auto-deploys)

**Step 3: Verify**
```bash
# Test locally
export HEALTH_WORKER_CODE=HW-YOUR-NEW-CODE
python app.py
```

### Distribution:
- Share the code with authorized health workers
- Keep code confidential
- Change code periodically for security
- Document when code was changed

---

## Security Notes

1. **Code is Confidential**
   - Only share with authorized health workers
   - Don't include in public documentation
   - Don't commit to repository with real values

2. **Environment Variables**
   - Use `.env` for local development only
   - Use Render environment settings for production
   - Never hardcode values in code

3. **Access Control**
   - Only health workers with valid code can register
   - Prevents unauthorized registration
   - Maintains data integrity

---

## Technical Details

### Code Validation Location:
- File: `routes/auth.py`
- Function: `register()`
- Lines: ~335-360

### Validation Steps:
1. Check if code field is empty
2. Strip whitespace from code
3. Get code from environment variable
4. Compare code strings (exact match)
5. If mismatch, show error
6. Otherwise, allow registration

### Form Handling:
- File: `templates/register.html`
- Role selection triggers field visibility
- JavaScript shows/hides health worker fields
- Form data preserved on validation failure

---

**Last Updated:** April 25, 2026  
**Status:** Fixed and deployed

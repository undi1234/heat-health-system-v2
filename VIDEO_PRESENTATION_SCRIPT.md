# Heat Health Monitoring System - Video Presentation Script

## Introduction (0:00 - 0:30)
"Hello everyone! Today, I'm excited to present our Heat Health Monitoring System - a comprehensive solution designed to protect communities from heat-related illnesses in the Philippines.

This system combines real-time temperature monitoring, resident health tracking, and health worker management to create a safer environment during hot weather conditions."

## What is the System? (0:30 - 1:30)
"Our Heat Health Monitoring System is a web-based application that:

- Monitors temperature and heat index levels in real-time
- Allows residents to report heat-related symptoms
- Enables health workers to manage illness cases and user accounts
- Provides safety alerts and recommendations based on heat levels
- Generates comprehensive reports for health authorities

The system is built with Flask and uses PostgreSQL for data storage, deployed on Render for reliable hosting."

## System Features (1:30 - 3:00)

### 1. User Authentication & Roles (1:30 - 1:45)
"The system supports two main user types:
- Residents: Can report illnesses and view safety alerts
- Health Workers: Can manage cases, users, and view reports

Users register with their personal information and role-specific details."

### 2. Temperature Monitoring (1:45 - 2:15)
"Real-time temperature data is fetched from OpenWeather API and stored in our database. The system automatically calculates heat index values and categorizes them into safety levels:
- Normal (Green)
- Caution (Yellow) 
- Extreme Caution (Orange)
- Danger (Red)
- Extreme Danger (Dark Red)"

### 3. Resident Dashboard (2:15 - 2:45)
"Residents have access to:
- Current temperature and heat index for their barangay
- Safety reminders based on heat levels
- Illness reporting form with symptom selection
- Personal profile management"

### 4. Health Worker Dashboard (2:45 - 3:00)
"Health workers can:
- View and manage all illness records
- Add new cases for residents
- Update case statuses
- Manage user accounts
- Generate heat health reports"

## Step-by-Step User Guide (3:00 - 6:00)

### For Residents (3:00 - 4:30)

#### Step 1: Registration (3:00 - 3:15)
"1. Visit the registration page
2. Fill in your full name, username, and password
3. Select 'Resident' as your role
4. Choose your gender and barangay address
5. Enter your contact number (starting with 09)
6. Submit the form"

#### Step 2: Login (3:15 - 3:20)
"1. Enter your username and password
2. Click login to access your dashboard"

#### Step 3: View Dashboard (3:20 - 3:35)
"1. See current temperature and heat index for your area
2. Read safety reminders based on current heat level
3. Check for any alerts if heat levels are dangerous"

#### Step 4: Report Illness (3:35 - 4:00)
"1. Click 'Report Illness Case' from the sidebar
2. Select symptoms from the dropdown or type them manually
3. The date is automatically set to today
4. Submit your report"

#### Step 5: Update Profile (4:00 - 4:15)
"1. Go to Account settings
2. Update your contact information or address
3. Save changes"

#### Step 6: Logout (4:15 - 4:30)
"1. Click the logout button in the top right
2. Confirm logout"

### For Health Workers (4:30 - 6:00)

#### Step 1: Registration (4:30 - 4:45)
"1. Visit the registration page
2. Fill in your details
3. Select 'HealthWorker' as your role
4. Choose your position (Nurse, Midwife, or Barangay Health Worker)
5. Enter the health worker code provided by administrators
6. Submit the form"

#### Step 2: Login (4:45 - 4:50)
"1. Enter your credentials
2. Access the health worker dashboard"

#### Step 3: Manage Illness Records (4:50 - 5:15)
"1. Click 'Illness Records' from the sidebar
2. View all reported cases
3. Add new cases by clicking '+ Add Case'
4. Update case statuses by clicking the edit button
5. Delete cases if necessary"

#### Step 4: Manage Users (5:15 - 5:30)
"1. Go to 'Users' section
2. View all registered users
3. Edit user information
4. Delete users (except yourself)"

#### Step 5: View Reports (5:30 - 5:45)
"1. Access the 'Reports' page
2. See summary statistics
3. Generate detailed heat reports
4. Export data for further analysis"

#### Step 6: Temperature Management (5:45 - 6:00)
"1. View temperature records
2. Add manual temperature readings
3. Monitor heat index trends"

## Technical Implementation (6:00 - 7:00)
"The system is built with:
- Backend: Python Flask framework
- Database: PostgreSQL with SQLAlchemy ORM
- Frontend: HTML, CSS, JavaScript
- Deployment: Render hosting platform
- Security: CSRF protection, input validation, role-based access

Key technical features include:
- Real-time API integration for weather data
- Automated heat index calculations
- Secure user authentication
- Responsive design for mobile and desktop"

## Benefits & Impact (7:00 - 8:00)
"This system provides several benefits:

1. **Early Warning System**: Residents get timely alerts about dangerous heat conditions
2. **Efficient Case Management**: Health workers can quickly respond to illness reports
3. **Data-Driven Decisions**: Comprehensive reports help authorities make informed decisions
4. **Community Health**: Promotes preventive healthcare during heat waves
5. **Accessibility**: Web-based system accessible from any device with internet

By monitoring heat levels and illness patterns, we can reduce heat-related health risks and improve community resilience."

## Conclusion (8:00 - 8:30)
"Thank you for watching this presentation of our Heat Health Monitoring System. This platform demonstrates how technology can be used to protect public health and enhance community safety.

We believe this system will be valuable for barangays and local health authorities in managing heat-related health challenges. If you have any questions, please feel free to ask!"

## Demo Screenshots/Timeline
- 0:00-0:30: System logo and introduction
- 0:30-1:30: Feature overview slides
- 1:30-3:00: Feature demonstrations
- 3:00-4:30: Resident user flow
- 4:30-6:00: Health worker user flow
- 6:00-7:00: Technical architecture
- 7:00-8:00: Benefits and impact
- 8:00-8:30: Conclusion and Q&A
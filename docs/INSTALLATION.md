# CONNECTBOOK – INSTALLATION GUIDE (WINDOWS 11)

### 1. System Requirements
- Windows 11 (64-bit)
- Python 3.12+ (ensure "Add Python to PATH" was selected during install)
- PowerShell 5.1+ or PowerShell 7

### 2. Step-by-Step Installation

#### Step 1: Clone or Navigate to the Workspace
```powershell
cd C:\Users\onkar\OneDrive\Documents\Antigravity\first
```

#### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

#### Step 3: Upgrade Pip & Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

#### Step 5: Run Database Migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

#### Step 6: Collect Static Files
```powershell
python manage.py collectstatic --noinput
```

#### Step 7: Seed Sample Social Data
```powershell
python manage.py seed_connectbook
```

#### Step 8: Start the Local Development Server
```powershell
python manage.py runserver 127.0.0.1:8002
```

Navigate to [http://127.0.0.1:8002/](http://127.0.0.1:8002/) in your browser.

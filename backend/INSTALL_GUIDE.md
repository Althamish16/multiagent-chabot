# Quick Installation Guide

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

## Installation Steps

### 1. Clean Environment (Recommended)
```powershell
# Navigate to backend directory
cd backend

# Remove old virtual environment (if exists)
Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue

# Create new virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip
```

### 2. Install All Requirements
```powershell
# Install all packages from requirements.txt
pip install -r requirements.txt
```

### 3. Verify Installation
```powershell
# Check installed packages
pip list

# Verify key packages
pip show fastapi openai langchain motor msal
```

## Alternative: Install by Category

If you want to install packages incrementally:

### Core Server Only
```powershell
pip install fastapi==0.110.1 uvicorn==0.25.0 pydantic==2.11.9 python-dotenv==1.1.1
```

### Add Database
```powershell
pip install motor==3.3.1 pymongo==4.5.0 dnspython==2.8.0
```

### Add Authentication
```powershell
pip install msal==1.34.0 PyJWT==2.10.1 "python-jose[cryptography]==3.5.0"
```

### Add AI Agents
```powershell
pip install openai==2.2.0 langchain==0.3.27 langchain-openai==0.3.35 langgraph==0.6.8
```

## Troubleshooting

### Issue: pip install fails
**Solution**: Upgrade pip
```powershell
python -m pip install --upgrade pip setuptools wheel
```

### Issue: Cryptography installation fails
**Solution**: Install Visual C++ Build Tools or use pre-built wheel
```powershell
pip install --upgrade pip
pip install cryptography --only-binary cryptography
```

### Issue: Import errors after installation
**Solution**: Ensure virtual environment is activated
```powershell
# Check if venv is active (should see (venv) in prompt)
.\venv\Scripts\Activate.ps1

# Reinstall if needed
pip install -r requirements.txt --force-reinstall
```

### Issue: Package conflicts
**Solution**: Use clean virtual environment
```powershell
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the Application

### Start Backend Server
```powershell
# Make sure you're in the backend directory and venv is activated
cd backend
.\venv\Scripts\Activate.ps1

# Run with auto-reload (development)
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# OR using Python directly
python -m uvicorn server:app --reload
```

### Start Frontend (in separate terminal)
```powershell
cd frontend
npm install
npm start
```

## Package Summary by Purpose

| Category | Key Packages | Purpose |
|----------|-------------|---------|
| Web Server | fastapi, uvicorn | REST API backend |
| Database | motor, pymongo | MongoDB async driver |
| Auth | msal, PyJWT | Azure AD SSO |
| AI | openai, langchain | AI agents |
| Orchestration | langgraph | Multi-agent coordination |
| Config | python-dotenv | Environment variables |
| Async | aiohttp, httpx | HTTP requests |

## File Sizes
- Total download size: ~150-200 MB
- Installation time: 2-5 minutes (depending on internet speed)

## Python Version Compatibility
- **Minimum**: Python 3.8
- **Recommended**: Python 3.10 or 3.11
- **Maximum tested**: Python 3.12

## Notes
- All packages are pinned to specific versions for reproducibility
- Development tools (pytest, black, flake8) are commented out
- Uncomment development tools in requirements.txt if needed for testing/linting

---

**Last Updated**: Based on project analysis of multi-agent chatbot with Azure AD auth

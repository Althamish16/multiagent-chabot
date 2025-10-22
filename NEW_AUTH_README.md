# 🔐 New Authentication System

A clean, simplified authentication system for the multiagent chatbot using Google OAuth 2.0.

## 🎯 What's Fixed

### Previous Issues
- ❌ Complex dual auth system (Azure AD + Google)
- ❌ Complicated session management
- ❌ Inconsistent token handling
- ❌ Poor error handling
- ❌ Confusing auth flow

### New Solution
- ✅ Single Google OAuth provider
- ✅ Clean session management
- ✅ Proper JWT tokens
- ✅ Clear error messages
- ✅ Simple auth flow

## 📁 New Files

### Backend
```
backend/
├── auth_new.py           # Main authentication module
├── auth_routes.py        # FastAPI auth endpoints
└── SERVER_UPDATES.py     # Guide for updating server.py
```

### Frontend
```
frontend/src/components/
├── AuthProvider_new.js    # Auth context provider
├── GoogleCallback_new.js  # OAuth callback handler
└── LoginButton_new.js     # Login UI component
```

### Documentation
```
├── AUTH_MIGRATION_GUIDE.md  # Detailed migration steps
├── migrate_auth.py          # Automated migration script
└── NEW_AUTH_README.md       # This file
```

## 🚀 Quick Start

### Option 1: Automatic Migration (Recommended)

```bash
# Run the migration script
python migrate_auth.py
```

This will:
1. Backup old files (`.backup` extension)
2. Rename new files to replace old ones
3. Show next steps

### Option 2: Manual Setup

1. **Backend:**
   ```bash
   cd backend
   
   # Rename new files
   mv auth_new.py auth.py
   # auth_routes.py is ready as-is
   
   # Backup old files (optional)
   mv google_auth.py google_auth.py.backup
   ```

2. **Frontend:**
   ```bash
   cd frontend/src/components
   
   # Rename new files
   mv AuthProvider_new.js AuthProvider.js
   mv GoogleCallback_new.js GoogleCallback.js
   mv LoginButton_new.js LoginButton.js
   
   # Backup old files (optional)
   mv AuthProvider.js AuthProvider.js.backup  # (before renaming)
   ```

3. **Update `server.py`:**
   - See `SERVER_UPDATES.py` for exact changes
   - Or follow `AUTH_MIGRATION_GUIDE.md`

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Google OAuth (Required)
GOOGLE_CLIENT_ID=your-client-id-from-google-console
GOOGLE_CLIENT_SECRET=your-client-secret-from-google-console
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# JWT Secret (Change this!)
JWT_SECRET=your-super-secret-key-at-least-32-chars-long

# Azure OpenAI (for AI features)
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-deployment-name
```

### Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: "Web application"
6. Authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback`
   - Add production URL when deploying
7. Copy Client ID and Client Secret to `.env`

## 🔄 Authentication Flow

```
┌─────────┐                ┌──────────┐                ┌────────┐
│ Browser │                │ Backend  │                │ Google │
└────┬────┘                └────┬─────┘                └───┬────┘
     │                          │                          │
     │ 1. Click Login           │                          │
     ├─────────────────────────►│                          │
     │                          │                          │
     │ 2. Get Auth URL          │                          │
     │◄─────────────────────────┤                          │
     │                          │                          │
     │ 3. Open Popup & Redirect │                          │
     ├──────────────────────────┼─────────────────────────►│
     │                          │                          │
     │ 4. User Signs In         │                          │
     │◄─────────────────────────┼──────────────────────────┤
     │                          │                          │
     │ 5. Callback with Code    │                          │
     ├─────────────────────────►│                          │
     │                          │                          │
     │                          │ 6. Exchange Code         │
     │                          ├─────────────────────────►│
     │                          │                          │
     │                          │ 7. Access Token          │
     │                          │◄─────────────────────────┤
     │                          │                          │
     │                          │ 8. Get User Info         │
     │                          ├─────────────────────────►│
     │                          │                          │
     │                          │ 9. User Profile          │
     │                          │◄─────────────────────────┤
     │                          │                          │
     │                          │ 10. Create Session       │
     │                          │     & Generate JWT       │
     │                          │                          │
     │ 11. Return JWT + Profile │                          │
     │◄─────────────────────────┤                          │
     │                          │                          │
     │ 12. Store Token          │                          │
     │    Close Popup           │                          │
     │                          │                          │
     │ 13. Make API Calls       │                          │
     │    with Bearer Token     │                          │
     ├─────────────────────────►│                          │
     │                          │                          │
```

## 🛡️ Security Features

- ✅ **Secure OAuth 2.0 Flow**: Industry standard authentication
- ✅ **JWT Tokens**: Stateless authentication with expiration
- ✅ **Session Management**: Server-side session tracking
- ✅ **CSRF Protection**: State parameter validation
- ✅ **Origin Verification**: PostMessage origin checking
- ✅ **HTTPS Ready**: Works with HTTPS in production

## 📚 API Endpoints

### Public Endpoints

#### `GET /api/auth/login`
Get Google OAuth authorization URL

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-state-string"
}
```

#### `POST /api/auth/callback`
Exchange authorization code for tokens

**Request:**
```json
{
  "code": "authorization-code-from-google",
  "redirect_uri": "http://localhost:5000/auth/google/callback"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user_profile": {
    "id": "google-user-id",
    "email": "user@example.com",
    "name": "User Name",
    "picture": "https://...",
    "verified_email": true
  },
  "session_id": "session-token"
}
```

#### `POST /api/auth/logout`
Logout and invalidate session

**Request:**
```json
{
  "session_id": "session-token"
}
```

### Protected Endpoints

#### `GET /api/auth/me`
Get current user information

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "id": "google-user-id",
  "email": "user@example.com",
  "name": "User Name",
  "picture": "https://...",
  "verified_email": true
}
```

#### `GET /api/auth/status`
Get authentication system status

**Response:**
```json
{
  "configured": true,
  "provider": "Google OAuth 2.0",
  "active_sessions": 5
}
```

## 💻 Usage Examples

### Backend

```python
from fastapi import Depends
from auth import get_current_user, get_google_token, UserProfile

# Require authentication
@app.get("/protected")
async def protected_route(user: UserProfile = Depends(get_current_user)):
    return {"message": f"Hello {user.name}"}

# Optional authentication
@app.get("/public")
async def public_route(user: UserProfile = Depends(get_optional_user)):
    if user:
        return {"message": f"Welcome back {user.name}"}
    return {"message": "Hello guest"}

# Need Google API access
@app.post("/send-email")
async def send_email(
    google_token: str = Depends(get_google_token),
    user: UserProfile = Depends(get_current_user)
):
    # Use google_token with Google APIs
    headers = {"Authorization": f"Bearer {google_token}"}
    # ... call Gmail API
```

### Frontend

```javascript
import { useAuth } from '@/components/AuthProvider';

function MyComponent() {
    const { user, isAuthenticated, login, logout, getAuthHeaders } = useAuth();
    
    // Make authenticated API call
    const fetchData = async () => {
        const response = await axios.get(
            'http://localhost:5000/api/protected',
            { headers: getAuthHeaders() }
        );
        return response.data;
    };
    
    return (
        <div>
            {isAuthenticated ? (
                <>
                    <p>Welcome {user.name}</p>
                    <button onClick={logout}>Logout</button>
                </>
            ) : (
                <button onClick={login}>Login</button>
            )}
        </div>
    );
}
```

## 🧪 Testing

```bash
# Start backend
cd backend
python server.py

# Start frontend
cd frontend
npm start

# Test auth flow:
# 1. Click "Sign in with Google"
# 2. Complete OAuth in popup
# 3. Verify user profile appears
# 4. Try protected endpoints
# 5. Test logout
```

## 🐛 Troubleshooting

### "Google OAuth not configured"
- Check `.env` file exists in backend folder
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Restart backend server

### "Popup blocked"
- Allow popups in browser settings
- User will see error message with instructions

### "Token has expired"
- Tokens expire after 24 hours
- User needs to log in again
- Consider implementing refresh tokens

### "Session expired or invalid"
- Sessions are stored in memory (reset on server restart)
- User needs to log in again
- For production, use Redis or database

### Import errors
- Make sure files are renamed correctly
- Check `server.py` imports match new module names
- Restart both backend and frontend

## 🚀 Production Deployment

### Use Redis for Sessions

```python
# Replace SessionStore in auth.py
import redis
import json

class RedisSessionStore:
    def __init__(self):
        self.redis = redis.from_url(os.getenv('REDIS_URL'))
    
    def create(self, user_id, user_data, google_tokens):
        session_id = secrets.token_urlsafe(32)
        self.redis.setex(
            f"session:{session_id}",
            86400,  # 24 hours
            json.dumps({
                'user_id': user_id,
                'user_data': user_data,
                'google_tokens': google_tokens
            })
        )
        return session_id
```

### Use HTTPS

Update `.env` for production:
```env
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
```

Add to Google Console:
- Authorized redirect URIs: `https://yourdomain.com/auth/google/callback`

### Rotate JWT Secret

Generate a secure secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📖 Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Introduction](https://jwt.io/introduction)

## ❓ Need Help?

1. Check logs in backend console
2. Check browser console for errors
3. Review `AUTH_MIGRATION_GUIDE.md`
4. Verify environment variables
5. Test step by step

---

**Ready to migrate?** Run `python migrate_auth.py` to get started! 🚀

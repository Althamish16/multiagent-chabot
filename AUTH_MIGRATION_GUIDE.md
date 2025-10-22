# Authentication System Migration Guide

## Overview
This guide helps you migrate from the old authentication system to the new, simplified one.

## What's New?

### Backend Changes
1. **Simplified auth module** (`auth_new.py`)
   - Single Google OAuth provider (removed Azure AD complexity)
   - Clean session management with in-memory store
   - Proper JWT token handling
   - Better error handling and logging

2. **Clean auth routes** (`auth_routes.py`)
   - RESTful API endpoints
   - Proper request/response models
   - HTML callback page for OAuth flow

### Frontend Changes
1. **Simplified AuthProvider** (`AuthProvider_new.js`)
   - Cleaner state management
   - Better error handling
   - Proper token storage and verification

2. **Improved callback handler** (`GoogleCallback_new.js`)
   - Visual feedback for users
   - Proper error states
   - Secure postMessage communication

3. **Updated login button** (`LoginButton_new.js`)
   - Loading states
   - User profile display
   - Error messages

## Migration Steps

### Step 1: Update Backend

1. **Replace imports in `server.py`:**

```python
# OLD imports (remove these)
from google_auth import (
    GoogleOAuth, UserProfile, AuthToken,
    get_current_user, session_manager,
    is_authenticated_request, get_user_from_request, GoogleAPIClient
)

# NEW imports (add these)
from auth_new import (
    google_auth,
    get_current_user,
    get_google_token,
    get_optional_user,
    session_store,
    UserProfile
)
from auth_routes import auth_router
```

2. **Remove old auth initialization:**

```python
# Remove these lines
try:
    google_auth = GoogleOAuth()
    print("✅ Google OAuth auth initialized")
except Exception as e:
    raise RuntimeError(f"❌ Google OAuth auth initialization failed: {e}")
```

3. **Add new auth router to FastAPI app:**

```python
# Add after creating api_router
from auth_routes import auth_router, create_callback_html

# Include auth router
api_router.include_router(auth_router)
```

4. **Update the OAuth callback route:**

```python
# Replace old @app.get("/auth/google/callback") with:
@app.get("/auth/google/callback")
async def google_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback - HTML version"""
    if error:
        return create_callback_html(success=False, error=error)
    
    if not code:
        return create_callback_html(success=False, error="No authorization code received")
    
    try:
        # Exchange code for tokens
        auth_response = await google_auth.handle_callback(code)
        
        # Return HTML page that sends data to parent window
        return create_callback_html(
            success=True,
            data={
                'access_token': auth_response.access_token,
                'user_profile': auth_response.user_profile.dict(),
                'session_id': auth_response.session_id
            }
        )
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return create_callback_html(success=False, error=str(e))
```

5. **Update protected routes to use new dependencies:**

```python
# Old way
@api_router.post("/some-endpoint")
async def some_endpoint(current_user: UserProfile = Depends(get_current_user)):
    # ...

# New way (same syntax, but using new auth_new module)
@api_router.post("/some-endpoint")
async def some_endpoint(current_user: UserProfile = Depends(get_current_user)):
    # ...

# For Google API access
@api_router.post("/send-email")
async def send_email(google_token: str = Depends(get_google_token)):
    # Use google_token to call Gmail API
```

### Step 2: Update Frontend

1. **Update imports in `App.js`:**

```javascript
// OLD
import { AuthProvider, useAuth } from "@/components/AuthProvider";
import { LoginButton } from "@/components/LoginButton";

// NEW
import { AuthProvider, useAuth } from "@/components/AuthProvider_new";
import { LoginButton } from "@/components/LoginButton_new";
```

2. **Update routing for callback (if using React Router):**

```javascript
// In your router configuration
import GoogleCallback from '@/components/GoogleCallback_new';

// Add route
<Route path="/auth/google/callback" element={<GoogleCallback />} />
```

3. **Update API calls to include auth headers:**

```javascript
const { getAuthHeaders } = useAuth();

// In your API calls
const response = await axios.get(`${API}/some-endpoint`, {
    headers: getAuthHeaders()
});
```

### Step 3: Environment Variables

Ensure your `.env` file has these variables:

```env
# Google OAuth (Required)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# JWT Secret (Change in production!)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Azure OpenAI (for AI features)
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-deployment
```

### Step 4: Test the New System

1. **Start the backend:**
```bash
cd backend
python server.py
```

2. **Start the frontend:**
```bash
cd frontend
npm start
```

3. **Test flow:**
   - Click "Sign in with Google"
   - Complete OAuth flow in popup
   - Verify user info appears
   - Try making authenticated API calls
   - Test logout

## Key Improvements

### Security
- ✅ Proper JWT token validation
- ✅ Session management with expiration
- ✅ Secure OAuth state validation
- ✅ Origin verification for postMessage

### User Experience
- ✅ Better loading states
- ✅ Clear error messages
- ✅ Visual feedback during auth
- ✅ Graceful error handling

### Code Quality
- ✅ Cleaner, more maintainable code
- ✅ Proper separation of concerns
- ✅ Better logging for debugging
- ✅ Type hints and documentation

## Troubleshooting

### "Google OAuth not configured"
- Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
- Restart backend after updating .env

### "Token has expired"
- Tokens expire after 24 hours
- User needs to log in again
- Consider implementing token refresh

### "Session expired or invalid"
- Sessions are in-memory (lost on restart)
- For production, use Redis or database
- User needs to log in again

### Popup blocked
- Browser is blocking popups
- User needs to allow popups for the site
- Error message will guide user

## Production Considerations

### Session Storage
Replace in-memory storage with Redis:

```python
# In auth_new.py
import redis
from typing import Optional, Dict, Any

class RedisSessionStore:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def create(self, user_id: str, user_data: dict, google_tokens: dict) -> str:
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
    
    # ... implement other methods
```

### Token Refresh
Implement Google token refresh:

```python
def refresh_google_token(self, refresh_token: str) -> str:
    """Refresh expired Google access token"""
    response = requests.post(
        self.config.TOKEN_URL,
        data={
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
    )
    response.raise_for_status()
    return response.json()['access_token']
```

### HTTPS in Production
- Use HTTPS for all OAuth redirects
- Update GOOGLE_REDIRECT_URI to use https://
- Configure proper CORS origins

## Files Reference

### New Files
- `backend/auth_new.py` - Main auth module
- `backend/auth_routes.py` - Auth API routes
- `frontend/src/components/AuthProvider_new.js` - Auth context
- `frontend/src/components/GoogleCallback_new.js` - OAuth callback
- `frontend/src/components/LoginButton_new.js` - Login UI

### Files to Remove (after migration)
- `backend/auth.py` (old Azure AD auth)
- `backend/google_auth.py` (old Google auth)
- `frontend/src/components/AuthProvider.js` (old)
- `frontend/src/components/GoogleCallback.js` (old)
- `frontend/src/components/LoginButton.js` (old)

## Support

For issues or questions:
1. Check logs in backend console
2. Check browser console for frontend errors
3. Verify environment variables
4. Test OAuth flow step by step

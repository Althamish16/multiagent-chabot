# OAuth Authentication Errors Fixed

## Issues Identified

### 1. **Cross-Origin-Opener-Policy (COOP) Blocking `window.closed`**
**Error:** `Cross-Origin-Opener-Policy policy would block the window.closed call.`

**Cause:** The backend sets `Cross-Origin-Opener-Policy: same-origin-allow-popups` for OAuth callback routes, which prevents the frontend from checking if the popup window is closed.

**Fix:** Added error handling around `popup.closed` check in `AuthProvider_new.js`.

### 2. **PostMessage Origin Mismatch**
**Error:** `Failed to execute 'postMessage' on 'DOMWindow': The target origin provided ('http://localhost:5000') does not match the recipient window's origin ('http://localhost:4200').`

**Cause:** The callback HTML was sending postMessage to `window.location.origin` (backend port 5000), but the frontend is running on port 4200.

**Fix:** Updated callback HTML to send postMessage to the correct frontend origin.

### 3. **Message Origin Validation Too Strict**
**Error:** Messages from backend origin were rejected by frontend.

**Cause:** `AuthProvider_new.js` only accepted messages from `window.location.origin`, but callback HTML is served by backend.

**Fix:** Updated message handler to accept messages from both frontend and backend origins.

### 4. **Wrong Fallback Redirect URLs**
**Error:** Fallback redirects went to backend port instead of frontend.

**Cause:** Error and success fallbacks redirected to `http://localhost:5000/` instead of frontend.

**Fix:** Updated all fallback redirects to use frontend URL.

## Changes Made

### File: `backend/auth_routes.py`

#### 1. Added Environment Variable Support
```python
import os

def create_callback_html(success: bool, data: dict = None, error: str = None):
    # Get frontend URL from environment or default
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
```

#### 2. Updated Success Callback JavaScript
```javascript
// Frontend origin (from environment or default)
const frontendOrigin = '{frontend_url}';

if (window.opener && !window.opener.closed) {{
    // We're in a popup, send message to parent window (frontend)
    window.opener.postMessage({{
        type: 'auth-success',
        ...authData
    }}, frontendOrigin);
    window.close();
}} else {{
    // Not in popup, redirect to frontend with data in URL hash
    const dataStr = encodeURIComponent(JSON.stringify(authData));
    window.location.href = frontendOrigin + '/#auth-success=' + dataStr;
}}
```

#### 3. Updated Error Callback JavaScript
```javascript
// Frontend origin (from environment or default)
const frontendOrigin = '{frontend_url}';

if (window.opener && !window.opener.closed) {{
    // We're in a popup, send error message to parent window (frontend)
    window.opener.postMessage({{
        type: 'auth-error',
        error: errorMsg
    }}, frontendOrigin);
    window.close();
}} else {{
    // Not in popup, redirect to frontend with error in URL hash
    const errorStr = encodeURIComponent(errorMsg);
    window.location.href = frontendOrigin + '/#auth-error=' + errorStr;
}}
```

#### 4. Updated Fallback Redirects
```javascript
} catch (err) {{
    console.error('Failed to handle auth callback:', err);
    // Fallback: redirect to frontend anyway
    window.location.href = '{frontend_url}/';
}}
```

### File: `frontend/src/components/AuthProvider_new.js`

#### 1. Updated Message Origin Validation
```javascript
const messageHandler = (event) => {{
    // Security: verify origin - allow both frontend and backend origins
    const allowedOrigins = [
        window.location.origin,  // Frontend origin (http://localhost:4200)
        'http://localhost:5000'  // Backend origin (where callback HTML is served)
    ];
    
    if (!allowedOrigins.includes(event.origin)) {{
        console.warn('Message from unexpected origin:', event.origin);
        return;
    }}
    // ... rest of handler
}};
```

#### 2. Added Error Handling for COOP Policy
```javascript
const checkClosed = setInterval(() => {{
    try {{
        if (popup.closed) {{
            clearInterval(checkClosed);
            window.removeEventListener('message', messageHandler);
            
            if (!user) {{
                const error = 'Authentication cancelled';
                setError(error);
                reject(new Error(error));
            }}
        }}
    }} catch (e) {{
        // COOP policy may block window.closed access
        // Continue checking - the message handler will catch success/failure
        console.warn('Could not check popup status due to COOP policy');
    }}
}}, 1000);
```

## Configuration

### Frontend Environment (`.env`)
```
REACT_APP_BACKEND_URL=http://localhost:5000
PORT=4200
WDS_SOCKET_PORT=4200
```

### Backend Environment (Optional)
```bash
# Set this if frontend is not on default port
export FRONTEND_URL=http://localhost:4200
```

## Expected Behavior After Fix

1. **✅ No COOP errors** - Error handling prevents crashes
2. **✅ Correct postMessage targets** - Messages sent to frontend origin
3. **✅ Accepted messages** - Both frontend and backend origins allowed
4. **✅ Proper fallbacks** - Redirects go to frontend, not backend

## Testing Steps

1. **Start backend:**
   ```bash
   cd backend
   uvicorn server:app --reload --host 0.0.0.0 --port 5000
   ```

2. **Start frontend:**
   ```bash
   cd frontend
   npm start
   ```
   (Should start on http://localhost:4200)

3. **Test authentication:**
   - Click login button
   - Should open Google OAuth popup
   - After authentication, popup should close and user should be logged in
   - No console errors about COOP or postMessage

4. **Check console:**
   - Should see: `INFO: 127.0.0.1:xxxxx - "GET /auth/login HTTP/1.1" 200 OK`
   - Should see: `INFO: 127.0.0.1:xxxxx - "GET /auth/google/callback?... HTTP/1.1" 200 OK`
   - No Cross-Origin-Opener-Policy errors
   - No postMessage origin mismatch errors

## Alternative Frontend Ports

If you need to change the frontend port:

1. **Update `.env`:**
   ```
   PORT=3000  # or any other port
   WDS_SOCKET_PORT=3000
   ```

2. **Update backend environment:**
   ```bash
   export FRONTEND_URL=http://localhost:3000
   ```

3. **Or update the default in `auth_routes.py`:**
   ```python
   frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
   ```

## Summary

The OAuth authentication flow should now work correctly without console errors. The main issues were:

- **COOP policy blocking popup status checks** → Added error handling
- **Wrong postMessage target origins** → Fixed to target frontend
- **Overly strict origin validation** → Allow both frontend and backend origins
- **Wrong fallback URLs** → Redirect to frontend instead of backend

All authentication flows (popup success, popup error, direct redirects) should now work properly.
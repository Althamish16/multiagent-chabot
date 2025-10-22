"""
Clean authentication routes for FastAPI server
Drop-in replacement for auth endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os

# Import new auth system
from auth_new import (
    google_auth,
    get_current_user,
    get_google_token,
    get_optional_user,
    session_store,
    UserProfile,
    AuthResponse
)

logger = logging.getLogger(__name__)

# Create auth router
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


# Request models
class CallbackRequest(BaseModel):
    """OAuth callback request"""
    code: str
    redirect_uri: Optional[str] = None


class LogoutRequest(BaseModel):
    """Logout request"""
    session_id: Optional[str] = None


# Auth endpoints
@auth_router.get("/login")
async def login():
    """
    Initiate Google OAuth login flow
    Returns authorization URL for client to redirect to
    """
    try:
        auth_data = google_auth.get_authorization_url()
        return auth_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.post("/callback", response_model=AuthResponse)
async def callback(request: CallbackRequest):
    """
    Handle OAuth callback - exchange code for tokens
    Creates user session and returns JWT token
    """
    try:
        auth_response = await google_auth.handle_callback(request.code)
        return auth_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/logout")
async def logout(request: LogoutRequest):
    """
    Logout user and invalidate session
    """
    if request.session_id:
        session_store.delete(request.session_id)
    
    return {"message": "Logged out successfully"}


@auth_router.get("/me")
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """
    Get current authenticated user information
    Requires valid JWT token in Authorization header
    """
    return current_user.dict()


@auth_router.get("/status")
async def auth_status():
    """
    Get authentication system status
    """
    from auth_new import AuthConfig
    
    return {
        "configured": AuthConfig.is_configured(),
        "provider": "Google OAuth 2.0",
        "active_sessions": len(session_store._sessions)
    }


@auth_router.get("/google/callback")
async def google_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    Handle Google OAuth callback - HTML version
    This is the redirect target from Google OAuth
    """
    if error:
        return create_callback_html(success=False, error=error)
    
    if not code:
        return create_callback_html(success=False, error="No authorization code received")
    
    try:
        # Exchange code for tokens using new auth system
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


# HTML callback page (alternative to API callback)
def create_callback_html(success: bool, data: dict = None, error: str = None):
    """Generate callback HTML page that redirects to frontend with auth data"""
    # Get frontend URL from environment or default
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:4200')
    
    if success:
        # Success page - redirect to frontend with tokens in URL fragment
        user_profile_json = json.dumps(data['user_profile'])
        access_token = data["access_token"]
        session_id = data["session_id"]
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Authentication Successful</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .icon {{
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                .title {{
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: #10b981;
                    margin-bottom: 0.5rem;
                }}
                .message {{
                    color: #6b7280;
                    font-size: 0.875rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✓</div>
                <div class="title">Authentication Successful!</div>
                <div class="message">Redirecting to app...</div>
            </div>
            <script>
            (function() {{
                try {{
                    // Encode auth data
                    const authData = {{
                        access_token: '{access_token}',
                        session_id: '{session_id}',
                        user_profile: {user_profile_json}
                    }};
                    
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
                }} catch (err) {{
                    console.error('Failed to handle auth callback:', err);
                    // Fallback: redirect to frontend anyway
                    window.location.href = '{frontend_url}/';
                }}
            }})();
            </script>
        </body>
        </html>
        """)
    else:
        # Error page - redirect to frontend with error
        error_msg = error or 'Unknown error'
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Authentication Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f43f5e 0%, #dc2626 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .icon {{
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                .title {{
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: #dc2626;
                    margin-bottom: 0.5rem;
                }}
                .message {{
                    color: #6b7280;
                    font-size: 0.875rem;
                    word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✗</div>
                <div class="title">Authentication Failed</div>
                <div class="message">{error_msg}</div>
                <div class="message" style="margin-top: 1rem;">Redirecting to app...</div>
            </div>
            <script>
            (function() {{
                try {{
                    const errorMsg = '{error_msg}';
                    
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
                }} catch (err) {{
                    console.error('Failed to handle auth error:', err);
                    // Fallback: redirect to frontend anyway
                    window.location.href = '{frontend_url}/';
                }}
            }})();
            </script>
        </body>
        </html>
        """)

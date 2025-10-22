"""
Updated server.py imports and auth setup
Copy these changes to your server.py
"""

# ============================================================================
# SECTION 1: IMPORTS (Replace lines 30-40)
# ============================================================================

# OLD IMPORTS (Remove these)
"""
try:
    from google_auth import (
        GoogleOAuth, UserProfile, AuthToken,
        get_current_user, session_manager,
        is_authenticated_request, get_user_from_request, GoogleAPIClient
    )
    print("✅ Google OAuth authentication loaded")
except ImportError as e:
    raise RuntimeError(f"❌ Google OAuth authentication not available: {e}")
"""

# NEW IMPORTS (Add these instead)
try:
    from auth import (
        google_auth,
        get_current_user,
        get_google_token,
        get_optional_user,
        session_store,
        UserProfile
    )
    from auth_routes import auth_router, create_callback_html
    print("✅ Google OAuth authentication loaded")
except ImportError as e:
    raise RuntimeError(f"❌ Google OAuth authentication not available: {e}")


# ============================================================================
# SECTION 2: REMOVE OLD AUTH INITIALIZATION (Remove lines 48-53)
# ============================================================================

# REMOVE THESE LINES:
"""
# Initialize Google OAuth
try:
    google_auth = GoogleOAuth()
    print("✅ Google OAuth auth initialized")
except Exception as e:
    raise RuntimeError(f"❌ Google OAuth auth initialization failed: {e}")
"""

# The new auth module initializes automatically, no need for this


# ============================================================================
# SECTION 3: ADD AUTH ROUTER (Add after api_router creation, around line 140)
# ============================================================================

# Create API router
api_router = APIRouter(prefix="/api")

# ADD THIS LINE:
api_router.include_router(auth_router)


# ============================================================================
# SECTION 4: REMOVE OLD AUTH ROUTES (Remove lines 556-625)
# ============================================================================

# REMOVE ALL THESE OLD ROUTES:
"""
@api_router.get("/auth/login")
async def login_redirect(redirect_uri: str = "http://localhost:5000/auth/google/callback"):
    ...

@api_router.post("/auth/callback")
async def auth_callback(auth_request: GoogleAuthCallbackRequest):
    ...

@api_router.post("/auth/logout")
async def logout(session_id: str = None):
    ...

@api_router.get("/auth/me")
async def get_current_user_info(current_user: UserProfile = Depends(get_current_user)):
    ...
"""

# These are now provided by auth_router from auth_routes.py


# ============================================================================
# SECTION 5: UPDATE OAUTH CALLBACK ROUTE (Replace around line 913)
# ============================================================================

# REPLACE the existing @app.get("/auth/google/callback") with:

@app.get("/auth/google/callback")
async def google_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback - HTML version"""
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
        logging.error(f"OAuth callback failed: {e}")
        return create_callback_html(success=False, error=str(e))


# ============================================================================
# SECTION 6: UPDATE PROTECTED ROUTES (Examples)
# ============================================================================

# Protected routes now use the new get_current_user dependency
# The syntax is the same, but it now uses the new auth module

# Example 1: Require authentication
@api_router.post("/some-protected-endpoint")
async def protected_endpoint(
    current_user: UserProfile = Depends(get_current_user)
):
    # current_user is guaranteed to be authenticated
    return {"user": current_user.email}


# Example 2: Optional authentication
@api_router.get("/some-public-endpoint")
async def public_endpoint(
    current_user: Optional[UserProfile] = Depends(get_optional_user)
):
    if current_user:
        return {"message": f"Hello {current_user.name}"}
    else:
        return {"message": "Hello guest"}


# Example 3: Need Google API access
@api_router.post("/send-email")
async def send_email(
    google_token: str = Depends(get_google_token),
    current_user: UserProfile = Depends(get_current_user)
):
    # Use google_token to call Gmail API
    # current_user has the user info
    return {"status": "email sent"}


# ============================================================================
# SUMMARY OF CHANGES
# ============================================================================

"""
CHANGES SUMMARY:

1. ✅ Updated imports to use new auth module
2. ✅ Removed old auth initialization
3. ✅ Added auth_router to api_router
4. ✅ Removed old auth route definitions
5. ✅ Updated OAuth callback route
6. ✅ Protected routes work the same way

FILES NEEDED:
- backend/auth.py (renamed from auth_new.py)
- backend/auth_routes.py (new file)

OLD FILES (can be removed):
- backend/google_auth.py (old)
- backend/auth.py (old Azure AD version)

NO CHANGES needed to:
- Protected route syntax (same Depends(get_current_user))
- Database operations
- Agent implementations
- Other endpoints
"""

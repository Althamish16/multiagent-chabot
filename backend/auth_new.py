"""
Simplified Google OAuth 2.0 Authentication
Clean implementation with proper error handling
"""
import os
import jwt
import json
import requests
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configuration
class AuthConfig:
    """Authentication configuration"""
    CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    # Google OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    # Required scopes
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # JWT settings
    JWT_SECRET = os.environ.get('JWT_SECRET', 'change-this-super-secret-key-in-production')
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if OAuth is properly configured"""
        return bool(cls.CLIENT_ID and cls.CLIENT_SECRET)


# Pydantic models
class UserProfile(BaseModel):
    """User profile information"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = False


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_profile: UserProfile
    session_id: str


# In-memory session storage (replace with Redis in production)
class SessionStore:
    """Simple in-memory session storage"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create(self, user_id: str, user_data: dict, google_tokens: dict) -> str:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = {
            'user_id': user_id,
            'user_data': user_data,
            'google_access_token': google_tokens.get('access_token'),
            'google_refresh_token': google_tokens.get('refresh_token'),
            'created_at': datetime.utcnow(),
            'last_accessed': datetime.utcnow()
        }
        logger.info(f"Created session for user {user_id}")
        return session_id
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = self._sessions.get(session_id)
        if session:
            session['last_accessed'] = datetime.utcnow()
            return session
        return None
    
    def delete(self, session_id: str):
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session {session_id}")
    
    def get_by_user_id(self, user_id: str) -> Optional[str]:
        """Get session ID by user ID"""
        for session_id, session in self._sessions.items():
            if session.get('user_id') == user_id:
                return session_id
        return None
    
    def cleanup_expired(self):
        """Remove expired sessions (older than 24 hours)"""
        now = datetime.utcnow()
        expired = [
            sid for sid, data in self._sessions.items()
            if (now - data['last_accessed']).total_seconds() > 86400
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")


# Global session store
session_store = SessionStore()


class GoogleAuth:
    """Google OAuth authentication handler"""
    
    def __init__(self):
        self.config = AuthConfig()
        if not self.config.is_configured():
            logger.warning("Google OAuth not configured - auth endpoints will not work")
    
    def get_authorization_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """Generate Google OAuth authorization URL"""
        if not self.config.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )
        
        if not state:
            state = secrets.token_urlsafe(16)
        
        params = {
            'client_id': self.config.CLIENT_ID,
            'redirect_uri': self.config.REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(self.config.SCOPES),
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        query_string = '&'.join([f'{k}={requests.utils.quote(str(v))}' for k, v in params.items()])
        auth_url = f"{self.config.AUTH_URL}?{query_string}"
        
        logger.info("Generated authorization URL")
        return {
            'auth_url': auth_url,
            'state': state
        }
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        if not self.config.is_configured():
            raise HTTPException(status_code=503, detail="Google OAuth not configured")
        
        token_data = {
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.config.REDIRECT_URI
        }
        
        try:
            response = requests.post(self.config.TOKEN_URL, data=token_data, timeout=10)
            response.raise_for_status()
            tokens = response.json()
            
            if 'access_token' not in tokens:
                raise HTTPException(status_code=400, detail="No access token in response")
            
            logger.info("Successfully exchanged code for tokens")
            return tokens
            
        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to get tokens: {str(e)}")
    
    def get_user_info(self, access_token: str) -> UserProfile:
        """Get user information from Google"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.config.USER_INFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            user_data = response.json()
            
            return UserProfile(
                id=user_data['id'],
                email=user_data['email'],
                name=user_data.get('name', user_data['email']),
                picture=user_data.get('picture'),
                verified_email=user_data.get('verified_email', False)
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user info: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to get user info: {str(e)}")
    
    def create_jwt_token(self, user_profile: UserProfile, session_id: str) -> str:
        """Create JWT token for the application"""
        payload = {
            'user_id': user_profile.id,
            'email': user_profile.email,
            'name': user_profile.name,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(hours=self.config.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.config.JWT_SECRET, algorithm=self.config.JWT_ALGORITHM)
        return token
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.config.JWT_SECRET,
                algorithms=[self.config.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def handle_callback(self, code: str) -> AuthResponse:
        """Complete OAuth flow - exchange code for tokens and create session"""
        # Exchange code for tokens
        google_tokens = self.exchange_code_for_tokens(code)
        
        # Get user information
        user_profile = self.get_user_info(google_tokens['access_token'])
        
        # Create session
        session_id = session_store.create(
            user_id=user_profile.id,
            user_data=user_profile.dict(),
            google_tokens=google_tokens
        )
        
        # Create JWT token
        jwt_token = self.create_jwt_token(user_profile, session_id)
        
        logger.info(f"User {user_profile.email} authenticated successfully")
        
        return AuthResponse(
            access_token=jwt_token,
            token_type="Bearer",
            expires_in=self.config.JWT_EXPIRATION_HOURS * 3600,
            user_profile=user_profile,
            session_id=session_id
        )


# FastAPI security
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserProfile:
    """Dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token
    auth = GoogleAuth()
    payload = auth.verify_jwt_token(credentials.credentials)
    
    # Get session
    session_id = payload.get('session_id')
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid token - no session")
    
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    # Return user profile
    user_data = session['user_data']
    return UserProfile(**user_data)


async def get_google_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Dependency to get Google access token for API calls"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify token
    auth = GoogleAuth()
    payload = auth.verify_jwt_token(credentials.credentials)
    
    # Get session
    session_id = payload.get('session_id')
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    
    google_token = session.get('google_access_token')
    if not google_token:
        raise HTTPException(status_code=401, detail="No Google access token")
    
    return google_token


# Optional: Helper to check if request is authenticated (returns None if not)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserProfile]:
    """Get user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Initialize global auth instance
google_auth = GoogleAuth()

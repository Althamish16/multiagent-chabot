"""
Google OAuth 2.0 Authentication Integration
Handles SSO login with Google OAuth
"""
import os
import jwt
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel
import secrets
import asyncio

# Configuration for Google OAuth
class GoogleOAuthConfig:
    # These will be loaded from environment variables
    CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id-here')
    CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret-here') 
    REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    # Google OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    # Scopes for accessing Google APIs
    SCOPES = [
        "openid",
        "profile", 
        "email",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # JWT Configuration
    JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this')
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = False

class AuthToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_profile: UserProfile
    google_access_token: str
    google_refresh_token: Optional[str] = None

class GoogleOAuth:
    def __init__(self):
        self.config = GoogleOAuthConfig()
    
    def get_auth_url(self, state: str = None) -> Dict[str, str]:
        """Generate Google OAuth authorization URL"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.config.CLIENT_ID,
            'redirect_uri': self.config.REDIRECT_URI,
            'scope': ' '.join(self.config.SCOPES),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        auth_url = self.config.AUTH_URL + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
        
        return {
            'auth_url': auth_url,
            'state': state
        }
    
    async def handle_auth_callback(self, code: str, redirect_uri: str = None) -> AuthToken:
        """Handle OAuth callback and exchange code for tokens"""
        if not redirect_uri:
            redirect_uri = self.config.REDIRECT_URI
            
        # Exchange authorization code for access token
        token_data = {
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        try:
            # Get tokens from Google
            token_response = requests.post(self.config.TOKEN_URL, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()
            
            google_access_token = tokens.get('access_token')
            google_refresh_token = tokens.get('refresh_token')
            
            if not google_access_token:
                raise HTTPException(status_code=400, detail="Failed to get access token from Google")
            
            # Get user information
            headers = {'Authorization': f'Bearer {google_access_token}'}
            user_response = requests.get(self.config.USER_INFO_URL, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
            
            # Create user profile
            user_profile = UserProfile(
                id=user_data['id'],
                email=user_data['email'],
                name=user_data['name'],
                picture=user_data.get('picture'),
                verified_email=user_data.get('verified_email', False)
            )
            
            # Generate JWT token for our application
            jwt_payload = {
                'user_id': user_profile.id,
                'email': user_profile.email,
                'name': user_profile.name,
                'exp': datetime.utcnow() + timedelta(hours=self.config.JWT_EXPIRATION_HOURS),
                'iat': datetime.utcnow()
            }
            
            jwt_token = jwt.encode(
                jwt_payload, 
                self.config.JWT_SECRET, 
                algorithm=self.config.JWT_ALGORITHM
            )
            
            return AuthToken(
                access_token=jwt_token,
                token_type="Bearer",
                expires_in=self.config.JWT_EXPIRATION_HOURS * 3600,
                user_profile=user_profile,
                google_access_token=google_access_token,
                google_refresh_token=google_refresh_token
            )
            
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to authenticate with Google: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

# Session management
class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, user_id: str, token_data: dict) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'user_id': user_id,
            'token_data': token_data,
            'created_at': datetime.utcnow(),
            'last_accessed': datetime.utcnow()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        session = self.sessions.get(session_id)
        if session:
            session['last_accessed'] = datetime.utcnow()
        return session
    
    def delete_session(self, session_id: str):
        self.sessions.pop(session_id, None)
    
    def cleanup_expired_sessions(self):
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if now - session['last_accessed'] > timedelta(hours=24)
        ]
        for session_id in expired_sessions:
            del self.sessions[session_id]

# Global instances
session_manager = SessionManager()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            GoogleOAuthConfig.JWT_SECRET, 
            algorithms=[GoogleOAuthConfig.JWT_ALGORITHM]
        )
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return UserProfile(
            id=user_id,
            email=payload.get('email'),
            name=payload.get('name'),
            picture=payload.get('picture'),
            verified_email=True
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def is_authenticated_request(request: Request) -> bool:
    """Check if request is authenticated"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        
        token = auth_header.split(" ")[1]
        jwt.decode(token, GoogleOAuthConfig.JWT_SECRET, algorithms=[GoogleOAuthConfig.JWT_ALGORITHM])
        return True
    except:
        return False

async def get_user_from_request(request: Request) -> Optional[UserProfile]:
    """Get user from request"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, GoogleOAuthConfig.JWT_SECRET, algorithms=[GoogleOAuthConfig.JWT_ALGORITHM])
        
        return UserProfile(
            id=payload.get('user_id'),
            email=payload.get('email'),
            name=payload.get('name'),
            picture=payload.get('picture'),
            verified_email=True
        )
    except:
        return None

# Google API integration helpers
class GoogleAPIClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {'Authorization': f'Bearer {access_token}'}
    
    async def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send email via Gmail API"""
        # This is a simplified implementation
        # In production, you'd use the Gmail API properly
        
        # For demo purposes, we'll simulate email sending
        await asyncio.sleep(0.5)  # Simulate API delay
        
        return {
            'id': f'gmail-{secrets.token_urlsafe(8)}',
            'status': 'sent',
            'to': to,
            'subject': subject,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_calendar_events(self) -> list:
        """Get calendar events via Google Calendar API"""
        # Demo implementation
        await asyncio.sleep(0.3)
        
        return [
            {
                'id': '1',
                'title': 'Google Meeting',
                'start': '2024-01-15T09:00:00Z',
                'end': '2024-01-15T10:00:00Z',
                'description': 'Team sync via Google Calendar'
            },
            {
                'id': '2', 
                'title': 'Demo Presentation',
                'start': '2024-01-15T14:00:00Z',
                'end': '2024-01-15T15:00:00Z',
                'description': 'Show the multi-agent system'
            }
        ]
    
    async def create_calendar_event(self, title: str, start: str, end: str, description: str = "") -> dict:
        """Create calendar event via Google Calendar API"""
        await asyncio.sleep(0.4)
        
        return {
            'id': f'cal-{secrets.token_urlsafe(8)}',
            'title': title,
            'start': start,
            'end': end,
            'description': description,
            'status': 'created'
        }
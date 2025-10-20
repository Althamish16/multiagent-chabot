"""
Azure Active Directory Authentication Integration
Handles SSO login with Microsoft Azure AD
"""
import os
import jwt
import msal
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel

# Configuration for Azure AD
class AzureADConfig:
    # These will be loaded from environment variables
    # User needs to set these in their .env file with real credentials
    CLIENT_ID = os.environ.get('AZURE_CLIENT_ID', 'your-client-id-here')
    CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', 'your-client-secret-here') 
    TENANT_ID = os.environ.get('AZURE_TENANT_ID', 'your-tenant-id-here')
    
    # Azure AD endpoints
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    SCOPES = ["User.Read", "Mail.Send", "Calendars.ReadWrite", "Notes.ReadWrite"]
    
    # JWT Configuration
    JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this')
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    tenant_id: str
    roles: list = []

class AuthToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_profile: UserProfile

class AzureADAuth:
    def __init__(self):
        self.config = AzureADConfig()
        self.msal_app = self._create_msal_app()
        
    def _create_msal_app(self):
        """Create MSAL confidential client application"""
        if not self.config.CLIENT_ID or self.config.CLIENT_ID == 'your-client-id-here':
            raise ValueError("Azure AD CLIENT_ID not configured. Please set AZURE_CLIENT_ID in .env file")
        if not self.config.CLIENT_SECRET or self.config.CLIENT_SECRET == 'your-client-secret-here':
            raise ValueError("Azure AD CLIENT_SECRET not configured. Please set AZURE_CLIENT_SECRET in .env file")
        if not self.config.TENANT_ID or self.config.TENANT_ID == 'your-tenant-id-here':
            raise ValueError("Azure AD TENANT_ID not configured. Please set AZURE_TENANT_ID in .env file")
        
        return msal.ConfidentialClientApplication(
            client_id=self.config.CLIENT_ID,
            client_credential=self.config.CLIENT_SECRET,
            authority=self.config.AUTHORITY
        )
    
    def get_auth_url(self, redirect_uri: str, state: str = None) -> Dict[str, Any]:
        """Get Azure AD authorization URL for user login"""
        try:
            auth_url = self.msal_app.get_authorization_request_url(
                scopes=self.config.SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )
            
            return {
                "auth_url": auth_url,
                "state": state
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")
    
    async def handle_auth_callback(self, code: str, redirect_uri: str) -> AuthToken:
        """Handle OAuth callback and exchange code for tokens"""
        try:
            # Exchange authorization code for tokens
            result = self.msal_app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.config.SCOPES,
                redirect_uri=redirect_uri
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {result.get('error_description')}")
            
            # Get user profile from Microsoft Graph
            access_token = result["access_token"]
            user_profile = await self._get_user_profile(access_token)
            
            # Create JWT token for our application
            jwt_payload = {
                "user_id": user_profile.id,
                "email": user_profile.email,
                "name": user_profile.name,
                "tenant_id": user_profile.tenant_id,
                "roles": user_profile.roles,
                "azure_access_token": access_token,  # Store for Microsoft Graph API calls
                "exp": datetime.now(timezone.utc) + timedelta(hours=self.config.JWT_EXPIRATION_HOURS),
                "iat": datetime.now(timezone.utc),
                "iss": "ai-agents-poc"
            }
            
            jwt_token = jose_jwt.encode(jwt_payload, self.config.JWT_SECRET, algorithm=self.config.JWT_ALGORITHM)
            
            return AuthToken(
                access_token=jwt_token,
                token_type="Bearer",
                expires_in=result.get("expires_in", self.config.JWT_EXPIRATION_HOURS * 3600),
                user_profile=user_profile
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
    
    async def _get_user_profile(self, access_token: str) -> UserProfile:
        """Get user profile from Microsoft Graph API"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=400, detail="Failed to fetch user profile")
                
                user_data = response.json()
                
                return UserProfile(
                    id=user_data["id"],
                    email=user_data["mail"] or user_data["userPrincipalName"],
                    name=user_data["displayName"],
                    picture=None,  # Can be fetched separately if needed
                    tenant_id=self.config.TENANT_ID,
                    roles=["user", "ai-agent-access"]  # Can be enhanced with actual role logic
                )
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")
    
    def verify_token(self, token: str) -> UserProfile:
        """Verify JWT token and extract user information"""
        try:
            # Decode and verify JWT token
            payload = jose_jwt.decode(
                token, 
                self.config.JWT_SECRET, 
                algorithms=[self.config.JWT_ALGORITHM]
            )
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Token expired")
            
            # Create user profile from token
            return UserProfile(
                id=payload["user_id"],
                email=payload["email"],
                name=payload["name"],
                tenant_id=payload["tenant_id"],
                roles=payload.get("roles", [])
            )
            
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

# FastAPI Security Dependencies
security = HTTPBearer()
azure_auth = AzureADAuth()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """FastAPI dependency to get current authenticated user"""
    return azure_auth.verify_token(credentials.credentials)

async def require_roles(required_roles: list):
    """FastAPI dependency factory for role-based access control"""
    def check_roles(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_roles

# Optional: Admin-only access
async def get_admin_user(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """Require admin role for access"""
    if "admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

class SessionManager:
    """Manage user sessions and tokens"""
    
    def __init__(self):
        self.active_sessions = {}  # In production, use Redis or database
    
    def create_session(self, user_id: str, token_data: Dict[str, Any]) -> str:
        """Create a new user session"""
        session_id = f"session-{user_id}-{datetime.now().timestamp()}"
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "token_data": token_data,
            "created_at": datetime.now(timezone.utc),
            "last_active": datetime.now(timezone.utc)
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = self.active_sessions.get(session_id)
        if session:
            session["last_active"] = datetime.now(timezone.utc)
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        return self.active_sessions.pop(session_id, None) is not None
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        expired_sessions = [
            session_id for session_id, session_data in self.active_sessions.items()
            if session_data["last_active"] < cutoff
        ]
        
        for session_id in expired_sessions:
            self.active_sessions.pop(session_id, None)
        
        return len(expired_sessions)

# Global session manager instance
session_manager = SessionManager()

# Authentication utilities
def is_authenticated_request(request: Request) -> bool:
    """Check if request has valid authentication"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        
        token = auth_header.split(" ")[1]
        azure_auth.verify_token(token)
        return True
    except:
        return False

def get_user_from_request(request: Request) -> Optional[UserProfile]:
    """Extract user from request if authenticated"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        return azure_auth.verify_token(token)
    except:
        return None
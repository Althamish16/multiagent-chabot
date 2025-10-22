# Google OAuth Setup Guide

## 🎯 Quick Setup for Google OAuth Authentication

To enable Google OAuth login for your Multi-Agent Chatbot, follow these steps:

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" or select an existing project
3. Note your Project ID

### Step 2: Enable APIs

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Enable these APIs:
   - **Google+ API** (for user profile)
   - **Gmail API** (for email functionality)
   - **Google Calendar API** (for calendar features)
   - **Google Drive API** (for file operations)

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type
3. Fill in required fields:
   - **App name**: "Multi-Agent Chatbot"
   - **User support email**: Your email
   - **Developer contact**: Your email
4. **Scopes**: Add these scopes:
   - `openid`
   - `profile`
   - `email`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/drive.readonly`

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Set **Authorized redirect URIs**:
   ```
   http://localhost:5000/auth/google/callback
   ```
5. Download the credentials JSON file

### Step 5: Update Environment Variables

Add these to your `backend/.env` file:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

### Step 6: Test the Setup

1. Start your backend: `cd backend && python server.py`
2. Start your frontend: `cd frontend && npm start`
3. Visit `http://localhost:5000`
4. Click "Sign in with Google"

## ✅ Success Indicators

- You should see a Google login popup
- After signing in, you'll be redirected back to your app
- Your profile name and email should appear
- All agents (Email, Calendar, Notes, File) should work

## 🔧 Troubleshooting

### "redirect_uri_mismatch" Error
- Ensure redirect URI in Google Console matches exactly: `http://localhost:5000/auth/google/callback`

### "access_denied" Error
- Check OAuth consent screen is properly configured
- Verify all required scopes are added

### "invalid_client" Error
- Double-check your Client ID and Client Secret in `.env`
- Ensure they match your Google Cloud Console credentials

## 🚀 Production Deployment

For production:
1. Update redirect URI to your production domain
2. Add your production domain to **Authorized domains**
3. Update `.env` with production values
4. Consider using **Internal** user type if within organization

## 📋 Environment Variables Template

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=123456789-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# JWT Configuration  
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
```

## 🎭 Demo Mode

If you don't want to set up Google OAuth immediately, the app falls back to demo mode with:
- Mock authentication
- Simulated API responses
- All features working with sample data

Just leave the Google OAuth variables empty or remove them from `.env`.

---

**Need help?** Check the [Google OAuth 2.0 documentation](https://developers.google.com/identity/protocols/oauth2) for more details.
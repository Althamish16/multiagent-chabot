# 🔐 Authentication System Migration Checklist

Use this checklist to ensure successful migration to the new auth system.

## ✅ Pre-Migration

- [ ] Read `NEW_AUTH_README.md` for overview
- [ ] Have Google OAuth credentials ready (or know how to get them)
- [ ] Have backup of current code (git commit or manual backup)
- [ ] Backend server is stopped
- [ ] Frontend dev server is stopped

## ✅ Step 1: Get Google OAuth Credentials

- [ ] Go to [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Create/select project
- [ ] Enable Google+ API
- [ ] Create OAuth 2.0 Client ID
- [ ] Add redirect URI: `http://localhost:5000/auth/google/callback`
- [ ] Copy Client ID
- [ ] Copy Client Secret

## ✅ Step 2: Update Environment Variables

- [ ] Open/create `backend/.env` file
- [ ] Add `GOOGLE_CLIENT_ID=your-client-id`
- [ ] Add `GOOGLE_CLIENT_SECRET=your-client-secret`
- [ ] Add `GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback`
- [ ] Add `JWT_SECRET=` (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Verify Azure OpenAI keys are present (for AI features)

Your `.env` should look like:
```env
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123...
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
JWT_SECRET=your-generated-secret-key
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=...
```

## ✅ Step 3: Run Migration Script (Recommended)

**Option A: Automatic**
- [ ] Run: `python migrate_auth.py`
- [ ] Verify success messages
- [ ] Check that .backup files were created

**Option B: Manual**
- [ ] Backend: `mv backend/auth_new.py backend/auth.py`
- [ ] Keep `backend/auth_routes.py` as-is
- [ ] Frontend: `mv frontend/src/components/AuthProvider_new.js frontend/src/components/AuthProvider.js`
- [ ] Frontend: `mv frontend/src/components/GoogleCallback_new.js frontend/src/components/GoogleCallback.js`
- [ ] Frontend: `mv frontend/src/components/LoginButton_new.js frontend/src/components/LoginButton.js`

## ✅ Step 4: Update server.py

- [ ] Open `backend/server.py`
- [ ] Open `backend/SERVER_UPDATES.py` as reference
- [ ] Follow each section in SERVER_UPDATES.py

### Section 1: Update imports (around line 30)
- [ ] Replace old google_auth imports with new auth imports
- [ ] Add auth_routes import

### Section 2: Remove old initialization (around line 48)
- [ ] Remove old `google_auth = GoogleOAuth()` block

### Section 3: Add auth router (around line 140)
- [ ] Add `api_router.include_router(auth_router)`

### Section 4: Remove old auth routes (around line 556)
- [ ] Remove old `@api_router.get("/auth/login")`
- [ ] Remove old `@api_router.post("/auth/callback")`
- [ ] Remove old `@api_router.post("/auth/logout")`
- [ ] Remove old `@api_router.get("/auth/me")`

### Section 5: Update OAuth callback (around line 913)
- [ ] Replace `@app.get("/auth/google/callback")` with new version
- [ ] Use `create_callback_html` for responses

## ✅ Step 5: Test Backend

- [ ] Start backend: `cd backend && python server.py`
- [ ] Check console for "✅ Google OAuth authentication loaded"
- [ ] Check for any import errors
- [ ] Open browser: `http://localhost:5000/api/auth/status`
- [ ] Verify: `{"configured": true, "provider": "Google OAuth 2.0", ...}`

## ✅ Step 6: Test Frontend

- [ ] Start frontend: `cd frontend && npm start`
- [ ] Check console for any import errors
- [ ] Check if app loads without errors

## ✅ Step 7: Test Authentication Flow

- [ ] Click "Sign in with Google" button
- [ ] Popup window opens (allow popups if blocked)
- [ ] Google OAuth page loads
- [ ] Sign in with Google account
- [ ] Grant permissions
- [ ] Popup shows "Authentication successful"
- [ ] Popup closes automatically
- [ ] Main window shows user profile
- [ ] User name and email displayed

## ✅ Step 8: Test Protected Features

- [ ] Try sending a message in chat
- [ ] Try uploading a file
- [ ] Try other authenticated features
- [ ] Check browser Network tab - requests include `Authorization` header
- [ ] Verify no auth errors in console

## ✅ Step 9: Test Logout

- [ ] Click logout button
- [ ] User profile disappears
- [ ] Login button reappears
- [ ] Try accessing protected feature - should prompt for login

## ✅ Step 10: Test Error Cases

- [ ] Close popup during OAuth - should show error
- [ ] Try protected endpoint without login - should get 401
- [ ] Invalid token - should prompt for re-login

## ✅ Cleanup (Optional)

After verifying everything works:

- [ ] Remove old backup files (`.backup`)
- [ ] Remove old auth files:
  - `backend/google_auth.py.backup`
  - `frontend/src/components/AuthProvider.js.backup`
  - `frontend/src/components/GoogleCallback.js.backup`
  - `frontend/src/components/LoginButton.js.backup`

## ❌ Rollback (If Needed)

If something goes wrong:

1. [ ] Restore from .backup files:
   ```bash
   # Backend
   mv backend/auth.py.backup backend/google_auth.py
   
   # Frontend
   mv frontend/src/components/AuthProvider.js.backup frontend/src/components/AuthProvider.js
   mv frontend/src/components/GoogleCallback.js.backup frontend/src/components/GoogleCallback.js
   mv frontend/src/components/LoginButton.js.backup frontend/src/components/LoginButton.js
   ```

2. [ ] Restore server.py from git or backup

3. [ ] Restart servers

## 🎉 Success Criteria

Migration is successful when:

- ✅ Backend starts without errors
- ✅ Frontend starts without errors
- ✅ Can login with Google
- ✅ User profile shows after login
- ✅ Can make authenticated API calls
- ✅ Can logout successfully
- ✅ No console errors

## 📝 Notes

Common issues and solutions:

**"Google OAuth not configured"**
- Check GOOGLE_CLIENT_ID in .env
- Restart backend server

**"Popup blocked"**
- Allow popups in browser
- Try Ctrl+Click on login button

**"Module not found"**
- Check file names match exactly
- Check imports in server.py
- Restart servers

**"Token expired"**
- Login again (tokens last 24 hours)
- Normal behavior, not an error

## 📚 Reference Documents

- `NEW_AUTH_README.md` - Complete documentation
- `AUTH_MIGRATION_GUIDE.md` - Detailed migration guide
- `backend/SERVER_UPDATES.py` - Code examples
- `migrate_auth.py` - Automated migration script

---

**After completing this checklist, you'll have a clean, working authentication system! 🚀**

Any issues? Check the troubleshooting section in `NEW_AUTH_README.md`

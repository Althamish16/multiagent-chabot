# How to Test Email API in VS Code

## 🔧 Setup

### 1. Install REST Client Extension
1. Press `Ctrl+Shift+X` to open Extensions
2. Search for **"REST Client"**
3. Install by **Huachao Mao**
4. Reload VS Code if needed

### 2. Get Your JWT Token
You need to authenticate first to get a token:

**Option A: Via Browser**
1. Start your backend: `uvicorn server:app --reload --port 5000`
2. Open browser: `http://localhost:5000/auth/login`
3. Sign in with Google
4. Open Browser DevTools (F12)
5. Go to **Application** tab → **Cookies** → `http://localhost:5000`
6. Find `auth_token` cookie and copy its value

**Option B: Via Console**
1. Sign in via browser
2. Open browser console (F12)
3. Run: `localStorage.getItem('auth_token')` or `document.cookie`
4. Copy the token value

### 3. Update test_email_api.http
1. Open `test_email_api.http`
2. Replace `YOUR_JWT_TOKEN_HERE` with your actual token:
   ```
   @token = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

## 🚀 How to Use REST Client

### Sending Requests
1. Open `test_email_api.http`
2. Place cursor on or above any `###` line
3. Click **"Send Request"** link that appears above the line
4. Or press `Ctrl+Alt+R` (Windows) / `Cmd+Alt+R` (Mac)
5. Results open in new panel on the right

### Reading Results
- **Status Code**: Shows at top (200, 400, 401, 500, etc.)
- **Headers**: Response headers shown
- **Body**: JSON response displayed and formatted
- **Time**: Request duration shown

### Testing Flow

#### Step 1: Test Server
```http
GET http://localhost:5000/api/
```
Expected: 200 OK with server info

#### Step 2: Get Inbox
```http
GET http://localhost:5000/api/email/inbox?max_results=10
Authorization: Bearer YOUR_TOKEN
```
Expected: 200 OK with email list

#### Step 3: Test Chat Interface
```http
POST http://localhost:5000/api/enhanced-chat
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "message": "Show me my latest emails",
  "session_id": "test_123"
}
```
Expected: 200 OK with email agent response

## 📝 Tips

### Variables
Use `@variableName = value` at the top:
```http
@baseUrl = http://localhost:5000
@token = your_token_here

GET {{baseUrl}}/api/email/inbox
Authorization: Bearer {{token}}
```

### Environment Files
Create `.env.local.json` for different environments:
```json
{
  "local": {
    "baseUrl": "http://localhost:5000",
    "token": "local_token_here"
  },
  "dev": {
    "baseUrl": "https://dev-api.example.com",
    "token": "dev_token_here"
  }
}
```

Use: `{{$dotenv baseUrl}}`

### Comments
```http
# This is a comment
### This creates a request separator
```

### Multiple Requests
Separate with `###`:
```http
### Request 1
GET http://localhost:5000/api/email/inbox

### Request 2
GET http://localhost:5000/api/email/drafts/session_123
```

## 🐛 Troubleshooting

### 401 Unauthorized
- Token expired → Sign in again and get new token
- Token missing → Add `Authorization: Bearer {{token}}`
- Token invalid → Check token format (should start with `eyJ`)

### 503 Service Unavailable
- Email agent not loaded → Check backend startup logs
- Missing dependencies → Run `pip install -r requirements.txt`

### 500 Internal Server Error
- Check backend terminal for error details
- Verify Google API enabled in Cloud Console
- Check access token is valid

## 🎯 Alternative: Thunder Client

Another great option (more visual):

1. Install **Thunder Client** extension
2. Click Thunder Client icon in sidebar
3. Create **New Request**
4. Set method (GET/POST/DELETE)
5. Enter URL
6. Add headers: `Authorization: Bearer YOUR_TOKEN`
7. Add body (JSON) for POST requests
8. Click **Send**

## 📊 Other Options

### httpYac
- Similar to REST Client
- More features (OAuth flow, GraphQL)
- Install: Search "httpYac" in extensions

### Insomnia for VS Code
- Postman-like interface
- Install: Search "Insomnia" in extensions

---

## ✅ Quick Start Commands

```bash
# 1. Start backend
cd backend
uvicorn server:app --reload --port 5000

# 2. Sign in via browser
http://localhost:5000/auth/login

# 3. Open test_email_api.http in VS Code

# 4. Update @token variable with your JWT

# 5. Click "Send Request" above any request

# 6. View results in right panel
```

**You're all set to test the Email API!** 🚀

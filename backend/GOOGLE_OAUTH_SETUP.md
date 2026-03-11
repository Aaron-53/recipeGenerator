# Google OAuth Setup Guide

## Prerequisites

1. Google Cloud Console account
2. Created project in Google Cloud Console

## Setup Steps

### 1. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth 2.0 Client ID**
5. Configure OAuth consent screen if not done already
6. Select **Web application** as application type
7. Add authorized redirect URIs:
   - `http://localhost:8000/auth/google/callback` (for local development)
   - Your production callback URL
8. Click **Create**
9. Copy the **Client ID** and **Client Secret**

### 2. Configure Environment Variables

Add to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:3000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## API Endpoints

### Server-Side OAuth Flow (for web apps)

1. **Initiate Login**
   - `GET /auth/google/login`
   - Redirects to Google login page
2. **OAuth Callback**
   - `GET /auth/google/callback`
   - Handles Google callback and redirects to frontend with token

### Client-Side OAuth Flow (for SPAs/Mobile)

1. **Verify Google Token**
   - `POST /auth/google/verify`
   - Body: `{"token": "google-id-token"}`
   - Returns: `{"access_token": "jwt-token", "token_type": "bearer"}`

## Usage Examples

### Server-Side Flow

```javascript
// Frontend: Redirect to backend
window.location.href = "http://localhost:8000/auth/google/login";

// Backend handles OAuth and redirects back to:
// http://localhost:3000/auth/callback?token=jwt-token
```

### Client-Side Flow (React Example)

```javascript
import { GoogleLogin } from "@react-oauth/google";

function LoginButton() {
  const handleSuccess = async (credentialResponse) => {
    const response = await fetch("http://localhost:8000/auth/google/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: credentialResponse.credential }),
    });

    const data = await response.json();
    localStorage.setItem("token", data.access_token);
  };

  return (
    <GoogleLogin
      onSuccess={handleSuccess}
      onError={() => console.log("Login Failed")}
    />
  );
}
```

## User Flow

1. **New User**:
   - Automatically registered with Google email as username
   - No password required (uses Google authentication)
2. **Existing User**:
   - If user exists with same email, links Google account
   - Can login with either Google or username/password

## Security Notes

- Always use HTTPS in production
- Keep client secrets secure (never expose in frontend)
- Validate tokens on backend
- Use secure session storage
- Set appropriate CORS policies

## Troubleshooting

**Error: "Google OAuth not configured"**

- Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`

**Error: "redirect_uri_mismatch"**

- Verify the redirect URI in Google Console matches `GOOGLE_REDIRECT_URI` in `.env`
- Check for trailing slashes

**Error: "Token verification failed"**

- Ensure the token is a valid Google ID token
- Check that client ID matches your Google Cloud project

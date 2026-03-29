from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import RedirectResponse
from datetime import datetime
from schemas.user import UserCreate, UserLogin, UserResponse, Token, GoogleAuth
from utils.auth_utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_from_token,
    validate_password_strength,
)
from utils.google_oauth import oauth, verify_google_token, get_google_user_info
from configs.database import get_collection
from configs import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_user_by_username(username: str):
    """Get user from database by username"""
    users_collection = await get_collection("users")
    user = await users_collection.find_one({"username": username})
    return user


@router.get("/")
async def root():
    """Root endpoint for auth router"""
    return {"message": "Authentication API"}


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def register(user: UserCreate):
    """Register a new user"""

    # Validate password strength
    if not validate_password_strength(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, and digit",
        )

    # Check if username already exists
    existing_user = await get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create new user
    users_collection = await get_collection("users")
    hashed_password = get_password_hash(user.password)

    user_dict = {
        "username": user.username,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }

    result = await users_collection.insert_one(user_dict)

    return UserResponse(
        user_id=str(result.inserted_id),
        username=user.username,
        is_active=True,
        created_at=user_dict["created_at"],
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user and return access token"""

    # Get user from database
    user = await get_user_by_username(credentials.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": str(user["_id"])}
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user_from_token)):
    """Logout user"""
    # For stateless JWT, logout is handled client-side by removing the token
    # If you need server-side token blacklisting, implement it here
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_user_from_token)):
    """Get current user information"""

    # Get full user details from database
    users_collection = await get_collection("users")
    user = await users_collection.find_one({"username": current_user["username"]})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        user_id=str(user["_id"]),
        username=user["username"],
        is_active=user.get("is_active", True),
        created_at=user["created_at"],
    )


@router.get("/verify-token")
async def verify_token_endpoint(
    current_user: dict = Depends(get_current_user_from_token),
):
    """Verify if the provided token is valid"""
    return {
        "valid": True,
        "username": current_user["username"],
        "user_id": current_user["user_id"],
    }


# Google OAuth Endpoints


def _google_oauth_redirect_uri(request: Request) -> str:
    """Callback URL matching this request’s host/port so the session cookie matches Google’s redirect."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/google/callback"


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth flow"""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI or _google_oauth_redirect_uri(request)
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        # Get the authorization token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            user_info = await get_google_user_info(token["access_token"])

        # Extract user data
        google_id = user_info.get("sub") or user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0])
        picture = user_info.get("picture")

        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to get required user information from Google",
            )

        # Check if user exists by google_id or email
        users_collection = await get_collection("users")
        user = await users_collection.find_one(
            {"$or": [{"google_id": google_id}, {"username": email}]}
        )

        if user:
            # Update existing user with Google info if needed
            if not user.get("google_id"):
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"google_id": google_id, "picture": picture}},
                )
        else:
            # Create new user
            user_dict = {
                "username": email,
                "google_id": google_id,
                "name": name,
                "picture": picture,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "auth_provider": "google",
            }
            result = await users_collection.insert_one(user_dict)
            user = await users_collection.find_one({"_id": result.inserted_id})

        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": str(user["_id"])}
        )

        # Redirect to frontend with token
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )


@router.post("/google/verify", response_model=Token)
async def verify_google_token_endpoint(auth_data: GoogleAuth):
    """Verify Google ID token and login/register user"""
    try:
        # Verify the Google token
        user_info = await verify_google_token(auth_data.token)

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0] if email else "User")
        picture = user_info.get("picture")

        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to get required user information from Google token",
            )

        # Check if user exists
        users_collection = await get_collection("users")
        user = await users_collection.find_one(
            {"$or": [{"google_id": google_id}, {"username": email}]}
        )

        if user:
            # Update existing user with Google info if needed
            if not user.get("google_id"):
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"google_id": google_id, "picture": picture}},
                )
        else:
            # Create new user
            user_dict = {
                "username": email,
                "google_id": google_id,
                "name": name,
                "picture": picture,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "auth_provider": "google",
            }
            result = await users_collection.insert_one(user_dict)
            user = await users_collection.find_one({"_id": result.inserted_id})

        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": str(user["_id"])}
        )

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token verification failed: {str(e)}",
        )

from fastapi import APIRouter, HTTPException, status
from gotrue.errors import AuthApiError
from pydantic import BaseModel, EmailStr

from ..dependencies import CurrentUser, SupabaseClient

router = APIRouter()


class SignupRequest(BaseModel):
    """Request body for user signup."""

    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response for successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """Current user information with credit balance."""

    id: str
    email: str | None
    credit_balance: int


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, supabase: SupabaseClient):
    """Create a new user account.

    Proxies to Supabase Auth and initializes credit balance.
    """
    try:
        response = supabase.auth.sign_up({"email": request.email, "password": request.password})

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed - user not created",
            )

        if response.session is None:
            # Email confirmation required
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Please check your email to confirm your account",
            )

        # Initialize credits for new user
        supabase.table("credits").insert({"user_id": response.user.id, "balance": 0}).execute()

        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
        )

    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, supabase: SupabaseClient):
    """Authenticate user and return session tokens."""
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
        )

    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post("/logout")
async def logout(user: CurrentUser, supabase: SupabaseClient):
    """End the current user session.

    Note: This invalidates the refresh token on Supabase side.
    The access token will remain valid until expiration.
    """
    try:
        supabase.auth.admin.sign_out(user.id)
        return {"message": "Logged out successfully"}
    except AuthApiError as e:
        # Log error but don't fail - user wanted to logout
        return {"message": "Logged out", "warning": str(e)}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(user: CurrentUser, supabase: SupabaseClient):
    """Get current user information including credit balance."""
    # Fetch credit balance
    result = supabase.table("credits").select("balance").eq("user_id", user.id).execute()

    balance = 0
    if result.data:
        balance = result.data[0].get("balance", 0)
    else:
        # Initialize credits if not exists (edge case)
        supabase.table("credits").insert({"user_id": user.id, "balance": 0}).execute()

    return UserInfo(
        id=user.id,
        email=user.email,
        credit_balance=balance,
    )

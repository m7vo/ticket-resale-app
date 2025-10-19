"""
Authentication Routes
=====================

These endpoints handle user registration, login, and token management.

ENDPOINTS:
- POST /api/auth/signup — Create a new user account
- POST /api/auth/login — Login and get access token
- POST /api/auth/logout — Logout (optional, tokens expire automatically)
- GET /api/auth/verify-email/{token} — Verify email address

WHY WE NEED THIS:
- Users need to create accounts (signup)
- Users need to login to get a token (to make authenticated requests)
- Tokens prove "you are who you say you are" without storing passwords everywhere
- Email verification prevents fake accounts

HOW JWT TOKENS WORK:
1. User signs up with email/password
2. We hash the password (never store plain passwords!)
3. User logs in with email/password
4. We verify password, then create a JWT token
5. User includes token in future requests
6. We verify token without querying database every time
7. Token expires after 30 minutes for security
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import secrets

# Import models and config
from models import Base, User, UserProfile
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, DATABASE_URL

# Create engine and SessionLocal (same as in app.py)
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# SECURITY SETUP
# ============================================================================

# Password hashing context
# This uses bcrypt to securely hash passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create router
# This groups all auth endpoints together under /api/auth
router = APIRouter()

# ============================================================================
# PYDANTIC SCHEMAS (Request/Response models)
# ============================================================================
# These define what data the API expects and returns
# Think of them as contracts: "If you send this, you get that back"

class UserSignupRequest(BaseModel):
    """What the user sends when signing up"""
    username: str  # e.g., "alice123"
    email: EmailStr  # Validated email format
    password: str  # At least 8 characters (you should add validation)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "alice123",
                "email": "alice@example.com",
                "password": "securepass123"
            }
        }

class UserLoginRequest(BaseModel):
    """What the user sends when logging in"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "alice@example.com",
                "password": "securepass123"
            }
        }

class UserResponse(BaseModel):
    """What we send back to the user (never include password!)"""
    id: int
    username: str
    email: str
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Read from SQLAlchemy models

class TokenResponse(BaseModel):
    """What we send back after successful login"""
    access_token: str  # The JWT token
    token_type: str  # Always "bearer"
    user: UserResponse  # User info

class VerificationEmailRequest(BaseModel):
    """Request to resend verification email"""
    email: EmailStr

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    WHY: Never store plain passwords! If database is hacked, attackers
    can't immediately use those passwords.
    
    bcrypt is slow on purpose — makes brute force attacks harder.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plain password matches the hashed version.
    
    Used during login:
    1. User sends plain password
    2. We get hashed password from database
    3. We check if they match (without ever storing the plain password)
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
    """
    Create a JWT token that proves the user is logged in.
    
    JWT = JSON Web Token
    It's like a ticket that says "User 5 is logged in, valid until 3pm"
    
    The token is SIGNED with SECRET_KEY, so we can verify nobody tampered with it.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Payload = the data inside the token
    payload = {
        "user_id": user_id,
        "exp": expire  # Expiration time
    }
    
    # Encode = create the token
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_email_verification_token() -> str:
    """
    Generate a random token for email verification.
    
    When user signs up:
    1. Create random token
    2. Save it to database
    3. Send email with link: http://localhost:3000/verify?token=xyz123
    4. User clicks link
    5. We check if token exists and mark user as verified
    """
    return secrets.token_urlsafe(32)

# ============================================================================
# DEPENDENCY: Get current user from token
# ============================================================================

async def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Dependency that extracts user from JWT token in Authorization header.
    
    Header format: Authorization: Bearer <token>
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization:
        raise credentials_exception
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise credentials_exception
    except ValueError:
        raise credentials_exception
    
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    return user

# ============================================================================
# ROUTES
# ============================================================================

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: UserSignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Flow:
    1. Check if username/email already exists
    2. Hash password
    3. Create user in database
    4. Create user profile
    5. Generate verification token (for email verification)
    6. Create JWT token (for immediate login)
    7. Return token + user info
    
    TODO: Send verification email with token
    """
    
    # Check if username exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password (NEVER store plain passwords!)
    hashed_password = hash_password(request.password)
    
    # Create user
    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=hashed_password,
        is_verified=False  # User must verify email
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Get the ID that was auto-generated
    
    # Create user profile
    user_profile = UserProfile(user_id=new_user.id)
    db.add(user_profile)
    db.commit()
    
    # TODO: Generate verification token and send email
    # verification_token = generate_email_verification_token()
    # Save token to database (you'll need to add a field to User model)
    # Send email with verification link
    
    # Create and return JWT token
    access_token = create_access_token(user_id=new_user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(new_user)
    )

@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login and get access token.
    
    Flow:
    1. Find user by email
    2. Verify password matches
    3. Create JWT token
    4. Return token + user info
    
    Client will use this token in future requests like:
    Authorization: Bearer <token>
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    # If user doesn't exist or password is wrong, don't tell which one
    # (security: don't reveal whether email is registered)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token = create_access_token(user_id=user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user's info.
    
    Requires: Authorization header with JWT token
    
    Example:
    Headers: Authorization: Bearer <token>
    
    Returns: Current user info
    
    This endpoint is PROTECTED — only works if you have a valid token.
    """
    return UserResponse.from_orm(current_user)

@router.post("/logout")
def logout():
    """
    Logout endpoint.
    
    NOTE: With JWT, logout is mainly a frontend thing.
    - Client just deletes the token from localStorage
    - Token expires automatically after 30 minutes
    
    This endpoint exists for API completeness.
    """
    return {"message": "Successfully logged out"}

# ============================================================================
# ERROR HANDLING
# ============================================================================
# These are automatically used by FastAPI when errors occur

@router.get("/token")
def get_token_info(current_user: User = Depends(get_current_user)):
    """
    Debug endpoint to verify current token.
    Only works if token is valid.
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }
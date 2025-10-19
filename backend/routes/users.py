"""
Users/Profiles Routes
=====================

These endpoints handle user profiles, ratings, and seller verification.

ENDPOINTS:
- GET /api/users/{user_id} — Get user profile
- PUT /api/users/me — Update current user profile
- GET /api/users/me/profile — Get current user profile
- POST /api/users/{user_id}/reviews — Leave a review for seller
- GET /api/users/{user_id}/reviews — Get reviews for a user
- POST /api/users/me/proof — Upload seller proof (past sales)
- GET /api/users/{user_id}/proof — Get seller proof images
- GET /api/users/search — Search users by username

FEATURES:
- View seller profiles with ratings
- Leave ratings/reviews for sellers
- Upload proof of past sales
- See seller trust scores
- Search for sellers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Import models and dependencies
from models import User, UserProfile, Review, SellerProof, Listing
from routes.auth import get_db, get_current_user

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class UserProfileUpdateRequest(BaseModel):
    """Data to update user profile"""
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "bio": "Concert enthusiast! Selling extra tickets.",
                "profile_picture_url": "https://example.com/photo.jpg"
            }
        }

class ReviewCreateRequest(BaseModel):
    """Data to create a review"""
    listing_id: Optional[int] = None  # Which transaction is this for?
    rating: int  # 1-5 stars
    comment: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "listing_id": 42,
                "rating": 5,
                "comment": "Great seller! Fast communication, legitimate tickets."
            }
        }

class ReviewResponse(BaseModel):
    """Review data"""
    id: int
    reviewer_id: int
    reviewer_username: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SellerProofResponse(BaseModel):
    """Seller proof of past sales"""
    id: int
    proof_image_url: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    """Full user profile with stats"""
    id: int
    username: str
    email: str
    bio: Optional[str]
    profile_picture_url: Optional[str]
    total_sales: int
    average_rating: float
    is_verified_seller: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserPublicProfileResponse(BaseModel):
    """Public user profile (no email, no private info)"""
    id: int
    username: str
    bio: Optional[str]
    profile_picture_url: Optional[str]
    total_sales: int
    average_rating: float
    is_verified_seller: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SellerProofCreateRequest(BaseModel):
    """Data to upload seller proof"""
    proof_image_url: str  # URL of screenshot
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "proof_image_url": "https://example.com/proof.jpg",
                "description": "Sold 2 Taylor Swift tickets on Ticketmaster"
            }
        }

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter()

# ============================================================================
# GET USER PROFILE (Public)
# ============================================================================

@router.get("/{user_id}", response_model=UserPublicProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """
    Get public profile of a user.
    
    Shows:
    - Username, bio, profile picture
    - Total sales, average rating
    - Verified seller status
    
    Does NOT show:
    - Email address
    - Private profile info
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get profile stats
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "bio": profile.bio,
        "profile_picture_url": profile.profile_picture_url,
        "total_sales": profile.total_sales,
        "average_rating": profile.average_rating,
        "is_verified_seller": profile.is_verified_seller,
        "created_at": user.created_at
    }

# ============================================================================
# GET CURRENT USER PROFILE (Private)
# ============================================================================

@router.get("/me/profile", response_model=UserProfileResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's full profile (with private info).
    
    REQUIRES: Valid JWT token
    
    Shows everything including email address.
    """
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "bio": profile.bio,
        "profile_picture_url": profile.profile_picture_url,
        "total_sales": profile.total_sales,
        "average_rating": profile.average_rating,
        "is_verified_seller": profile.is_verified_seller,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at
    }

# ============================================================================
# UPDATE CURRENT USER PROFILE
# ============================================================================

@router.put("/me", response_model=UserProfileResponse)
def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    REQUIRES: Valid JWT token
    
    Can update:
    - bio (description)
    - profile_picture_url (link to photo)
    """
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update fields if provided
    if request.bio is not None:
        profile.bio = request.bio
    
    if request.profile_picture_url is not None:
        profile.profile_picture_url = request.profile_picture_url
    
    profile.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(profile)
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "bio": profile.bio,
        "profile_picture_url": profile.profile_picture_url,
        "total_sales": profile.total_sales,
        "average_rating": profile.average_rating,
        "is_verified_seller": profile.is_verified_seller,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at
    }

# ============================================================================
# LEAVE REVIEW FOR SELLER
# ============================================================================

@router.post("/{user_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    user_id: int,
    request: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Leave a review/rating for a seller.
    
    REQUIRES: Valid JWT token
    
    Flow:
    1. Validate rating is 1-5
    2. Validate seller exists
    3. Create review
    4. Update seller's average rating
    
    Use case: After buying tickets from seller, leave review.
    """
    
    # Can't review yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot review yourself"
        )
    
    # Validate rating
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Check if seller exists
    seller = db.query(User).filter(User.id == user_id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found"
        )
    
    # If listing_id provided, verify it exists
    if request.listing_id:
        listing = db.query(Listing).filter(Listing.id == request.listing_id).first()
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"
            )
    
    # Create review
    new_review = Review(
        reviewer_id=current_user.id,
        reviewed_user_id=user_id,
        listing_id=request.listing_id,
        rating=request.rating,
        comment=request.comment
    )
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    # Update seller's average rating
    update_seller_rating(user_id, db)
    
    return {
        "id": new_review.id,
        "reviewer_id": current_user.id,
        "reviewer_username": current_user.username,
        "rating": new_review.rating,
        "comment": new_review.comment,
        "created_at": new_review.created_at
    }

# ============================================================================
# GET REVIEWS FOR USER
# ============================================================================

@router.get("/{user_id}/reviews", response_model=List[ReviewResponse])
def get_user_reviews(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a user (seller).
    
    Shows:
    - Reviewer username
    - Rating (1-5)
    - Comment
    - Date
    
    Paginated, newest first.
    """
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    reviews = db.query(Review).filter(
        Review.reviewed_user_id == user_id
    ).order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    # Add reviewer username to each review
    result = []
    for review in reviews:
        reviewer = db.query(User).filter(User.id == review.reviewer_id).first()
        result.append({
            "id": review.id,
            "reviewer_id": review.reviewer_id,
            "reviewer_username": reviewer.username if reviewer else "Unknown",
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at
        })
    
    return result

# ============================================================================
# UPLOAD SELLER PROOF
# ============================================================================

@router.post("/me/proof", response_model=SellerProofResponse, status_code=status.HTTP_201_CREATED)
def upload_seller_proof(
    request: SellerProofCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload proof of past sales to build seller credibility.
    
    REQUIRES: Valid JWT token
    
    Proof should be:
    - Screenshot of Ticketmaster/AXS confirmation
    - Screenshot of past positive review
    - Any evidence of legitimate past sales
    
    Helps new sellers build trust.
    """
    
    new_proof = SellerProof(
        seller_id=current_user.id,
        proof_image_url=request.proof_image_url,
        description=request.description
    )
    
    db.add(new_proof)
    db.commit()
    db.refresh(new_proof)
    
    return {
        "id": new_proof.id,
        "proof_image_url": new_proof.proof_image_url,
        "description": new_proof.description,
        "created_at": new_proof.created_at
    }

# ============================================================================
# GET SELLER PROOF
# ============================================================================

@router.get("/{user_id}/proof", response_model=List[SellerProofResponse])
def get_seller_proof(user_id: int, db: Session = Depends(get_db)):
    """
    Get all proof images for a seller.
    
    Shows evidence of past legitimate sales.
    Helps buyers verify seller credibility.
    """
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    proof_images = db.query(SellerProof).filter(
        SellerProof.seller_id == user_id
    ).order_by(SellerProof.created_at.desc()).all()
    
    return proof_images

# ============================================================================
# SEARCH USERS
# ============================================================================

@router.get("/search", response_model=List[UserPublicProfileResponse])
def search_users(
    query: str = Query(..., min_length=1, max_length=50, description="Search by username"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    verified_only: bool = Query(False, description="Only verified sellers"),
    db: Session = Depends(get_db)
):
    """
    Search for users by username.
    
    FILTERS:
    - query: Search term (case-insensitive)
    - verified_only: Only return verified sellers
    
    Returns public profile info.
    """
    
    search_term = f"%{query}%"
    
    user_query = db.query(User).filter(
        User.username.ilike(search_term)
    )
    
    # Filter by verified sellers
    if verified_only:
        user_query = user_query.join(UserProfile).filter(
            UserProfile.is_verified_seller == True
        )
    
    users = user_query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        result.append({
            "id": user.id,
            "username": user.username,
            "bio": profile.bio if profile else None,
            "profile_picture_url": profile.profile_picture_url if profile else None,
            "total_sales": profile.total_sales if profile else 0,
            "average_rating": profile.average_rating if profile else 0,
            "is_verified_seller": profile.is_verified_seller if profile else False,
            "created_at": user.created_at
        })
    
    return result

# ============================================================================
# HELPER FUNCTION
# ============================================================================

def update_seller_rating(user_id: int, db: Session):
    """
    Calculate and update seller's average rating based on all reviews.
    
    Called after each new review is added.
    """
    
    # Get average rating from all reviews
    avg_rating = db.query(func.avg(Review.rating)).filter(
        Review.reviewed_user_id == user_id
    ).scalar()
    
    # Get profile and update
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if profile:
        profile.average_rating = float(avg_rating) if avg_rating else 0
        
        # Auto-verify as seller if enough ratings
        review_count = db.query(Review).filter(
            Review.reviewed_user_id == user_id
        ).count()
        
        if review_count >= 5 and profile.average_rating >= 4.5:
            profile.is_verified_seller = True
        
        profile.updated_at = datetime.utcnow()
        db.commit()
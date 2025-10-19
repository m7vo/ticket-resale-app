"""
Listings Routes
===============

These endpoints handle ticket listings (buying/selling).

ENDPOINTS:
- POST /api/listings — Create a new listing (seller creates ticket for sale)
- GET /api/listings — Get all listings with filters/search
- GET /api/listings/{listing_id} — Get single listing details
- PUT /api/listings/{listing_id} — Update listing (only by seller)
- DELETE /api/listings/{listing_id} — Delete listing (only by seller)
- GET /api/listings/user/{user_id} — Get all listings by a user

FILTERS:
- artist_name — Search by artist
- min_price / max_price — Price range
- concert_date — Date range
- section — Stadium section
- verified_seller_only — Only show verified sellers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

# Import models and dependencies
from models import User, Listing, UserProfile
from routes.auth import get_db, get_current_user

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ListingCreateRequest(BaseModel):
    """Data to create a new listing"""
    artist_name: str
    concert_date: date
    venue_name: str
    section: Optional[str] = None
    row: Optional[str] = None
    seat_number: Optional[str] = None
    price: float  # Price in dollars
    quantity_available: int = 1
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "artist_name": "Taylor Swift",
                "concert_date": "2024-12-15",
                "venue_name": "SoFi Stadium",
                "section": "Floor A",
                "row": "12",
                "seat_number": "5",
                "price": 150.50,
                "quantity_available": 1,
                "description": "Great view of the stage!"
            }
        }

class ListingUpdateRequest(BaseModel):
    """Data to update a listing"""
    price: Optional[float] = None
    quantity_available: Optional[int] = None
    description: Optional[str] = None
    is_available: Optional[bool] = None

class SellerInfo(BaseModel):
    """Seller info shown on listing"""
    id: int
    username: str
    total_sales: int
    average_rating: float
    is_verified_seller: bool
    
    class Config:
        from_attributes = True

class ListingResponse(BaseModel):
    """Full listing with seller info"""
    id: int
    artist_name: str
    concert_date: date
    venue_name: str
    section: Optional[str]
    row: Optional[str]
    seat_number: Optional[str]
    price: float
    quantity_available: int
    description: Optional[str]
    is_available: bool
    created_at: datetime
    updated_at: datetime
    seller: SellerInfo  # Nested seller info
    
    class Config:
        from_attributes = True

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter()

# ============================================================================
# CREATE LISTING
# ============================================================================

@router.post("/", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    request: ListingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new ticket listing.
    
    REQUIRES: Valid JWT token (user must be logged in)
    
    Flow:
    1. Validate concert date is in the future
    2. Create listing in database
    3. Return listing details with seller info
    
    Only logged-in users can create listings.
    """
    
    # Validate concert date is in future
    if request.concert_date <= date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Concert date must be in the future"
        )
    
    # Validate price is positive
    if request.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be greater than 0"
        )
    
    # Validate quantity is positive
    if request.quantity_available <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be at least 1"
        )
    
    # Create listing
    new_listing = Listing(
        seller_id=current_user.id,
        artist_name=request.artist_name,
        concert_date=request.concert_date,
        venue_name=request.venue_name,
        section=request.section,
        row=request.row,
        seat_number=request.seat_number,
        price=request.price,
        quantity_available=request.quantity_available,
        description=request.description,
        is_available=True
    )
    
    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    
    return new_listing

# ============================================================================
# GET ALL LISTINGS (with filters)
# ============================================================================

@router.get("/", response_model=List[ListingResponse])
def get_listings(
    artist_name: Optional[str] = Query(None, description="Search by artist name"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    venue_name: Optional[str] = Query(None, description="Search by venue"),
    section: Optional[str] = Query(None, description="Filter by section"),
    concert_date_from: Optional[date] = Query(None, description="Concert date from"),
    concert_date_to: Optional[date] = Query(None, description="Concert date to"),
    verified_seller_only: bool = Query(False, description="Only show verified sellers"),
    is_available: bool = Query(True, description="Only show available listings"),
    skip: int = Query(0, ge=0, description="Skip N listings (for pagination)"),
    limit: int = Query(10, ge=1, le=100, description="Return max N listings"),
    db: Session = Depends(get_db)
):
    """
    Get all ticket listings with optional filters.
    
    FILTERS:
    - artist_name: Search by artist (case-insensitive partial match)
    - min_price / max_price: Price range
    - venue_name: Filter by venue
    - section: Filter by stadium section
    - concert_date_from / concert_date_to: Date range
    - verified_seller_only: Only show verified sellers
    - is_available: Only available listings
    
    PAGINATION:
    - skip: How many to skip (for loading more)
    - limit: How many to return (max 100)
    
    Example:
    GET /api/listings?artist_name=Taylor&min_price=100&max_price=200
    """
    
    # Start with base query
    query = db.query(Listing)
    
    # Filter by availability
    query = query.filter(Listing.is_available == is_available)
    
    # Filter by artist name (case-insensitive contains)
    if artist_name:
        query = query.filter(Listing.artist_name.ilike(f"%{artist_name}%"))
    
    # Filter by venue (case-insensitive contains)
    if venue_name:
        query = query.filter(Listing.venue_name.ilike(f"%{venue_name}%"))
    
    # Filter by section
    if section:
        query = query.filter(Listing.section == section)
    
    # Filter by price range
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)
    
    # Filter by concert date range
    if concert_date_from:
        query = query.filter(Listing.concert_date >= concert_date_from)
    if concert_date_to:
        query = query.filter(Listing.concert_date <= concert_date_to)
    
    # Filter by verified seller only
    if verified_seller_only:
        query = query.join(User).join(UserProfile).filter(
            UserProfile.is_verified_seller == True
        )
    
    # Sort by date (oldest first)
    query = query.order_by(Listing.concert_date.asc())
    
    # Pagination
    total = query.count()
    listings = query.offset(skip).limit(limit).all()
    
    return listings

# ============================================================================
# GET SINGLE LISTING
# ============================================================================

@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """
    Get details of a single listing.
    
    Returns listing with seller information.
    """
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found"
        )
    
    return listing

# ============================================================================
# UPDATE LISTING
# ============================================================================

@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(
    listing_id: int,
    request: ListingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a listing (only seller can update their own listing).
    
    Can update:
    - price
    - quantity_available
    - description
    - is_available (mark as sold/unavailable)
    """
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    # Check if current user is the seller
    if listing.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own listings"
        )
    
    # Update fields if provided
    if request.price is not None:
        if request.price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be greater than 0"
            )
        listing.price = request.price
    
    if request.quantity_available is not None:
        if request.quantity_available < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot be negative"
            )
        listing.quantity_available = request.quantity_available
    
    if request.description is not None:
        listing.description = request.description
    
    if request.is_available is not None:
        listing.is_available = request.is_available
    
    # Update timestamp
    listing.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(listing)
    
    return listing

# ============================================================================
# DELETE LISTING
# ============================================================================

@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a listing (only seller can delete).
    
    Returns 204 No Content on success.
    """
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    # Check if current user is the seller
    if listing.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own listings"
        )
    
    db.delete(listing)
    db.commit()
    
    return None

# ============================================================================
# GET LISTINGS BY SELLER
# ============================================================================

@router.get("/seller/{seller_id}", response_model=List[ListingResponse])
def get_seller_listings(
    seller_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all listings by a specific seller.
    
    Useful for viewing a seller's profile and their tickets.
    """
    
    # Check if seller exists
    seller = db.query(User).filter(User.id == seller_id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found"
        )
    
    listings = db.query(Listing).filter(
        Listing.seller_id == seller_id,
        Listing.is_available == True
    ).order_by(Listing.concert_date.asc()).all()
    
    return listings
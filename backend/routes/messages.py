"""
Messages Routes
===============

These endpoints handle direct messaging between buyers and sellers.

ENDPOINTS:
- POST /api/messages — Send a message
- GET /api/messages — Get all messages for current user
- GET /api/messages/conversation/{user_id} — Get conversation with specific user
- GET /api/messages/{message_id} — Get single message
- PUT /api/messages/{message_id}/read — Mark message as read
- DELETE /api/messages/{message_id} — Delete a message

FEATURES:
- Direct messages about listings
- Mark messages as read/unread
- View conversations with other users
- See all messages you've sent/received
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Import models and dependencies
from models import User, Message, Listing
from routes.auth import get_db, get_current_user

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class MessageCreateRequest(BaseModel):
    """Data to send a message"""
    receiver_id: int  # Who to send message to
    message_text: str  # The message content
    listing_id: Optional[int] = None  # Which listing is this about?
    
    class Config:
        json_schema_extra = {
            "example": {
                "receiver_id": 5,
                "message_text": "Is this ticket still available? Can we do $140?",
                "listing_id": 12
            }
        }

class MessageResponse(BaseModel):
    """Message data returned to user"""
    id: int
    sender_id: int
    receiver_id: int
    listing_id: Optional[int]
    message_text: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageDetailResponse(MessageResponse):
    """Message with sender/receiver info"""
    sender: Optional[dict]  # Sender's username
    receiver: Optional[dict]  # Receiver's username
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    """Summary of conversation with another user"""
    other_user_id: int
    other_user_username: str
    last_message: str
    last_message_time: datetime
    unread_count: int
    
    class Config:
        from_attributes = True

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter()

# ============================================================================
# SEND MESSAGE
# ============================================================================

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a direct message to another user.
    
    REQUIRES: Valid JWT token (must be logged in)
    
    Flow:
    1. Validate receiver exists
    2. Validate listing exists (if provided)
    3. Create message
    4. Return message details
    
    Use case: Buyer messages seller about a listing
    """
    
    # Can't send message to yourself
    if request.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )
    
    # Check if receiver exists
    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    # If listing_id provided, verify it exists
    if request.listing_id:
        listing = db.query(Listing).filter(Listing.id == request.listing_id).first()
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"
            )
    
    # Validate message is not empty
    if not request.message_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )
    
    # Create message
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=request.receiver_id,
        listing_id=request.listing_id,
        message_text=request.message_text,
        is_read=False
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message

# ============================================================================
# GET ALL MESSAGES
# ============================================================================

@router.get("/", response_model=List[MessageResponse])
def get_all_messages(
    unread_only: bool = Query(False, description="Only unread messages"),
    skip: int = Query(0, ge=0, description="Skip N messages"),
    limit: int = Query(20, ge=1, le=100, description="Return max N messages"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for current user (sent or received).
    
    FILTERS:
    - unread_only: Only return unread messages
    
    PAGINATION:
    - skip: How many to skip
    - limit: How many to return
    
    Returns messages ordered by newest first.
    """
    
    # Get messages where user is either sender or receiver
    query = db.query(Message).filter(
        or_(
            Message.sender_id == current_user.id,
            Message.receiver_id == current_user.id
        )
    )
    
    # Filter by unread
    if unread_only:
        query = query.filter(
            and_(
                Message.receiver_id == current_user.id,
                Message.is_read == False
            )
        )
    
    # Sort by newest first
    messages = query.order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    
    return messages

# ============================================================================
# GET CONVERSATION WITH USER
# ============================================================================

@router.get("/conversation/{other_user_id}", response_model=List[MessageResponse])
def get_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages in a conversation with another user.
    
    Returns all messages between current user and other_user,
    ordered chronologically (oldest first).
    
    Also marks all unread messages as read.
    """
    
    # Check if other user exists
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get all messages between these two users
    messages = db.query(Message).filter(
        or_(
            and_(
                Message.sender_id == current_user.id,
                Message.receiver_id == other_user_id
            ),
            and_(
                Message.sender_id == other_user_id,
                Message.receiver_id == current_user.id
            )
        )
    ).order_by(Message.created_at.asc()).all()
    
    # Mark all messages received by current user as read
    unread_messages = db.query(Message).filter(
        and_(
            Message.sender_id == other_user_id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        )
    ).all()
    
    for msg in unread_messages:
        msg.is_read = True
    
    db.commit()
    
    return messages

# ============================================================================
# GET SINGLE MESSAGE
# ============================================================================

@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single message by ID.
    
    Only sender or receiver can view the message.
    Automatically marks as read if receiver.
    """
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if user is sender or receiver
    if message.sender_id != current_user.id and message.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own messages"
        )
    
    # Mark as read if receiver
    if message.receiver_id == current_user.id and not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)
    
    return message

# ============================================================================
# MARK MESSAGE AS READ
# ============================================================================

@router.put("/{message_id}/read", response_model=MessageResponse)
def mark_as_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a message as read.
    
    Only receiver can mark as read.
    """
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if user is receiver
    if message.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only receiver can mark message as read"
        )
    
    message.is_read = True
    db.commit()
    db.refresh(message)
    
    return message

# ============================================================================
# DELETE MESSAGE
# ============================================================================

@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message.
    
    Only sender or receiver can delete.
    """
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if user is sender or receiver
    if message.sender_id != current_user.id and message.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages"
        )
    
    db.delete(message)
    db.commit()
    
    return None

# ============================================================================
# GET UNREAD COUNT
# ============================================================================

@router.get("/stats/unread-count", response_model=dict)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get count of unread messages for current user.
    
    Useful for showing notification badge.
    """
    
    unread_count = db.query(Message).filter(
        and_(
            Message.receiver_id == current_user.id,
            Message.is_read == False
        )
    ).count()
    
    return {"unread_count": unread_count}

# ============================================================================
# GET CONVERSATIONS LIST
# ============================================================================

@router.get("/conversations/list", response_model=List[dict])
def get_conversations_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all active conversations with other users.
    
    Returns:
    - User info
    - Last message preview
    - Timestamp of last message
    - Unread message count
    
    Useful for displaying a chat/inbox interface.
    """
    
    # Get all users the current user has messaged with
    query = db.query(
        Message.sender_id,
        Message.receiver_id
    ).filter(
        or_(
            Message.sender_id == current_user.id,
            Message.receiver_id == current_user.id
        )
    ).all()
    
    # Collect unique user IDs (excluding current user)
    user_ids = set()
    for sender_id, receiver_id in query:
        if sender_id != current_user.id:
            user_ids.add(sender_id)
        if receiver_id != current_user.id:
            user_ids.add(receiver_id)
    
    conversations = []
    
    for user_id in user_ids:
        # Get last message with this user
        last_message = db.query(Message).filter(
            or_(
                and_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == user_id
                ),
                and_(
                    Message.sender_id == user_id,
                    Message.receiver_id == current_user.id
                )
            )
        ).order_by(Message.created_at.desc()).first()
        
        # Count unread messages from this user
        unread_count = db.query(Message).filter(
            and_(
                Message.sender_id == user_id,
                Message.receiver_id == current_user.id,
                Message.is_read == False
            )
        ).count()
        
        other_user = db.query(User).filter(User.id == user_id).first()
        
        conversations.append({
            "user_id": user_id,
            "username": other_user.username,
            "last_message": last_message.message_text if last_message else "",
            "last_message_time": last_message.created_at if last_message else None,
            "unread_count": unread_count
        })
    
    # Sort by last message time (newest first)
    conversations.sort(
        key=lambda x: x["last_message_time"] or datetime.min,
        reverse=True
    )
    
    return conversations
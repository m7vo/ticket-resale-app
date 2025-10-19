"""
User Model
==========

Represents a user in the system (buyer or seller).

Database table: users
Columns: id, username, email, password_hash, is_verified, created_at, updated_at
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey 
from sqlalchemy.orm import relationship 
from datetime import datetime
from models import Base

class User(Base):
    __tablename__ = "users"
    
    # Primary Key - Unique ID for each user
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Never store plain passwords!
    
    # Email verification
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (links to other tables)
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="seller", cascade="all, delete-orphan")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    reviews_given = relationship("Review", foreign_keys="Review.reviewer_id", back_populates="reviewer")
    reviews_received = relationship("Review", foreign_keys="Review.reviewed_user_id", back_populates="reviewed_user")
    proof_images = relationship("SellerProof", back_populates="seller", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to users table
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Profile information
    bio = Column(String(500), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    
    # Seller stats
    total_sales = Column(Integer, default=0)
    is_verified_seller = Column(Boolean, default=False)
    average_rating = Column(Integer, default=0)  # Will calculate from reviews
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to User
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, total_sales={self.total_sales})>"

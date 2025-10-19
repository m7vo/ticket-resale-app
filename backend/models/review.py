"""
Review Model
============

Represents a review/rating left by a buyer for a seller.

Database table: reviews
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewed_user = relationship("User", foreign_keys=[reviewed_user_id], back_populates="reviews_received")
    listing = relationship("Listing", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.id}, rating={self.rating}, reviewer={self.reviewer_id})>"
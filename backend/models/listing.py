"""
Listing Model
=============

Represents a ticket listing (a ticket for sale).

Database table: listings
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to seller
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Concert details
    artist_name = Column(String(200), nullable=False, index=True)
    concert_date = Column(Date, nullable=False, index=True)
    venue_name = Column(String(200), nullable=False)
    
    # Seat information
    section = Column(String(50), nullable=True)
    row = Column(String(10), nullable=True)
    seat_number = Column(String(10), nullable=True)
    
    # Price and availability
    price = Column(Numeric(10, 2), nullable=False)  # Price in dollars (e.g., 150.50)
    quantity_available = Column(Integer, default=1)
    
    # Additional info
    description = Column(String(1000), nullable=True)
    is_available = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seller = relationship("User", back_populates="listings")
    messages = relationship("Message", back_populates="listing", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="listing", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Listing(id={self.id}, artist='{self.artist_name}', price={self.price})>"

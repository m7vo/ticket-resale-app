"""
Message Model
=============

Represents a direct message between two users (buyer and seller).

Database table: messages
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    
    # Message content
    message_text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    listing = relationship("Listing", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, from_user={self.sender_id}, to_user={self.receiver_id})>"

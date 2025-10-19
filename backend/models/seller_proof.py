"""
SellerProof Model
=================

Represents proof of past sales (screenshots) to build seller credibility.

Database table: seller_proof
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class SellerProof(Base):
    __tablename__ = "seller_proof"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Proof information
    proof_image_url = Column(String(500), nullable=False)
    description = Column(String(255), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    seller = relationship("User", back_populates="proof_images")
    
    def __repr__(self):
        return f"<SellerProof(id={self.id}, seller_id={self.seller_id})>"
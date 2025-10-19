"""
Main FastAPI Application
========================

This is the entry point for your backend server.

HOW IT WORKS:
1. Creates a FastAPI app instance
2. Sets up database connection
3. Creates database tables (if they don't exist)
4. Registers API routes (endpoints)
5. Enables CORS so frontend can talk to backend
6. Runs the server on http://localhost:8000

RUN THIS FILE WITH:
    python app.py
    
Then visit http://localhost:8000/docs to see API documentation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import configuration
from config import DATABASE_URL, BACKEND_URL, FRONTEND_URL

# Import database models
from models import Base, User, UserProfile, Listing, Message, Review, SellerProof

# ============================================================================
# DATABASE SETUP
# ============================================================================

# Create database engine
# This is like creating a connection pool to PostgreSQL
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries in terminal (useful for debugging)
    future=True
)

# Create session factory
# Sessions manage database transactions (like one conversation with the database)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables if they don't exist
# This reads your models (User, Listing, etc.) and creates tables in the database
Base.metadata.create_all(bind=engine)

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Ticket Resale API",
    description="A peer-to-peer ticket resale platform without fees",
    version="1.0.0"
)

# ============================================================================
# CORS SETUP
# ============================================================================
# CORS = Cross-Origin Resource Sharing
# This allows your React frontend (localhost:3000) to make requests to this backend (localhost:8000)
# Without this, browsers block requests from different domains

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local React development
        "http://localhost:8000",  # Local backend
        FRONTEND_URL,              # From .env
    ],
    allow_credentials=True,        # Allow cookies
    allow_methods=["*"],           # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],           # Allow all headers
)

# ============================================================================
# DEPENDENCY: Get Database Session
# ============================================================================

def get_db():
    """
    Creates a database session for each request.
    
    FastAPI will automatically:
    1. Call this function before each endpoint
    2. Inject the session into the endpoint
    3. Close the session after the endpoint finishes
    
    Usage in an endpoint:
        @app.get("/users/{user_id}")
        def get_user(user_id: int, db: Session = Depends(get_db)):
            user = db.query(User).filter(User.id == user_id).first()
            return user
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# TEST ROUTE
# ============================================================================

@app.get("/")
def read_root():
    """
    Test endpoint to verify server is running.
    
    Visit http://localhost:8000 in browser to see this.
    """
    return {
        "message": "Ticket Resale API is running!",
        "docs_url": "http://localhost:8000/docs",
        "health": "OK"
    }

@app.get("/health")
def health_check():
    """
    Health check endpoint (useful for monitoring).
    Returns OK if server is running.
    """
    return {"status": "healthy"}

# ============================================================================
# ROUTE IMPORTS (When you create them)
# ============================================================================

# Uncomment these as you create the route files

# from routes.auth import router as auth_router
# from routes.listings import router as listings_router
# from routes.messages import router as messages_router
# from routes.users import router as users_router

# app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(listings_router, prefix="/api/listings", tags=["Listings"])
# app.include_router(messages_router, prefix="/api/messages", tags=["Messages"])
# app.include_router(users_router, prefix="/api/users", tags=["Users"])

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    """
    This block runs when you execute: python app.py
    
    uvicorn is the ASGI server that actually runs FastAPI
    
    Parameters:
    - app: The FastAPI application instance
    - host: Which IP to bind to (0.0.0.0 = accessible from anywhere)
    - port: Which port to run on (8000)
    - reload: Auto-restart when files change (great for development)
    """
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
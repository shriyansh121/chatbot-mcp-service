from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.db.models.user import User

router = APIRouter(prefix="/api/auth", tags=["authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=Token)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = AuthService.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = AuthService.create_user(db, user)
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = AuthService.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(db_user)
    )

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # Authenticate user
    db_user = AuthService.authenticate_user(db, user)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = AuthService.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(db_user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)
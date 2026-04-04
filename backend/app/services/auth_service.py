from sqlalchemy.orm import Session
from app.db.models.user import User
from app.schemas.auth import UserCreate, UserLogin
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

# pwd_context removed in favor of direct bcrypt

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthService:
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        hashed_password = AuthService.get_password_hash(user.password)
        db_user = User(
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, user: UserLogin) -> User:
        db_user = AuthService.get_user_by_email(db, user.email)
        if not db_user:
            return None
        if not AuthService.verify_password(user.password, db_user.password_hash):
            return None
        return db_user
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> str:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                return None
            return email
        except JWTError:
            return None
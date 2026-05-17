import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET = os.getenv("SHOPFIX_JWT_SECRET", "shopfix-dev-secret-change-me")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": subject, "exp": expire}, SECRET, algorithm=ALGORITHM)


def register_user(db: Session, email: str, password: str, display_name: str) -> User:
    user = User(email=email, hashed_password=hash_password(password), display_name=display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter_by(email=email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

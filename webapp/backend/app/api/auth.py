from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.config import get_settings
from app.models.base import User
from app.api.deps import get_current_user
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class SetupRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    role: str

@router.post("/setup", response_model=UserResponse)
def setup(data: SetupRequest, response: Response, session: Session = Depends(get_session)):
    existing = session.exec(select(User)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Setup already completed")
    
    if data.password != data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    
    if len(data.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        role="admin"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    svc = SettingsService(session)
    svc.set("setup_completed", True, "security")
    svc.set("admin_email", data.email, "security")
    
    settings = get_settings()
    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})
    response.set_cookie(key="access_token", value=access, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=1800)
    response.set_cookie(key="refresh_token", value=refresh, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=604800)
    
    return UserResponse(id=user.id, email=user.email, role=user.role)

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, session: Session = Depends(get_session)):
    settings = get_settings()
    stmt = select(User).where(User.email == data.email)
    user = session.exec(stmt).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})
    response.set_cookie(key="access_token", value=access, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=1800)
    response.set_cookie(key="refresh_token", value=refresh, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=604800)
    
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response):
    settings = get_settings()
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    
    access = create_access_token({"sub": user_id})
    refresh = create_refresh_token({"sub": user_id})
    response.set_cookie(key="access_token", value=access, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=1800)
    response.set_cookie(key="refresh_token", value=refresh, httponly=True, secure=not settings.DEBUG, samesite="lax", max_age=604800)
    
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, role=user.role)

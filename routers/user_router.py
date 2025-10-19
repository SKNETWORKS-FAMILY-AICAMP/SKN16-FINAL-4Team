from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

import models, schemas, hashing
from database import SessionLocal

# 환경변수 로드 및 시크릿키 세팅
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# OAuth2PasswordBearer 인스턴스 생성 (JWT 토큰 인증용)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

router = APIRouter(prefix="/api/users")

# DB 세션 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", status_code=201)
def user_signup(user_create: schemas.UserCreate, db: Session = Depends(get_db)):
    # 닉네임 중복 확인
    existing_nickname = db.query(models.User).filter(models.User.nickname == user_create.nickname).first()
    if existing_nickname:
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.")
    # 이메일 중복 확인
    existing_email = db.query(models.User).filter(models.User.email == user_create.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")
    # 비밀번호 길이 체크 (72바이트 제한)
    if len(user_create.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="비밀번호가 너무 깁니다. 72바이트 이하로 입력해주세요.")
    # 비밀번호 해싱
    hashed_password = hashing.hash_password(user_create.password)
    # 데이터베이스에 사용자 생성
    new_user = models.User(
        nickname=user_create.nickname,
        username=user_create.username,
        password=hashed_password,
        email=user_create.email,
        gender=user_create.gender,
        create_date=datetime.now()
    )
    db.add(new_user)
    db.commit()
    return {"message": "회원가입이 완료되었습니다."}

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # nickname으로 사용자 검색 + 탈퇴회원 제외
    user = db.query(models.User).filter(
        models.User.nickname == form_data.username, 
        models.User.is_active == True
    ).first()
    if not user or not hashing.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="닉네임 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # JWT 토큰 발급 (nickname 기반)
    data = {
        "sub": user.nickname,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    access_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    # 유저 정보 반환 (Pydantic 변환)
    user_obj = schemas.User.from_orm(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_obj
    }

# JWT 토큰에서 현재 사용자 정보 가져오는 함수
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="토큰이 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname: str = payload.get("sub")
        if nickname is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(
        models.User.nickname == nickname, 
        models.User.is_active == True # 탈퇴 회원 걸러내기
    ).first()
    if user is None:
        raise credentials_exception
    return user

@router.delete("/me", status_code=200)
async def delete_user_account(
    password: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """회원탈퇴 (소프트 딜리트) - DB 삭제 대신 상태값 변경"""
    if not hashing.verify_password(password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호가 올바르지 않습니다."
        )
    try:
        # 상태값 변경 (실제 삭제 대신)
        current_user.is_active = False
        db.commit()
        return {
            "message": "회원탈퇴가 완료되었습니다.",
            "detail": f"사용자 '{current_user.nickname}'의 계정이 탈퇴 처리되었습니다. (정보는 DB에 남아있음)"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원탈퇴 처리 중 오류가 발생했습니다."
        )

@router.get("/me", response_model=schemas.User)
async def get_my_info(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/me/stats")
async def get_user_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자 통계 정보 조회 (진단 기록 수, 저장된 결과 수)"""
    try:
        # 총 진단 기록 수 (SurveyResult 테이블에서 해당 사용자의 모든 기록 - 삭제된 것 포함)
        total_surveys = db.query(models.SurveyResult).filter(
            models.SurveyResult.user_id == current_user.id
        ).count()
        
        # 저장된 결과 수 (현재 활성화된 결과들만)
        saved_results = db.query(models.SurveyResult).filter(
            models.SurveyResult.user_id == current_user.id,
            models.SurveyResult.is_active == True
        ).count()
        
        # 채팅 세션 수 (ChatHistory 테이블에서 해당 사용자의 세션 수)
        chat_sessions = db.query(models.ChatHistory).filter(
            models.ChatHistory.user_id == current_user.id
        ).count()
        
        return {
            "total_surveys": total_surveys,      # 총 진단 기록 수 (삭제된 것 포함)
            "saved_results": saved_results,      # 현재 저장된 결과 수 (활성화된 것만)
            "chat_sessions": chat_sessions       # 채팅 세션 수
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 정보 조회 중 오류가 발생했습니다."
        )

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from schemas import UserRoleUpdateRequest, UserRoleUpdateResponse

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
        create_date=datetime.now(),
        role="user"  # 기본값
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Consent 기록 추가 (트랜잭션 내에서 간단히 추가)
    try:
        # 개인정보 수집 및 이용 (필수)
        consent_personal = models.Consent(
            user_id=new_user.id,
            consent_type='personal_info',
            consent=bool(user_create.consent_required),
            version=os.getenv('TERMS_VERSION', 'v1'),
            source='signup'
        )
        db.add(consent_personal)

        # 마케팅 수신 (선택)
        consent_marketing = models.Consent(
            user_id=new_user.id,
            consent_type='marketing',
            consent=bool(user_create.consent_marketing),
            version=os.getenv('TERMS_VERSION', 'v1'),
            source='signup'
        )
        db.add(consent_marketing)
        db.commit()
    except Exception:
        db.rollback()
        # 이미 유저는 생성되었으므로, 에러는 로깅 후 무시하거나 별도 처리 필요
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

@router.get("/list", response_model=list[schemas.User])
async def get_user_list(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")
    users = db.query(models.User).all()
    return users

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
        
        # 채팅 세션 수: '종료된' 세션만 카운트하도록 변경
        # (요청: end API 호출 후 횟수가 늘어나도록 하기 위함)
        chat_sessions = db.query(models.ChatHistory).filter(
            models.ChatHistory.user_id == current_user.id,
            models.ChatHistory.ended_at != None
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

# ------------------ 관리자용 챗봇 히스토리 라우터 ------------------

# 관리자만 접근 가능한 유저 role 수정 API
@router.patch("/{user_id}/role", response_model=UserRoleUpdateResponse)
async def update_user_role(
    user_id: int,
    req: UserRoleUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    if user.role == req.role:
        return UserRoleUpdateResponse(success=False, message="이미 해당 권한입니다.", user_id=user_id, role=user.role)
    user.role = req.role
    db.commit()
    return UserRoleUpdateResponse(success=True, message="권한이 성공적으로 변경되었습니다.", user_id=user_id, role=user.role)

# 전체 유저 챗봇 히스토리 및 유저 피드백 리스트
@router.get("/list/chat_history")
async def get_all_users_chat_history(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")
    chat_histories = db.query(models.ChatHistory).all()
    result = []
    for history in chat_histories:
        user_feedback = db.query(models.UserFeedback).filter(models.UserFeedback.history_id == history.id).first()
        feedback_data = None
        if user_feedback:
            feedback_data = {
                "id": user_feedback.id,
                "user_id": user_feedback.user_id,
                "feedback": user_feedback.feedback,
                "created_at": user_feedback.created_at
            }

        # 질문/답변 내역 추출
        messages = db.query(models.ChatMessage).filter(models.ChatMessage.history_id == history.id).order_by(models.ChatMessage.id.asc()).all()
        qa_pairs = []
        i = 0
        while i < len(messages) - 1:
            if messages[i].role == "user" and messages[i+1].role == "ai":
                qa_pairs.append({
                    "question": messages[i].text,
                    "answer": messages[i+1].text,
                    "question_id": messages[i].id,
                    "answer_id": messages[i+1].id,
                })
                i += 2
            else:
                i += 1

        result.append({
            "chat_history_id": history.id,
            "user_id": history.user_id,
            "created_at": history.created_at,
            "ended_at": history.ended_at,
            "user_feedback": feedback_data,
            "qa_pairs": qa_pairs
        })
    return result

# 특정 유저 챗봇/분석 히스토리 리스트
@router.get("/{user_id}/chat_history")
async def get_user_chat_history(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 접근 가능합니다.")
    chat_histories = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user_id).all()
    result = []
    for history in chat_histories:
        messages = db.query(models.ChatMessage).filter(models.ChatMessage.history_id == history.id).all()
        result.append({
            "chat_history_id": history.id,
            "created_at": history.created_at,
            "ended_at": history.ended_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "text": msg.text,
                    "created_at": msg.created_at
                } for msg in messages
            ]
        })
    return result

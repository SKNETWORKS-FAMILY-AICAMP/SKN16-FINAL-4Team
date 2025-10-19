from datetime import datetime
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Dict, Optional, Literal
import re
import json

# --- 기존 User, Survey 관련 모델 생략 없이 포함 ---
class UserCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=14)
    username: str
    password: str = Field(min_length=8, max_length=16)
    password_confirm: str
    email: str = Field(pattern=r'^[^@]+@[^@]+\.[^@]+$')
    gender: Literal['남성', '여성'] | None = None

    @model_validator(mode='after')
    def validate_all_fields(self):
        if not (2 <= len(self.nickname) <= 14):
            raise ValueError('닉네임은 2자 이상 14자 이하로 입력해주세요.')
        if ' ' in self.nickname:
            raise ValueError('닉네임에 공백이 있어 안됩니다.')
        if not re.match(r'^[a-zA-Z0-9가-힣]+$', self.nickname):
            raise ValueError('닉네임에는 한글, 영문, 숫자만 사용 가능합니다.')
        forbidden_words = ["운영자", "관리자", "admin"]
        if any(word in self.nickname.lower() for word in forbidden_words):
            raise ValueError('닉네임에 금지된 단어를 포함할 수 없습니다.')
        allowed_special = r'!"#$%()*+,-./:;<=>?@\[\]^_`{|}~'
        conditions = [
            re.search(r'[a-zA-Z]', self.password),
            re.search(r'\d', self.password),
            re.search(f'[{allowed_special}]', self.password)
        ]
        if sum(1 for c in conditions if c) < 2:
            raise ValueError('비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 조합해야 합니다.')
        if re.search(rf'[^a-zA-Z0-9{allowed_special}]', self.password):
            raise ValueError('비밀번호에 허용되지 않은 특수문자가 포함되어 있습니다.')
        if re.search(r'(\w)\1{3,}', self.password):
            raise ValueError('비밀번호에 4자리 이상 동일한 문자를 연속으로 사용할 수 없습니다.')
        if self.password != self.password_confirm:
            raise ValueError('비밀번호가 일치하지 않습니다.')
        return self

class User(BaseModel):
    id: int
    username: str
    nickname: str
    email: str
    gender: Literal['남성', '여성'] | None = None
    create_date: datetime
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class SurveyAnswerCreate(BaseModel):
    question_id: int
    option_id: str
    option_label: str

class SurveyResultCreate(BaseModel):
    answers: List[SurveyAnswerCreate]

class SurveyAnswer(BaseModel):
    id: int
    survey_result_id: int
    question_id: int
    option_id: str
    option_label: str
    score_map: Optional[Dict[str, int]] = None

    class Config:
        from_attributes = True

class SurveyResult(BaseModel):
    id: int
    user_id: Optional[int]
    created_at: datetime
    result_tone: str
    confidence: float
    total_score: int
    
    # OpenAI 분석 결과 상세 정보
    detailed_analysis: Optional[str] = None
    result_name: Optional[str] = None
    result_description: Optional[str] = None
    color_palette: Optional[List[str]] = None
    style_keywords: Optional[List[str]] = None
    makeup_tips: Optional[List[str]] = None
    top_types: Optional[List[Dict]] = None
    
    answers: List[SurveyAnswer] = []

    @field_validator('color_palette', mode='before')
    @classmethod
    def parse_color_palette(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    @field_validator('style_keywords', mode='before')
    @classmethod
    def parse_style_keywords(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    @field_validator('makeup_tips', mode='before')
    @classmethod
    def parse_makeup_tips(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    @field_validator('top_types', mode='before')
    @classmethod
    def parse_top_types(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    class Config:
        from_attributes = True

# --- 챗봇 관련 모델 추가 ---
class ChatResModel(BaseModel):
    primary_tone: str
    sub_tone: str
    description: str
    recommendations: List[str]

class ChatItemModel(BaseModel):
    question_id: int
    question: str
    answer: str
    chat_res: ChatResModel

class ChatbotRequest(BaseModel):
    history_id: Optional[int] = 0
    question: str

class ChatbotHistoryResponse(BaseModel):
    history_id: int
    items: List[ChatItemModel]

class UserFeedbackRequest(BaseModel):
    history_id: int
    feedback: str  # "좋다" 또는 "싫다"

class UserFeedbackResponse(BaseModel):
    user_feedback_id: int
    history_id: int
    user_id: int
    feedback: str
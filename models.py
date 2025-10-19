from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    nickname = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    gender = Column(Enum("여성", "남성", name="gender_enum"), nullable=True)
    create_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

class SurveyResult(Base):
    __tablename__ = "survey_result"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    result_tone = Column(String(20))
    confidence = Column(Float)
    total_score = Column(Integer)
    is_active = Column(Boolean, default=True)  # 소프트 딜리트를 위한 필드
    
    # OpenAI 분석 결과 상세 저장
    detailed_analysis = Column(Text, nullable=True)  # 상세 분석 텍스트
    result_name = Column(String(100), nullable=True)  # "봄 웜톤 🌸"
    result_description = Column(Text, nullable=True)  # 메인 타입 설명
    color_palette = Column(Text, nullable=True)  # JSON 문자열로 저장
    style_keywords = Column(Text, nullable=True)  # JSON 문자열로 저장  
    makeup_tips = Column(Text, nullable=True)  # JSON 문자열로 저장
    top_types = Column(Text, nullable=True)  # JSON 문자열로 저장 (전체 top_types 배열)
    
    answers = relationship("SurveyAnswer", back_populates="result", cascade="all, delete-orphan")

class SurveyAnswer(Base):
    __tablename__ = "survey_answer"
    id = Column(Integer, primary_key=True, index=True)
    survey_result_id = Column(Integer, ForeignKey("survey_result.id"), nullable=False)
    question_id = Column(Integer)
    option_id = Column(String(50))
    option_label = Column(String(255))
    result = relationship("SurveyResult", back_populates="answers")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    user = relationship("User", backref="chat_histories")
    messages = relationship("ChatMessage", back_populates="history", cascade="all, delete-orphan")
    user_feedback = relationship("UserFeedback", back_populates="history", uselist=False)

class ChatMessage(Base):
    __tablename__ = "chat_message"
    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("chat_history.id"), nullable=False)
    role = Column(String(10))  # "user" / "ai"
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    history = relationship("ChatHistory", back_populates="messages")
    ai_feedback = relationship("AIFeedback", back_populates="message", uselist=False)

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, ForeignKey("chat_history.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    feedback = Column(String(10))  # "좋다" or "싫다"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    history = relationship("ChatHistory", back_populates="user_feedback")

class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_message.id"), nullable=False)
    accuracy = Column(Float)
    consistency = Column(Float)
    reliability = Column(Float)
    personalization = Column(Float)
    practicality = Column(Float)
    total_score = Column(Float)
    vector_db_quality = Column(Float)
    detail_accuracy = Column(Text)
    detail_consistency = Column(Text)
    detail_reliability = Column(Text)
    detail_personalization = Column(Text)
    detail_practicality = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    message = relationship("ChatMessage", back_populates="ai_feedback")

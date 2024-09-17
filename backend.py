from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import random
import string
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SECRET_KEY 설정
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set for JWT")

# SECRET_KEY가 문자열인지 확인하고, 아니라면 문자열로 변환
if not isinstance(SECRET_KEY, str):
    SECRET_KEY = str(SECRET_KEY)

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    investment_preference = Column(String)
    risk_tolerance = Column(String)

# VerificationCode model
class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    code = Column(String(6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

# Pydantic models
class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    investment_preference: str
    risk_tolerance: str

class Token(BaseModel):
    access_token: str
    token_type: str

class EmailVerification(BaseModel):
    email: str

class VerificationCheck(BaseModel):
    email: str
    code: str

# Security
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"새 사용자 등록 시도: {user.email}")
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        logger.warning(f"이미 등록된 이메일: {user.email}")
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")
    
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        logger.warning(f"이미 사용 중인 사용자명: {user.username}")
        raise HTTPException(status_code=400, detail="이미 사용 중인 사용자명입니다")
    
    # 이메일 인증 확인
    verification_record = db.query(VerificationCode).filter(VerificationCode.email == user.email).first()
    if not verification_record:
        logger.warning(f"이메일 인증이 완료되지 않음: {user.email}")
        raise HTTPException(status_code=400, detail="이메일 인증이 완료되지 않았습니다")
    
    # 인증 레코드 삭제
    db.delete(verification_record)
    
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, username=user.username, hashed_password=hashed_password,
                   investment_preference=user.investment_preference, risk_tolerance=user.risk_tolerance)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"새 사용자가 성공적으로 등록되었습니다: {user.email}")
    return {"message": "사용자가 성공적으로 등록되었습니다"}

# 이메일 전송 함수
def send_email(to_email, subject, body):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        logger.info(f"이메일이 성공적으로 전송되었습니다: {to_email}")
        return True
    except Exception as e:
        logger.error(f"이메일 전송 실패: {str(e)}")
        return False

# request_verification 함수 수정
@app.post("/request-verification")
def request_verification(email_verification: EmailVerification, db: Session = Depends(get_db)):
    logger.info(f"인증 코드 요청: {email_verification.email}")
    user = db.query(User).filter(User.email == email_verification.email).first()
    
    if user:
        logger.warning(f"인증 코드 요청 실패: 이미 등록된 이메일 - {email_verification.email}")
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")
    
    # 기존 인증 코드 삭제
    db.query(VerificationCode).filter(VerificationCode.email == email_verification.email).delete()
    
    # 새 인증 코드 생성
    verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10분 후 만료
    new_code = VerificationCode(email=email_verification.email, code=verification_code, expires_at=expires_at)
    db.add(new_code)
    db.commit()

    # 이메일 전송
    subject = "이메일 인증 코드"
    body = f"귀하의 이메일 인증 코드는 {verification_code} 입니다. 이 코드는 10분 후에 만료됩니다."
    if send_email(email_verification.email, subject, body):
        logger.info(f"인증 코드가 성공적으로 전송되었습니다: {email_verification.email}")
        return {"message": "인증 코드가 이메일로 전송되었습니다"}
    else:
        logger.error(f"인증 코드 전송 실패: {email_verification.email}")
        raise HTTPException(status_code=500, detail="인증 코드 전송에 실패했습니다. 나중에 다시 시도해 주세요.")


@app.post("/verify-email")
def verify_email(verification: VerificationCheck, db: Session = Depends(get_db)):
    logger.info(f"이메일 인증 시도: {verification.email}")
    code_record = db.query(VerificationCode).filter(VerificationCode.email == verification.email).first()
    if not code_record:
        logger.warning(f"이메일 인증 실패: 인증 코드 레코드 없음 - {verification.email}")
        raise HTTPException(status_code=400, detail="인증 코드를 먼저 요청해주세요")
    if code_record.code != verification.code:
        logger.warning(f"이메일 인증 실패: 잘못된 인증 코드 - {verification.email}")
        raise HTTPException(status_code=400, detail="잘못된 인증 코드입니다")
    if code_record.expires_at < datetime.now(timezone.utc):
        logger.warning(f"이메일 인증 실패: 만료된 인증 코드 - {verification.email}")
        raise HTTPException(status_code=400, detail="인증 코드가 만료되었습니다")
    
    logger.info(f"이메일이 성공적으로 인증되었습니다: {verification.email}")
    return {"message": "이메일이 성공적으로 인증되었습니다"}


@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Add other endpoints (investment advice, calculation) here...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
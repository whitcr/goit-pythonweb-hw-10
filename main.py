from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from pathlib import Path
import crud
import models
import schemas
from database import SessionLocal, engine
from utils import get_password_hash, verify_password, create_access_token
import cloudinary.uploader
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
import cloudinary
import os
from fastapi import Depends, HTTPException 
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from models import User
from database import SessionLocal
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)

class EmailSchema(BaseModel):
    email: EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_USERNAME"),
    MAIL_PORT=465,
    MAIL_SERVER="smtp.meta.ua",
    MAIL_FROM_NAME="Example email",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Перевищено ліміт запитів. Спробуйте пізніше."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register", response_model=schemas.UserOut, status_code=201)
def register(
    user: schemas.UserCreate, 
    background_tasks: BackgroundTasks,  
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    hashed = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    message = MessageSchema(
        subject="Verify your email!",
        recipients=[db_user.email],   
        body=f"Verify your email here http://localhost:8000/verify_email?token={db_user.id}",
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

    return db_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.is_verified == 0:
        raise HTTPException(status_code=403, detail="Please verify your email to log in.")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/verify_email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == int(token)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = 1
    db.commit()
    db.refresh(user)
    return {"detail": "Email verified"}

@limiter.limit("1/second")
@app.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user), request: Request = None):
    return current_user

@app.patch("/avatar")
def upload_avatar(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = cloudinary.uploader.upload(file.file)
    current_user.avatar = result['secure_url']
    db.commit()
    db.refresh(current_user)
    return {"avatar": current_user.avatar}

@app.post("/contacts/", response_model=schemas.ContactOut, status_code=201)
def create_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_contact(db, contact, current_user)

@app.get("/contacts/", response_model=list[schemas.ContactOut])
def read_contacts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_contacts(db, current_user)

@app.get("/contacts/{contact_id}", response_model=schemas.ContactOut)
def read_contact(contact_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    contact = crud.get_contact(db, contact_id, current_user)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@app.put("/contacts/{contact_id}", response_model=schemas.ContactOut)
def update_contact(contact_id: int, contact: schemas.ContactUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    updated = crud.update_contact(db, contact_id, contact, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated

@app.delete("/contacts/{contact_id}", response_model=schemas.ContactOut)
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    deleted = crud.delete_contact(db, contact_id, current_user)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return deleted

@app.get("/search/", response_model=list[schemas.ContactOut])
def search(query: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.search_contacts(db, query, current_user)

@app.get("/birthdays/", response_model=list[schemas.ContactOut])
def birthdays(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_upcoming_birthdays(db, current_user)



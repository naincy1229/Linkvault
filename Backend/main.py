from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import models, auth
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkVault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class BookmarkCreate(BaseModel):
    title: str
    url: str
    category: Optional[str] = "General"
    notes: Optional[str] = None

# --- Auth Routes ---
@app.post("/signup", status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "username": new_user.username}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# --- Bookmark Routes ---
@app.get("/bookmarks")
def get_bookmarks(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    return db.query(models.Bookmark).filter(models.Bookmark.owner_id == current_user.id).all()

@app.post("/bookmarks", status_code=201)
def add_bookmark(bookmark: BookmarkCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    new_bookmark = models.Bookmark(**bookmark.dict(), owner_id=current_user.id)
    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)
    return new_bookmark

@app.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    bookmark = db.query(models.Bookmark).filter(
        models.Bookmark.id == bookmark_id,
        models.Bookmark.owner_id == current_user.id
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return {"message": "Deleted successfully"}

@app.get("/")
def root():
    return {"message": "LinkVault API is running!"}
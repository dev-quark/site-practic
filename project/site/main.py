import uvicorn
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
import hashlib
import os

import include.database.mongo.main as mongo

app = FastAPI(title="PC Builder API")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === НАСТРОЙКИ ===
SECRET_KEY = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_!@#$%^&*()"
ALGORITHM = "HS256"

# === МОДЕЛИ ===
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r'^[A-Za-z0-9_]+$')
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r'^[A-Za-z0-9_]+$')
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Неверный формат email')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+') and v:
            raise ValueError('Телефон должен начинаться с +')
        return v

class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[str] = None
    phone: Optional[str] = None
    current_password: Optional[str] = None

# === ФУНКЦИИ ===
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def get_current_user(request: Request) -> Optional[dict]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return mongo.get_user(username)
    except JWTError:
        return None

# === ENDPOINTS ===

@app.post("/api/login")
async def login(data: LoginRequest):
    print(f"📥 Login: {data.username}")
    if not mongo.check_user(data.username):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    user = mongo.get_user(data.username)
    if not user or not verify_password(data.password, user.get("user_password", "")):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_token({"sub": data.username})
    return {
        "token": token,
        "nickname": user.get("nickname", data.username),
        "avatar_url": user.get("user_img"),
        "role": user.get("role", 1)
    }

@app.post("/api/register")
async def register(data: RegisterRequest):
    print(f"📥 Register: {data.username}")
    if mongo.check_user(data.username):
        raise HTTPException(status_code=400, detail="Пользователь уже существует", headers={"X-Error-Field": "username"})
    if data.email and mongo.check_email(data.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован", headers={"X-Error-Field": "email"})
    if data.phone and mongo.check_phone(data.phone):
        raise HTTPException(status_code=400, detail="Телефон уже зарегистрирован", headers={"X-Error-Field": "phone"})
    result = mongo.create_user({
        "user_name": data.username,
        "password": data.password,
        "user_email": data.email,
        "user_phone": data.phone,
        "nickname": data.username,
        "role": 1
    })
    if not result:
        raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
    
    token = create_token({"sub": data.username})
    
    # 🔥 Берём avatar_url прямо из результата (он уже в правильном формате)
    avatar_url = result.get("user_img", f"/data/images/avatars/{data.username}_avatar.png")
    
    return {
        "token": token, 
        "nickname": data.username, 
        "role": 1,
        "avatar_url": avatar_url  # ← Возвращаем как есть из БД
    }

@app.get("/api/check-username")
async def check_username(username: str):
    return {"available": not mongo.check_user(username)}

@app.get("/data/profile/{username}")
async def get_profile(username: str, request: Request):
    user = mongo.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {
        "username": user.get("user_name"),
        "nickname": user.get("nickname", user.get("user_name")),
        "avatar_url": user.get("user_img"),
        "email": user.get("user_email"),
        "phone": user.get("user_phone"),
        "role": user.get("role", 1)
    }

@app.put("/data/profile/{username}")
async def update_profile(username: str, request: Request, data: ProfileUpdateRequest):
    current_user = get_current_user(request)
    if not current_user or current_user.get("user_name") != username:
        raise HTTPException(status_code=403, detail="Нет доступа")
    if data.email or data.phone:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Требуется текущий пароль")
        if not verify_password(data.current_password, current_user.get("user_password", "")):
            raise HTTPException(status_code=401, detail="Неверный пароль")
    if data.email and data.email != current_user.get("user_email"):
        if mongo.check_email(data.email):
            raise HTTPException(status_code=400, detail="Email уже занят", headers={"X-Error-Field": "email"})
    if data.phone and data.phone != current_user.get("user_phone"):
        if mongo.check_phone(data.phone):
            raise HTTPException(status_code=400, detail="Телефон уже занят", headers={"X-Error-Field": "phone"})
    update_data = {}
    if data.nickname:
        update_data["nickname"] = data.nickname
    if data.email:
        update_data["user_email"] = data.email
    if data.phone:
        update_data["user_phone"] = data.phone
    if update_data:
        mongo.update_user(username, update_data)
    return {"success": True, "updated": update_data}

@app.post("/data/profile/{username}/avatar")
async def upload_avatar(username: str, request: Request):
    current_user = get_current_user(request)
    if not current_user or current_user.get("user_name") != username:
        raise HTTPException(status_code=403, detail="Нет доступа")
    
    form = await request.form()
    avatar = form.get("avatar")
    
    if not avatar or not hasattr(avatar, 'filename'):
        raise HTTPException(status_code=400, detail="Файл не предоставлен")
    
    # Сохраняем файл
    file_ext = os.path.splitext(avatar.filename)[1] or ".png"
    filename = f"{username}_avatar{file_ext}"
    upload_dir = "data/images/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)  # Путь на диске
    
    with open(filepath, "wb") as f:
        content = await avatar.read()
        f.write(content)
    
    # 🔥 Обновляем путь в БД через вспомогательную функцию
    avatar_url = mongo.update_user_avatar(username, filename)
    
    return {"success": True, "avatar_url": avatar_url}  # ← Возвращаем URL из БД

# === СТАТИКА (ПРАВИЛЬНЫЙ ПОРЯДОК!) ===

# 🔥 1. СНАЧАЛА конкретные пути (аватары)
avatar_dir = "data/images/avatars"
os.makedirs(avatar_dir, exist_ok=True)
app.mount("/data/images/avatars", StaticFiles(directory=avatar_dir), name="avatars")

# 2. ПОТОМ общий путь (сайт)
app.mount("/", StaticFiles(directory="site_files", html=True), name="static")

if __name__ == "__main__":
    mongo.init()
    uvicorn.run("main:app", host="127.0.0.1", port=10000, reload=True)
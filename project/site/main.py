"""
=== FastAPI Application ===
PC Builder API Server (Development Version - No Cache)
"""

import uvicorn
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, status, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from jose import jwt, JWTError

# Импорт операций с БД
import include.database.mongo.main as mongo

# === НАСТРОЙКИ ===
SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# === ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ ===
app = FastAPI(title="PC Builder API", version="1.0.0", debug=True)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 🔥 КЛАСС ДЛЯ ОТКЛЮЧЕНИЯ КЕШИРОВАНИЯ СТАТИКИ ===
class NoCacheStaticFiles(StaticFiles):
    """StaticFiles с заголовками для отключения кеширования"""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# === МОДЕЛИ ЗАПРОСОВ (Pydantic) ===
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r'^[A-Za-z0-9_]+$')
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r'^[A-Za-z0-9_]+$')
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    phone: Optional[str] = None

class BuildCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    category: str = Field(..., pattern=r'^(gaming|work|budget|pro)$')
    price: int = Field(..., gt=0)
    components: dict
    image: Optional[str] = None
    is_published: bool = True

class UserBuildRequest(BaseModel):
    user_name: str
    user_email: Optional[str] = None
    user_phone: Optional[str] = None  # 🔥 Добавьте это поле
    request_type: str
    title: str
    description: str
    budget: Optional[int] = None
    components: Optional[dict] = None
    status: str = "pending"

class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request) -> Optional[dict]:
    """Получение текущего пользователя из токена"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        return mongo.get_user(username)
    except JWTError:
        return None

def require_auth(request: Request) -> dict:
    """Требует авторизацию"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user

def require_admin(request: Request) -> dict:
    """Требует права администратора"""
    user = require_auth(request)
    if user.get("role", 1) < 2:
        raise HTTPException(status_code=403, detail="Только для администраторов")
    return user

# === ENDPOINTS: АВТОРИЗАЦИЯ ===

@app.post("/api/login")
async def login_endpoint(data: LoginRequest):
    """Вход пользователя"""
    print(f"📥 Login attempt: {data.username}")
    
    user = mongo.get_user(data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # 🔥 ПРЯМОЕ СРАВНЕНИЕ ПАРОЛЕЙ (без хеширования - для разработки!)
    if user.get("user_password") != data.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    token = create_access_token({"sub": data.username})
    
    return {
        "token": token,
        "user_name": user.get("user_name"),
        "nickname": user.get("nickname", data.username),
        "avatar_url": user.get("user_img"),
        "role": user.get("role", 1),
        "email": user.get("user_email")
    }

@app.post("/api/register")
async def register_endpoint(data: RegisterRequest):
    """Регистрация нового пользователя"""
    print(f"📥 Registration: {data.username}")
    
    if mongo.check_user(data.username):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    if data.email and mongo.check_email(data.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    result = mongo.create_user({
        "user_name": data.username,
        "password": data.password,  # 🔥 Без хеширования для разработки
        "user_email": data.email,
        "user_phone": data.phone,
        "nickname": data.username,
        "role": 1
    })
    
    if not result:
        raise HTTPException(status_code=500, detail="Ошибка регистрации")
    
    token = create_access_token({"sub": data.username})
    
    return {
        "token": token,
        "user_name": data.username,
        "nickname": data.username,
        "role": 1,
        "avatar_url": result.get("user_img")
    }

# === 🔥 НОВЫЙ ЭНДПОИНТ: ПРОВЕРКА USERNAME ===

@app.get("/api/check-username")
async def check_username_endpoint(username: str):
    """Проверка доступности имени пользователя"""
    
    if not username or len(username) < 3:
        return {"available": False, "message": "Имя должно быть не менее 3 символов"}
    
    if len(username) > 20:
        return {"available": False, "message": "Имя должно быть не более 20 символов"}
    
    import re
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return {"available": False, "message": "Разрешены только буквы, цифры и подчёркивание"}
    
    if mongo.check_user(username):
        return {"available": False, "message": "Имя пользователя уже занято"}
    
    return {"available": True, "message": "Имя доступно"}

# === 🔥 ENDPOINTS: ОБНОВЛЕНИЕ ПРОФИЛЯ ===

# С префиксом /api
@app.put("/api/profile/me")
async def update_profile_api(
    data: ProfileUpdateRequest, 
    request: Request
):
    """Обновление профиля текущего пользователя"""
    return await _update_profile_logic(data, request)

# БЕЗ префикса /api (для совместимости с фронтендом)
@app.put("/profile/me")
async def update_profile_compat(
    data: ProfileUpdateRequest, 
    request: Request
):
    """Обновление профиля (без /api)"""
    return await _update_profile_logic(data, request)

# === 🔥 ВНУТРЕННЯЯ ЛОГИКА ===
async def _update_profile_logic(
    data: ProfileUpdateRequest, 
    request: Request
):
    """Общая логика обновления профиля"""
    current_user = require_auth(request)
    username = current_user.get("user_name")
    
    print(f"📥 Update profile: {username}")
    
    # Разрешённые поля для обновления
    allowed_fields = ["nickname", "user_email", "user_phone"]
    update_data = {k: v for k, v in data.dict(exclude_unset=True).items() if k in allowed_fields}
    
    # Проверка уникальности email
    if "user_email" in update_data and update_data["user_email"] != current_user.get("user_email"):
        if mongo.check_email(update_data["user_email"]):
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    # Обновление в БД
    if update_data:
        mongo.users_collection.update_one(
            {"user_name": username},
            {"$set": {**update_data, "updated_at": datetime.utcnow()}}
        )
        print(f"✅ Profile updated: {update_data}")
    
    return {
        "status": "success", 
        "message": "Профиль обновлён",
        "updated": update_data
    }

@app.get("/api/auth/me")
@app.get("/auth/me")
async def get_current_user_profile(request: Request):
    """Получение профиля текущего пользователя"""
    user = require_auth(request)
    
    return {
        "user_name": user.get("user_name"),
        "nickname": user.get("nickname"),
        "user_email": user.get("user_email"),
        "user_img": user.get("user_img"),
        "role": user.get("role", 1),
        "_id": str(user.get("_id", "")),
        "created_at": user.get("created_at")
    }

# === 🔥 ЭНДПОИНТЫ: АВАТАРЫ (ИЗМЕНЁННЫЙ ПУТЬ + УДАЛЕНИЕ СТАРОГО) ===

async def _delete_old_avatar(username: str):
    """Удаление старого аватара пользователя"""
    import glob
    
    avatar_dir = f"data/avatars/{username}"
    if os.path.exists(avatar_dir):
        # Удаляем все файлы аватаров в папке
        files = glob.glob(f"{avatar_dir}/*")
        for file_path in files:
            try:
                os.remove(file_path)
                print(f"🗑️ Удалён старый аватар: {file_path}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {file_path}: {e}")

async def _upload_avatar_logic(username: str, request: Request, file: UploadFile):
    print(f"📥 Avatar upload: {username}, file: {file.filename}")
    current_user = require_auth(request)
    if current_user.get("user_name") != username and current_user.get("role", 1) < 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    allowed = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(allowed)}")
    
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5MB)")
    
    try:
        # 🔥 НОВЫЙ ПУТЬ: data/avatars/{username}/
        avatar_dir = f"data/avatars/{username}"
        os.makedirs(avatar_dir, exist_ok=True)
        
        # 🔥 УДАЛЯЕМ СТАРЫЙ АВАТАР
        await _delete_old_avatar(username)
        
        # Сохраняем новый
        filename = f"{username}_avatar{ext}"
        filepath = f"{avatar_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        # 🔥 НОВЫЙ URL для БД
        avatar_url = f"/data/avatars/{username}/{filename}"
        
        mongo.users_collection.update_one(
            {"user_name": username}, 
            {"$set": {"user_img": avatar_url, "avatar_url": avatar_url}}
        )
        
        print(f"✅ Аватар сохранён: {avatar_url}")
        return {"status": "success", "avatar_url": avatar_url, "message": "Аватар загружен"}
        
    except Exception as e:
        print(f"❌ Avatar error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

# С префиксом /api
@app.post("/api/data/profile/{username}/avatar")
async def upload_avatar_api(username: str, request: Request, file: UploadFile = File(...)):
    return await _upload_avatar_logic(username, request, file)

# Без префикса /api
@app.post("/data/profile/{username}/avatar")
async def upload_avatar_compat(username: str, request: Request, file: UploadFile = File(...)):
    return await _upload_avatar_logic(username, request, file)

# Сброс аватара — с НОВЫМ путём и удалением старого
@app.post("/api/data/profile/{username}/avatar/reset")
@app.post("/data/profile/{username}/avatar/reset")
async def reset_avatar_endpoint(username: str, request: Request):
    current_user = require_auth(request)
    if current_user.get("user_name") != username and current_user.get("role", 1) < 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    user = mongo.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    try:
        from PIL import Image, ImageDraw
        
        # 🔥 НОВЫЙ ПУТЬ: data/avatars/{username}/
        avatar_dir = f"data/avatars/{username}"
        os.makedirs(avatar_dir, exist_ok=True)
        
        # 🔥 УДАЛЯЕМ СТАРЫЙ АВАТАР
        await _delete_old_avatar(username)
        
        filepath = f"{avatar_dir}/{username}_avatar.png"
        
        # Создаём стандартный аватар
        img = Image.new('RGB', (200, 200), color=(0, 212, 170))
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), username[0].upper(), anchor="mm", fill="#1a1a2e", font_size=80)
        img.save(filepath)
        
        # 🔥 НОВЫЙ URL
        avatar_url = f"/data/avatars/{username}/{username}_avatar.png"
        
        mongo.users_collection.update_one(
            {"user_name": username},
            {"$set": {"user_img": avatar_url, "avatar_url": avatar_url}}
        )
        
        print(f"✅ Аватар сброшен: {avatar_url}")
        return {"status": "success", "avatar_url": avatar_url, "message": "Аватар сброшен"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сброса: {str(e)}")
# === 🔥 ЭНДПОИНТЫ АВАТАРОВ (с префиксом /api и без) ===

# С префиксом /api
@app.post("/api/data/profile/{username}/avatar")
async def upload_avatar_endpoint(
    username: str,
    request: Request,
    file: UploadFile = File(..., description="Файл аватара")
):
    """Загрузка аватара пользователя"""
    print(f"📥 Avatar upload: {username}, file: {file.filename}")
    
    current_user = require_auth(request)
    if current_user.get("user_name") != username and current_user.get("role", 1) < 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    allowed = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(allowed)}")
    
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5MB)")
    
    try:
        avatar_dir = f"data/images/avatars/{username}"
        os.makedirs(avatar_dir, exist_ok=True)
        
        filename = f"{username}_avatar{ext}"
        filepath = f"{avatar_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        avatar_url = f"/data/images/avatars/{username}/{filename}"
        mongo.users_collection.update_one(
            {"user_name": username},
            {"$set": {"user_img": avatar_url, "avatar_url": avatar_url}}
        )
        
        return {
            "status": "success",
            "avatar_url": avatar_url,
            "message": "Аватар загружен"
        }
        
    except Exception as e:
        print(f"❌ Avatar upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


# === В main.py ===
from fastapi import UploadFile, File  # 🔥 Импортируйте это!

@app.post("/data/profile/{username}/avatar")
@app.post("/api/data/profile/{username}/avatar")  # Дубль с /api
async def upload_avatar_endpoint(
    username: str,
    request: Request,
    file: UploadFile = File(...)  # 🔥 Поле называется "file"
):
    """Загрузка аватара пользователя"""
    print(f"📥 Avatar upload: {username}")
    print(f"📁 File: {file.filename}, Type: {file.content_type}")
    
    # Проверка авторизации
    current_user = require_auth(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    # Проверка прав
    if current_user.get("user_name") != username and current_user.get("role", 1) < 2:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Проверка типа файла
    allowed = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(allowed)}")
    
    # Чтение файла
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5MB)")
    
    try:
        # Сохранение
        avatar_dir = f"data/images/avatars/{username}"
        os.makedirs(avatar_dir, exist_ok=True)
        
        filename = f"{username}_avatar{ext}"
        filepath = f"{avatar_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Обновление БД
        avatar_url = f"/data/images/avatars/{username}/{filename}"
        mongo.users_collection.update_one(
            {"user_name": username},
            {"$set": {"user_img": avatar_url, "avatar_url": avatar_url}}
        )
        
        return {
            "status": "success",
            "avatar_url": avatar_url,
            "message": "Аватар загружен"
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

# === 🔥 ENDPOINTS: СБОРКИ ПК ===

# Получение списка сборок
@app.get("/builds")
@app.get("/api/builds")  # Дубль с /api для совместимости
async def get_builds_endpoint(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    cpu_brand: Optional[str] = None
):
    """Получение списка сборок с фильтрацией"""
    builds = mongo.get_all_builds(
        category=category,
        max_price=max_price,
        cpu_brand=cpu_brand
    )
    return builds

# Получение сборки по ID
@app.get("/builds/{build_id}")
@app.get("/api/builds/{build_id}")
async def get_build_endpoint(build_id: str):
    """Получение сборки по ID"""
    build = mongo.get_build_by_id(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return build

# Создание новой сборки (только админ)
@app.post("/builds")
@app.post("/api/builds")
async def create_build_endpoint(build_data: dict, request: Request):
    """Создание сборки (только для админов)"""
    require_admin(request)
    
    # Валидация обязательных полей
    required = ["title", "category", "price", "components"]
    if not all(k in build_data for k in required):
        raise HTTPException(status_code=400, detail="Заполните все обязательные поля")
    
    result = mongo.create_build(build_data)
    if not result:
        raise HTTPException(status_code=500, detail="Ошибка создания")
    return result

# Обновление сборки (только админ)
@app.put("/builds/{build_id}")
@app.put("/api/builds/{build_id}")
async def update_build_endpoint(build_id: str, build_data: dict, request: Request):
    """Обновление сборки (только для админов)"""
    require_admin(request)
    
    success = mongo.update_build(build_id, build_data)
    if not success:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return {"status": "updated", "id": build_id}

# Удаление сборки (только админ)
@app.delete("/builds/{build_id}")
@app.delete("/api/builds/{build_id}")
async def delete_build_endpoint(build_id: str, request: Request):
    """Удаление сборки (только для админов)"""
    require_admin(request)
    
    from bson import ObjectId
    try:
        ObjectId(build_id)  # Проверка формата
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    
    success = mongo.delete_build(build_id)
    if not success:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return {"status": "deleted", "id": build_id}

# === ENDPOINTS: ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ ===

@app.get("/api/requests")
async def get_requests_endpoint(request: Request):
    """Получение всех запросов (только админы)"""
    require_admin(request)
    return list(mongo.db.requests.find({}, {"_id": 0}).sort("created_at", -1))

# В main.py, эндпоинт создания запроса:
@app.post("/requests")
async def create_request_endpoint(data: UserBuildRequest):
    request_doc = {
        **data.dict(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "admin_comment": None
    }
    mongo.db.requests.insert_one(request_doc)
    return {"status": "success", "message": "Запрос отправлен"}

@app.put("/api/requests/{request_id}")
async def update_request_endpoint(request_id: str, status: str, admin_comment: str = None, request: Request = None):
    """Обновление статуса запроса (только админы)"""
    if request:
        require_admin(request)
    mongo.db.requests.update_one(
        {"_id": request_id},
        {"$set": {"status": status, "admin_comment": admin_comment, "updated_at": datetime.utcnow()}}
    )
    return {"status": "updated"}
# ============================================
# === 🔥 API: АДМИН-ПАНЕЛЬ ===
# ============================================

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# === В main.py, замените функцию get_current_admin ===

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка токена и роли админа (через JWT)"""
    token = credentials.credentials
    
    try:
        # 🔥 Декодируем JWT токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if not username:
            raise HTTPException(status_code=401, detail="Неверный токен")
        
        # Получаем пользователя из БД по имени
        user_data = mongo.get_user(username)
        
        if not user_data or user_data.get("role", 0) < 3:
            raise HTTPException(status_code=403, detail="Доступ запрещён (требуется роль Администратор)")
            
        return user_data
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный или истёкший токен")


# === ЗАПРОСЫ/ЗАКАЗЫ ===

@app.get("/api/admin/requests")
async def admin_get_requests(
    status_filter: str = Query(None, description="pending/approved/rejected"),
    current_user: dict = Depends(get_current_admin)
):
    return mongo.get_all_requests(status_filter=status_filter)

@app.post("/api/admin/requests")
async def admin_create_request(
    request_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    result = mongo.create_request(request_data)
    if not result:
        raise HTTPException(status_code=400, detail="Ошибка создания")
    return result

@app.put("/api/admin/requests/{request_id}")
async def admin_update_request(
    request_id: str,
    status: str = Query(...),
    admin_comment: str = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.update_request_status(request_id, status, admin_comment)
    if not success:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    return {"status": "updated"}

@app.delete("/api/admin/requests/{request_id}")
async def admin_delete_request(
    request_id: str,
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.delete_request(request_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    return {"status": "deleted"}


# === ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ ===

@app.get("/api/admin/po")
async def admin_get_po(
    category: str = Query(None),
    search: str = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    return mongo.get_all_software(category=category, search=search)

@app.post("/api/admin/po")
async def admin_create_po(
    po_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    result = mongo.create_software(po_data)
    if not result:
        raise HTTPException(status_code=400, detail="Ошибка: проверьте уникальность ID")
    return result

@app.put("/api/admin/po/{po_id}")
async def admin_update_po(
    po_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.update_software(po_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="ПО не найдено")
    return {"status": "updated"}

@app.delete("/api/admin/po/{po_id}")
async def admin_delete_po(
    po_id: str,
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.delete_software(po_id)
    if not success:
        raise HTTPException(status_code=404, detail="ПО не найдено")
    return {"status": "deleted"}


# === 🔥 ENDPOINTS: КОМПЛЕКТУЮЩИЕ (admin) ===

@app.get("/api/admin/components/{component_type}")
async def admin_get_components(
    component_type: str,
    search: str = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """Получение компонентов по типу с поиском"""
    return mongo.get_all_components_by_type(component_type, search=search)

@app.post("/api/admin/components/{component_type}")
async def admin_create_component(
    component_type: str,
    component_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Создание компонента"""
    result = mongo.create_component(component_type, component_data)
    if not result:
        raise HTTPException(status_code=400, detail="Ошибка: проверьте уникальность ID")
    return result

# === 🔥 ОБНОВЛЕНИЕ КОМПОНЕНТА (ИСПРАВЛЕННОЕ) ===
@app.put("/api/admin/components/{component_type}/{component_id}")
async def admin_update_component(
    component_type: str,
    component_id: str,  # Это строковый ID из поля "id" в БД
    update_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    # Маппинг типов коллекций
    collection_map = {
        'cpu': 'cpu', 'gpu': 'gpu', 'ram': 'ozu', 'storage': 'storage',
        'psu': 'pzu', 'case': 'frame', 'mobo': 'motherboard', 'cooler': 'cooler'
    }
    
    if component_type not in collection_map:
        raise HTTPException(status_code=400, detail="Неверный тип компонента")
    
    collection = mongo.db[collection_map[component_type]]
    
    # 🔥 Ищем документ по полю "id" (строка), а не по "_id"
    existing = collection.find_one({"id": component_id})
    if not existing:
        # Если не нашли по id, пробуем найти по _id (на случай если передали ObjectId)
        from bson import ObjectId
        try:
            existing = collection.find_one({"_id": ObjectId(component_id)})
        except:
            pass
            
    if not existing:
        raise HTTPException(status_code=404, detail=f"Компонент с ID '{component_id}' не найден")

    # Удаляем защищенные поля из обновления
    protected = ["_id", "id", "created_at"]
    for field in protected:
        update_data.pop(field, None)
    
    update_data["updated_at"] = datetime.utcnow()

    # Обновляем документ
    result = collection.update_one(
        {"id": component_id},  # Ищем по строковому ID
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and not update_data:
        return {"status": "no_changes"}
        
    return {"status": "updated", "id": component_id}

@app.delete("/api/admin/components/{component_type}/{component_id}")
async def admin_delete_component(
    component_type: str,
    component_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Удаление компонента"""
    success = mongo.delete_component(component_type, component_id)
    if not success:
        raise HTTPException(status_code=404, detail="Компонент не найден")
    return {"status": "deleted"}


# === СБОРКИ ПК ===

@app.get("/api/admin/builds")
async def admin_get_builds(
    category: str = Query(None),
    search: str = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    return mongo.get_all_builds_admin(category=category, search=search)

@app.get("/api/admin/builds/{build_id}")
async def admin_get_build(
    build_id: str,
    current_user: dict = Depends(get_current_admin)
):
    build = mongo.get_build_admin(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return build

@app.post("/api/admin/builds")
async def admin_create_build(
    build_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    result = mongo.create_build_admin(build_data, author_id=current_user.get("user_name"))
    if not result:
        raise HTTPException(status_code=400, detail="Ошибка создания")
    return result

@app.put("/api/admin/builds/{build_id}")
async def admin_update_build(
    build_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.update_build_admin(build_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return {"status": "updated"}

@app.delete("/api/admin/builds/{build_id}")
async def admin_delete_build(
    build_id: str,
    current_user: dict = Depends(get_current_admin)
):
    success = mongo.delete_build_admin(build_id)
    if not success:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return {"status": "deleted"}


# === ПОЛЬЗОВАТЕЛИ (только роль 4 - Разработчик) ===

def get_current_developer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка токена и роли разработчика (через JWT)"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if not username:
            raise HTTPException(status_code=401, detail="Неверный токен")
        
        user_data = mongo.get_user(username)
        
        if not user_data or user_data.get("role", 0) < 4:
            raise HTTPException(status_code=403, detail="Требуется роль Разработчик")
            
        return user_data
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный или истёкший токен")

@app.get("/api/admin/users")
async def admin_get_users(
    search: str = Query(None),
    role_filter: int = Query(None),
    current_user: dict = Depends(get_current_developer)
):
    return mongo.get_all_users(search=search, role_filter=role_filter)

@app.get("/api/admin/users/{username}")
async def admin_get_user(
    username: str,
    current_user: dict = Depends(get_current_developer)
):
    user = mongo.get_user_admin(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

@app.put("/api/admin/users/{username}/role")
async def admin_update_user_role(
    username: str,
    new_role: int,
    current_user: dict = Depends(get_current_developer)
):
    if username == "admin":
        raise HTTPException(status_code=403, detail="Нельзя изменить роль главного админа")
    
    success = mongo.update_user_role(username, new_role)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"status": "updated"}

@app.put("/api/admin/users/{username}")
async def admin_update_user(
    username: str,
    update_data: dict,
    current_user: dict = Depends(get_current_developer)
):
    if username == "admin":
        raise HTTPException(status_code=403, detail="Нельзя редактировать главного админа")
    
    success = mongo.update_user_profile(username, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"status": "updated"}

@app.delete("/api/admin/users/{username}")
async def admin_delete_user(
    username: str,
    current_user: dict = Depends(get_current_developer)
):
    if username == "admin" or username == current_user.get("user_name"):
        raise HTTPException(status_code=403, detail="Нельзя удалить этого пользователя")
    
    success = mongo.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"status": "deleted"}
# === ENDPOINTS: ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ ===

@app.get("/api/po/list")
async def get_po_list_endpoint():
    """Получение списка ПО"""
    return mongo.get_all_po()

@app.get("/api/po/{po_id}")
async def get_po_endpoint(po_id: str):
    """Получение ПО по ID"""
    po = mongo.get_po_by_id(po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    return po

# === 🔥 СТАТИКА — ИЗМЕНЁННЫЙ ПУТЬ ===
# === В main.py, после существующих эндпоинтов ===

# === 🔥 ENDPOINTS: КОМПОНЕНТЫ (ИЗ configdb) ===

# === 🔥 ПРЯМОЙ ЭНДПОИНТ ДЛЯ CONFIGDB ===
# === 🔥 ENDPOINTS: КОМПОНЕНТЫ (ИЗ РАЗДЕЛЬНЫХ КОЛЛЕКЦИЙ) ===

@app.get("/api/configdb/components")
@app.get("/configdb/components")
async def get_components_endpoint(type: Optional[str] = None):
    """Получение компонентов из раздельных коллекций"""
    try:
        components = mongo.get_all_components(component_type=type)
        print(f"✅ Найдено компонентов: {len(components)}")
        return components
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === 🔥 ЭНДПОИНТЫ: ГЛОССАРИЙ ===

class GlossaryItem(BaseModel):
    term: str
    definition: str
    category: Optional[str] = "general"

@app.get("/api/glossary")
async def get_glossary(category: Optional[str] = None):
    """Получение терминов глоссария"""
    query = {}
    if category:
        query["category"] = category
    return list(mongo.db.glossary.find(query, {"_id": 0}).sort("term", 1))

@app.post("/api/glossary")
async def create_glossary( data: GlossaryItem, request: Request):
    """Добавление термина (только админ+)"""
    require_admin(request)
    mongo.db.glossary.insert_one({**data.dict(), "created_at": datetime.utcnow()})
    return {"status": "created"}

@app.delete("/api/glossary/{term}")
async def delete_glossary(term: str, request: Request):
    """Удаление термина (только админ+)"""
    require_admin(request)
    mongo.db.glossary.delete_one({"term": term})
    return {"status": "deleted"}

# === 🔥 ЭНДПОИНТЫ: ПОЛЬЗОВАТЕЛИ (Разработчик) ===

@app.get("/api/users")
async def get_users(request: Request):
    """Получение списка пользователей (только разработчик)"""
    require_admin(request)  # role >= 2
    user = get_current_user(request)
    if user.get("role", 1) < 4:
        raise HTTPException(status_code=403, detail="Только для разработчиков")
    
    users = list(mongo.users_collection.find({}, {
        "user_password": 0,
        "_id": 0
    }).sort("created_at", -1))
    return users
# В main.py, перед app.mount(...):
# ============================================
# === 🔥 ENDPOINT: ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ (БЕЗ /api/) ===
# ============================================

@app.get("/users/{username}")
async def get_user_profile(username: str):
    """Получение профиля пользователя — для auth.js"""
    from include.database.mongo import main as mongo
    
    user = mongo.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # 🔥 Убираем пароль из ответа
    user.pop("user_password", None)
    
    return user
# ============================================
# === 🔥 ENDPOINT: ПОЛУЧЕНИЕ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ ===
# ============================================

@app.get("/api/users/{username}")
async def get_user_profile_endpoint(username: str):
    """Получение профиля пользователя по имени"""
    # 🔥 Получаем пользователя из БД
    user = mongo.get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # 🔥 Убираем пароль из ответа
    user.pop("user_password", None)
    
    return user
@app.put("/api/users/{username}/role")
async def update_user_role(username: str, new_role: int, request: Request):
    """Изменение роли пользователя (только разработчик)"""
    require_admin(request)
    current_user = get_current_user(request)
    
    if current_user.get("role", 1) < 4:
        raise HTTPException(status_code=403, detail="Только для разработчиков")
    
    if new_role not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Неверная роль")
    
    mongo.users_collection.update_one(
        {"user_name": username},
        {"$set": {"role": new_role, "updated_at": datetime.utcnow()}}
    )
    return {"status": "updated", "username": username, "new_role": new_role}

# === 🔥 ENDPOINTS: ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ (ПО) ===

# Получение списка ПО
@app.get("/api/po/list")
@app.get("/po/list")  # Дубль без /api
async def get_po_list_endpoint():
    """Получение списка всех программ"""
    return mongo.get_all_po()

# Получение ПО по ID
@app.get("/api/po/{po_id}")
@app.get("/po/{po_id}")  # Дубль без /api
async def get_po_endpoint(po_id: str):
    """Получение программы по ID"""
    po = mongo.get_po_by_id(po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    return po

# Создание или обновление ПО
@app.post("/api/po")
@app.post("/po")  # Дубль без /api
async def create_or_update_po(data: POCreateRequest, request: Request):
    """Создание или обновление программы (только для админов)"""
    require_admin(request)
    
    existing = mongo.get_po_by_id(data.id)
    
    if existing:
        # Обновление
        update_data = data.dict(exclude_unset=True)
        if mongo.update_po(data.id, update_data):
            return {"success": True, "action": "updated", "id": data.id}
        else:
            raise HTTPException(status_code=500, detail="Ошибка обновления")
    else:
        # Создание
        result = mongo.create_po(data.dict())
        if result:
            return {"success": True, "action": "created", "id": data.id}
        else:
            raise HTTPException(status_code=500, detail="Ошибка создания")

# 🔥 УДАЛЕНИЕ ПО (исправленный DELETE)
@app.delete("/api/po/{po_id}")
@app.delete("/po/{po_id}")  # Дубль без /api
async def delete_po_endpoint(po_id: str, request: Request):
    """Удаление программы (только для админов)"""
    require_admin(request)
    
    if mongo.delete_po(po_id):
        # Удаляем папку с изображением если есть
        import shutil
        image_dir = f"data/images/po/{po_id}"
        if os.path.exists(image_dir):
            shutil.rmtree(image_dir)
        return {"success": True, "deleted": po_id}
    else:
        raise HTTPException(status_code=404, detail="Программа не найдена")

@app.delete("/api/builds/{build_id}")
async def delete_build_endpoint(build_id: str, request: Request):
    """Удаление сборки (только админы)"""
    require_admin(request)
    
    # 🔥 ВАЛИДАЦИЯ: проверяем, что build_id — валидный ObjectId
    from bson import ObjectId
    try:
        obj_id = ObjectId(build_id)
    except Exception:
        raise HTTPException(
            status_code=400, 
            detail=f"Неверный формат ID: {build_id}. Ожидается 24-символьная hex-строка"
        )
    
    success = mongo.delete_build(build_id=build_id)
    if not success:
        raise HTTPException(status_code=404, detail="Сборка не найдена")
    return {"status": "deleted", "id": build_id}

# === 🔥 ENDPOINTS: ГЛОССАРИЙ ===

@app.get("/api/admin/glossary")
async def admin_get_glossary(
    category: str = Query(None),
    search: str = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """Получение терминов глоссария (только админ+)"""
    return mongo.get_all_glossary(category=category, search=search)

@app.post("/api/admin/glossary")
async def admin_create_glossary(
    term_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Создание термина (только админ+)"""
    result = mongo.create_glossary(term_data)
    if not result:
        raise HTTPException(status_code=400, detail="Ошибка: термин уже существует")
    return result

@app.put("/api/admin/glossary/{term}")
async def admin_update_glossary(
    term: str,
    update_data: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Обновление термина (только админ+)"""
    success = mongo.update_glossary(term, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Термин не найден")
    return {"status": "updated"}

@app.delete("/api/admin/glossary/{term}")
async def admin_delete_glossary(
    term: str,
    current_user: dict = Depends(get_current_admin)
):
    """Удаление термина (только админ+)"""
    success = mongo.delete_glossary(term)
    if not success:
        raise HTTPException(status_code=404, detail="Термин не найден")
    return {"status": "deleted"}

# Публичный эндпоинт для чтения (без авторизации)
@app.get("/api/glossary")
async def public_get_glossary(category: str = None):
    """Публичный доступ к глоссарию (только чтение)"""
    return mongo.get_all_glossary(category=category)

# Создаём директории (НОВЫЙ ПУТЬ!)
os.makedirs("data/avatars", exist_ok=True)
os.makedirs("data/images/po", exist_ok=True)
os.makedirs("site_files", exist_ok=True)

# 🔥 Монтируем статику с НОВЫМ путём
app.mount("/data/avatars", NoCacheStaticFiles(directory="data/avatars"), name="avatars")
app.mount("/data/images/po", NoCacheStaticFiles(directory="data/images/po"), name="po_images")
app.mount("/", NoCacheStaticFiles(directory="site_files", html=True), name="static")

# === ЗАПУСК ===

if __name__ == "__main__":
    print("🚀 Запуск PC Builder API...")
    mongo.init()
    uvicorn.run("main:app", host="127.0.0.1", port=10000, reload=True)
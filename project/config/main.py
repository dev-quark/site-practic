# main.py
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from datetime import datetime, timedelta
from typing import Optional, Annotated
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import sys, os, hashlib, shutil, json
from fastapi.staticfiles import StaticFiles

# === ПОДКЛЮЧЕНИЕ К ВАШЕЙ БД ===
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from include.database.mongo.main import (
        get_user,
        check_user,
        check_email,
        check_phone,
        create_user,
        update_image,
        init_db
    )
    DB_AVAILABLE = True
    print("✅ MongoDB модуль подключён")
except Exception as e:
    print(f"⚠️ Ошибка импорта БД: {e}")
    DB_AVAILABLE = False

# === КОНФИГУРАЦИЯ ===
SECRET_KEY = "forgepower_secret_2026_do_not_share"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

app = FastAPI(title="ForgePower")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(username: str, password: str) -> bool:
    if not DB_AVAILABLE:
        return False
    user = get_user(username)
    if not user or "user_password" not in user:
        return False
    input_hash = _hash_password(password)
    stored_hash = user["user_password"]
    return input_hash == stored_hash

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен недействителен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = get_user(username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# === МОДЕЛИ ===
class UserRegister(BaseModel):
    username: str
    password: str
    email: str
    phone: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    username: str
    role: int

class ConfigSave(BaseModel):
    components: dict
    totalPrice: int
    totalPower: str
    name: Optional[str] = None

# === ИНИЦИАЛИЗАЦИЯ ===
@app.on_event("startup")
def on_startup():
    if DB_AVAILABLE:
        try:
            init_db()
            print("✅ ForgePower DB инициализирована")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации: {e}")

# === СТРАНИЦЫ ===
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return FileResponse("login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return FileResponse("register.html")

@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    return FileResponse("profile.html")

@app.get("/configurator", response_class=HTMLResponse)
async def configurator_page():
    return FileResponse("configurator.html")

# === API ===

@app.post("/token", response_model=Token)
async def login(form_data, OAuth2PasswordRequestForm = Depends()):
    if not DB_AVAILABLE:
        if form_data.username == "admin" and form_data.password == "admin123":
            access_token = create_access_token(data={"sub": "admin"})
            return {"access_token": access_token, "token_type": "bearer", 
                    "expires_in": ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, 
                    "username": "admin", "role": 4}
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    if not verify_password(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    user = get_user(form_data.username)
    access_token = create_access_token(data={"sub": user["user_name"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        "username": user["user_name"],
        "role": user.get("role", 1)
    }

@app.get("/me")
async def read_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["user_name"],
        "email": current_user.get("user_email", ""),
        "phone": current_user.get("user_phone", ""),
        "role": current_user.get("role", 1),
        "avatar": current_user.get("user_img", "")
    }

@app.post("/register")
async def register(user: UserRegister):
    if not DB_AVAILABLE:
        raise HTTPException(500, detail="База данных недоступна")
    if not check_user(user.username):
        raise HTTPException(400, detail="Пользователь уже существует")
    if not check_email(user.email):
        raise HTTPException(400, detail="Email уже зарегистрирован")
    if not check_phone(user.phone):
        raise HTTPException(400, detail="Телефон уже зарегистрирован")
    
    result = create_user(name=user.username, password=user.password, 
                         email=user.email, phone=user.phone)
    if result is True or (isinstance(result, dict) and result.get("success")):
        return {"message": "Регистрация успешна", "username": user.username}
    raise HTTPException(400, detail="Ошибка регистрации")

@app.post("/api/user/update")
async def update_user(update_data: UserUpdate, 
                      current_user: dict = Depends(get_current_user)):
    if not DB_AVAILABLE:
        raise HTTPException(500, detail="База данных недоступна")
    
    from include.database.mongo.main import db
    coll = db["users"]
    update_dict = {}
    
    if update_data.username and update_data.username.strip():
        if update_data.username != current_user["user_name"]:
            if not check_user(update_data.username):
                raise HTTPException(400, detail="Имя уже занято")
            update_dict["user_name"] = update_data.username
    
    if update_data.email and update_data.email.strip():
        if update_data.email != current_user.get("user_email"):
            if not check_email(update_data.email):
                raise HTTPException(400, detail="Email уже зарегистрирован")
            update_dict["user_email"] = update_data.email
    
    if update_data.phone and update_data.phone.strip():
        if update_data.phone != current_user.get("user_phone"):
            if not check_phone(update_data.phone):
                raise HTTPException(400, detail="Телефон уже зарегистрирован")
            update_dict["user_phone"] = update_data.phone
    
    if update_data.password and update_data.password.strip():
        update_dict["user_password"] = _hash_password(update_data.password)
    
    if update_dict:
        coll.update_one({"user_name": current_user["user_name"]}, {"$set": update_dict})
    
    return {"message": "Данные обновлены", 
            "username": update_dict.get("user_name", current_user["user_name"])}

@app.post("/api/user/avatar")
async def upload_avatar(avatar: UploadFile = File(...), 
                        current_user: dict = Depends(get_current_user)):
    if not avatar.content_type.startswith('image/'):
        raise HTTPException(400, detail="Только изображения")
    if avatar.size > 2 * 1024 * 1024:
        raise HTTPException(400, detail="Файл слишком большой")
    
    avatar_dir = "data/images/avatars"
    os.makedirs(avatar_dir, exist_ok=True)
    
    ext = os.path.splitext(avatar.filename)[1] or ".png"
    filename = f"{current_user['user_name']}_avatar{ext}"
    filepath = f"{avatar_dir}/{filename}"
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(avatar.file, buffer)
    
    update_image(current_user["user_name"], filepath)
    return {"avatar": f"/{filepath}"}

@app.delete("/api/user/delete")
async def delete_user(current_user: dict = Depends(get_current_user)):
    if not DB_AVAILABLE:
        raise HTTPException(500, detail="База данных недоступна")
    from include.database.mongo.main import db
    coll = db["users"]
    result = coll.delete_one({"user_name": current_user["user_name"]})
    if result.deleted_count == 0:
        raise HTTPException(404, detail="Пользователь не найден")
    return {"message": "Аккаунт удалён"}

@app.post("/api/config/save")
async def save_config(config_data: ConfigSave, 
                      current_user: dict = Depends(get_current_user)):
    """Сохранение сборки в БД"""
    if not DB_AVAILABLE:
        raise HTTPException(500, detail="База данных недоступна")
    
    from include.database.mongo.main import db
    coll = db["configs"]
    
    config_record = {
        "user_name": current_user["user_name"],
        "name": config_data.name or f"Сборка {datetime.utcnow().strftime('%d.%m.%Y')}",
        "components": config_data.components,
        "totalPrice": config_data.totalPrice,
        "totalPower": config_data.totalPower,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = coll.insert_one(config_record)
    return {"message": "Сборка сохранена", "id": str(result.inserted_id)}

@app.get("/api/config/list")
async def list_configs(current_user: dict = Depends(get_current_user)):
    """Получение списка сборок пользователя"""
    if not DB_AVAILABLE:
        raise HTTPException(500, detail="База данных недоступна")
    
    from include.database.mongo.main import db
    coll = db["configs"]
    
    configs = list(coll.find({"user_name": current_user["user_name"]}))
    for config in configs:
        config["_id"] = str(config["_id"])
    
    return {"configs": configs}

@app.post("/api/logout")
async def logout():
    return {"message": "Выход выполнен"}
app.mount("/", StaticFiles(directory="."))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=10000)
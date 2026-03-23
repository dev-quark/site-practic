from pymongo import MongoClient, ASCENDING
import hashlib
import os
import sys
from datetime import datetime

sys.path.append("./include")

mc = MongoClient("mongodb://localhost:27017/")
db = mc['sitedb']
users_collection = db['users']

users_collection.create_index([("user_name", ASCENDING)], unique=True)
users_collection.create_index([("user_email", ASCENDING)], sparse=True)
users_collection.create_index([("user_phone", ASCENDING)], sparse=True)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def check_user(username: str) -> bool:
    return users_collection.find_one({"user_name": username}) is not None

def check_email(email: str) -> bool:
    if not email:
        return False
    return users_collection.find_one({"user_email": email}) is not None

def check_phone(phone: str) -> bool:
    if not phone:
        return False
    return users_collection.find_one({"user_phone": phone}) is not None

def get_user(username: str) -> dict:
    return users_collection.find_one({"user_name": username})

def create_user(user_data: dict) -> dict:
    name = user_data.get("user_name")
    password = user_data.get("password")
    email = user_data.get("user_email")
    phone = user_data.get("user_phone")
    nickname = user_data.get("nickname", name)
    role = user_data.get("role", 1)
    
    if not name or not password:
        return None
    if check_user(name) or (email and check_email(email)) or (phone and check_phone(phone)):
        return None
    
    # === СОЗДАНИЕ АВАТАРА ===
    avatar_dir = "data/images/avatars"  # Путь на диске
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Путь к файлу на диске
    avatar_file_path = os.path.join(avatar_dir, f"{name}_avatar.png")
    
    # Создаём аватар если не существует
    if not os.path.exists(avatar_file_path):
        try:
            import include.gen_standart_image.main as gen_avatar
            gen_avatar.create_avatar_from_name(name, output_dir=avatar_dir)
        except Exception as e:
            print(f"⚠️ Не удалось создать аватар: {e}")
            # Создаём заглушку
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 200), color=(0, 212, 170))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), name[0].upper(), anchor="mm", fill="#1a1a2e", font_size=80)
            img.save(avatar_file_path)
    
    # 🔥 ВАЖНО: В БД сохраняем URL-путь (начинается с /), а не путь на диске!
    avatar_url = f"/data/images/avatars/{name}_avatar.png"
    
    document = {
        "user_name": name,
        "user_password": hash_password(password),
        "user_email": email,
        "user_phone": phone,
        "user_img": avatar_url,  # ← Сохраняем URL-путь!
        "nickname": nickname,
        "role": role,
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return document


def update_user_avatar(username: str, filename: str) -> str:
    """
    Обновляет путь к аватару в БД.
    Возвращает URL-путь для использования на фронтенде.
    """
    # 🔥 Формируем URL-путь (начинается с /)
    avatar_url = f"/data/images/avatars/{filename}"
    
    # Обновляем в БД
    users_collection.update_one(
        {"user_name": username},
        {"$set": {"user_img": avatar_url}}
    )
    
    return avatar_url

def update_user(username: str, update_data: dict) -> bool:
    if "user_password" in update_data:
        del update_data["user_password"]
    if not update_data:
        return True
    result = users_collection.update_one({"user_name": username}, {"$set": update_data})
    return result.modified_count > 0

def init():
    if users_collection.count_documents({}) == 0:
        create_user({
            "user_name": "admin",
            "password": "admin123",
            "user_email": "admin@pcbuilder.local",
            "nickname": "Administrator",
            "role": 4
        })
        print("✅ Админ создан: admin / admin123")

if __name__ == "__main__":
    init()
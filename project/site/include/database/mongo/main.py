"""
=== MongoDB Operations Module ===
Все операции с базой данных MongoDB
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import hashlib
import os
import sys
from datetime import datetime
from bson import ObjectId

sys.path.append("./include")

# === ПОДКЛЮЧЕНИЕ К БД ===
mc = MongoClient("mongodb://localhost:27017/")
db = mc['sitedb']
db1 = mc['configdb']

# Коллекции
users_collection = db['users']
software_collection = db['software']
builds_collection = db['builds']
requests_collection = db['requests']

# 🔥 КОЛЛЕКЦИИ КОМПОНЕНТОВ (из существующей структуры)
components_collections = {
    'cpu': db['cpu'],
    'gpu': db['gpu'],
    'ram': db['ozu'],  # Используем ozu
    'storage': db['storage'],
    'psu': db['pzu'],  # Используем pzu
    'case': db['frame'],  # Используем frame
    'mobo': db['motherboard'],
    'cooler': db['cooler'],
}

# === ИНДЕКСЫ ===
users_collection.create_index([("user_name", ASCENDING)], unique=True)
users_collection.create_index([("user_email", ASCENDING)], sparse=True)
users_collection.create_index([("user_phone", ASCENDING)], sparse=True)

builds_collection.create_index([("category", ASCENDING)])
builds_collection.create_index([("price", ASCENDING)])
builds_collection.create_index([("created_at", DESCENDING)])

requests_collection.create_index([("status", ASCENDING)])
requests_collection.create_index([("created_at", DESCENDING)])


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def serialize_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])  # 🔥 Конвертация ObjectId → str
    return doc


# === 🔥 ОПЕРАЦИИ С КОМПОНЕНТАМИ (ИСПРАВЛЕНО: db → db1) ===

def get_all_components(component_type: str = None) -> list:
    """Получение компонентов из раздельных коллекций"""
    
    collection_map = {
        'cpu': 'cpu',
        'gpu': 'gpu',
        'ram': 'ozu',
        'storage': 'storage',
        'psu': 'pzu',
        'case': 'frame',
        'mobo': 'motherboard',
        'cooler': 'cooler',
    }
    
    print(f"🔍 Запрос компонентов: type={component_type or 'all'}")
    print(f"🔍 Коллекции в db1: {db1.list_collection_names()}")  # 🔥 db1 вместо db
    
    if component_type and component_type in collection_map:
        coll_name = collection_map[component_type]
        collection = db1[coll_name]  # 🔥 db1 вместо db
        count = collection.count_documents({})
        print(f"📊 Коллекция '{coll_name}': {count} документов")
        
        docs = list(collection.find({}, {"_id": 0}).sort("name", 1))
        for doc in docs:
            doc['component_type'] = component_type
        print(f"✅ Возвращено: {len(docs)}")
        return docs
    else:
        all_components = []
        for comp_type, coll_name in collection_map.items():
            try:
                collection = db1[coll_name]  # 🔥 db1 вместо db
                count = collection.count_documents({})
                docs = list(collection.find({}, {"_id": 0}))
                for doc in docs:
                    doc['component_type'] = comp_type
                all_components.extend(docs)
                print(f"  {coll_name}: {count} документов")
            except Exception as e:
                print(f"  ⚠️ {coll_name}: ошибка - {e}")
        
        print(f"✅ Итого: {len(all_components)} компонентов")
        return all_components

def get_component_by_name(component_type: str, name: str) -> dict:
    """Получение компонента по имени из configdb"""
    configdb = db['configdb']
    doc = configdb.find_one({"type": component_type, "name": name}, {"_id": 0})
    return doc

def create_component(component_type: str, component_data: dict) -> dict:
    """Создание компонента в configdb"""
    configdb = db['configdb']
    
    component_data["type"] = component_type  # 🔥 Обязательно добавляем тип
    component_data["created_at"] = datetime.utcnow()
    component_data["updated_at"] = datetime.utcnow()
    
    result = configdb.insert_one(component_data)
    component_data["_id"] = str(result.inserted_id)
    return component_data

def update_component(component_type: str, name: str, update_data: dict) -> bool:
    """Обновление компонента в configdb"""
    configdb = db['configdb']
    update_data["updated_at"] = datetime.utcnow()
    
    result = configdb.update_one(
        {"type": component_type, "name": name},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_component(component_type: str, name: str) -> bool:
    """Удаление компонента из configdb"""
    configdb = db['configdb']
    result = configdb.delete_one({"type": component_type, "name": name})
    return result.deleted_count > 0


# ============================================
# === ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЯМИ ===
# ============================================

def check_user(username: str) -> bool:
    return users_collection.find_one({"user_name": username}) is not None

def check_email(email: str) -> bool:
    if not email:
        return False
    return users_collection.find_one({"user_email": email}) is not None

def get_user(username: str) -> dict:
    """Получение пользователя по имени"""
    doc = users_collection.find_one({"user_name": username})  # 🔥 Без {"_id": 0}!
    return serialize_doc(doc) if doc else None  # 🔥 Конвертируем _id в строку

def create_user(user_data: dict) -> dict:
    name = user_data.get("user_name")
    password = user_data.get("password")
    email = user_data.get("user_email")
    phone = user_data.get("user_phone")
    nickname = user_data.get("nickname", name)
    role = user_data.get("role", 1)
    
    if not name or not password:
        return None
    if check_user(name) or (email and check_email(email)):
        return None
    
    # Создание аватара
    avatar_dir = f"data/avatars/{name}"
    os.makedirs(avatar_dir, exist_ok=True)
    avatar_filename = f"{name}_avatar.png"
    avatar_file_path = os.path.join(avatar_dir, avatar_filename)
    
    if not os.path.exists(avatar_file_path):
        try:
            from include.gen_standart_image.main import generate_random_avatar
            generate_random_avatar(name, output_path=avatar_file_path, use_deterministic=True)
        except Exception as e:
            print(f"⚠️ Не удалось создать аватар: {e}")
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 200), color=(0, 212, 170))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), name[0].upper(), anchor="mm", fill="#1a1a2e", font_size=80)
            img.save(avatar_file_path)
    
    avatar_url = f"/data/avatars/{name}/{avatar_filename}"
    
    document = {
        "user_name": name,
        "user_password": password,  # Без хеширования для разработки
        "user_email": email,
        "user_phone": phone,
        "user_img": avatar_url,
        "avatar_url": avatar_url,
        "nickname": nickname,
        "role": role,
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return document


# ============================================
# === ОПЕРАЦИИ С ПРОГРАММНЫМ ОБЕСПЕЧЕНИЕМ ===
# ============================================

def get_all_po() -> list:
    cursor = software_collection.find({}, {"_id": 0})
    return list(cursor)

def get_po_by_id(po_id: str) -> dict:
    return software_collection.find_one({"id": po_id}, {"_id": 0})

def create_po(po_data: dict) -> dict:
    if software_collection.find_one({"id": po_data.get("id")}):
        return None
    po_data["created_at"] = datetime.utcnow()
    po_data["updated_at"] = datetime.utcnow()
    result = software_collection.insert_one(po_data)
    po_data["_id"] = str(result.inserted_id)
    return po_data

def update_po(po_id: str, update_data: dict) -> bool:
    update_data["updated_at"] = datetime.utcnow()
    result = software_collection.update_one({"id": po_id}, {"$set": update_data})
    return result.modified_count > 0

def delete_po(po_id: str) -> bool:
    result = software_collection.delete_one({"id": po_id})
    return result.deleted_count > 0


# ============================================
# === ОПЕРАЦИИ С СБОРКАМИ ПК ===
# ============================================

def get_all_builds(category: str = None, max_price: int = None, cpu_brand: str = None, only_published: bool = True, limit: int = 50) -> list:
    """Получение сборок с фильтрами"""
    query = {}
    if only_published:
        query["is_published"] = True
    if category:
        query["category"] = category
    if max_price:
        query["price"] = {"$lte": max_price}
    if cpu_brand:
        brand = "intel" if cpu_brand.lower() == "intel" else "amd"
        query["components.cpu"] = {"$regex": brand, "$options": "i"}
    
    # 🔥 ИСПРАВЛЕНО: убрали {"_id": 0} и добавили serialize_doc
    cursor = builds_collection.find(query).sort("created_at", -1).limit(limit)
    builds = list(cursor)
    return [serialize_doc(build) for build in builds]  # 🔥 Конвертируем _id в строку

def get_build_by_id(build_id: str, include_unpublished: bool = False) -> dict:
    """Получение сборки по ID"""
    from bson import ObjectId
    query = {"_id": ObjectId(build_id)}
    if not include_unpublished:
        query["is_published"] = True
    doc = builds_collection.find_one(query, {"_id": 0})
    return serialize_doc(doc) if doc else None

def create_build(build_data: dict) -> dict:
    """Создание новой сборки"""
    required = ["title", "category", "price", "components"]
    if not all(k in build_data for k in required):
        return None
    
    valid_categories = ["gaming", "work", "budget", "pro"]
    if build_data["category"] not in valid_categories:
        return None
    
    document = {
        "title": build_data["title"],
        "description": build_data.get("description", ""),
        "category": build_data["category"],
        "price": int(build_data["price"]),
        "components": build_data["components"],
        "image": build_data.get("image"),
        "is_published": build_data.get("is_published", True),
        "author_id": build_data.get("author_id"),
        "views": 0,
        "likes": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = builds_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_build(build_id: str, update_data: dict) -> bool:
    """Обновление сборки"""
    from bson import ObjectId
    protected = ["_id", "created_at", "views", "likes"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = builds_collection.update_one(
        {"_id": ObjectId(build_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_build(build_id: str) -> bool:
    """Удаление сборки"""
    from bson import ObjectId
    result = builds_collection.delete_one({"_id": ObjectId(build_id)})
    return result.deleted_count > 0


# ============================================
# === ОПЕРАЦИИ С ЗАПРОСАМИ ПОЛЬЗОВАТЕЛЕЙ ===
# ============================================

def get_all_requests(status_filter: str = None) -> list:
    query = {}
    if status_filter:
        query["status"] = status_filter
    cursor = requests_collection.find(query, {"_id": 0}).sort("created_at", DESCENDING)
    return list(cursor)

def create_request(request_data: dict) -> dict:
    document = {
        **request_data,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "admin_comment": None
    }
    result = requests_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_request_status(request_id: str, status: str, admin_comment: str = None) -> bool:
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    if admin_comment:
        update_data["admin_comment"] = admin_comment
    result = requests_collection.update_one({"_id": request_id}, {"$set": update_data})
    return result.modified_count > 0


# ============================================
# === ИНИЦИАЛИЗАЦИЯ ===
# ============================================

def init():
    """Инициализация БД: создание админа"""
    
    # Создание админа
    if users_collection.count_documents({}) == 0:
        create_user({
            "user_name": "admin",
            "password": "admin123",
            "user_email": "admin@pcbuilder.local",
            "nickname": "Administrator",
            "role": 4
        })
        print("✅ Админ создан: admin / admin123")
    
    # Проверка коллекций компонентов
    total_components = sum(coll.count_documents({}) for coll in components_collections.values())
    print(f"📦 Найдено компонентов: {total_components}")
    
    for type_name, collection in components_collections.items():
        count = collection.count_documents({})
        print(f"  - {type_name}: {count}")

# ============================================
# === 🔥 НОВЫЕ ОПЕРАЦИИ ДЛЯ АДМИН-ПАНЕЛИ ===
# ============================================

# === ЗАПРОСЫ (ЗАКАЗЫ) ===

def get_all_requests(status_filter: str = None, limit: int = 100) -> list:
    """Получение всех запросов с фильтрацией"""
    query = {}
    if status_filter and status_filter != 'all':
        query["status"] = status_filter
    
    cursor = requests_collection.find(query).sort("created_at", DESCENDING).limit(limit)
    return [serialize_doc(doc) for doc in cursor]

def create_request(request_data: dict) -> dict:
    """Создание нового запроса"""
    required = ["user_name", "request_type", "title"]
    if not all(k in request_data for k in required):
        return None
    
    document = {
        "user_name": request_data["user_name"],
        "user_email": request_data.get("user_email", ""),
        "request_type": request_data["request_type"],  # new_build, edit_build, component_request
        "title": request_data["title"],
        "description": request_data.get("description", ""),
        "budget": request_data.get("budget"),
        "components": request_data.get("components", {}),
        "status": "pending",  # pending, approved, rejected
        "admin_comment": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = requests_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_request_status(request_id: str, status: str, admin_comment: str = None) -> bool:
    """Обновление статуса запроса"""
    from bson import ObjectId
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    if admin_comment:
        update_data["admin_comment"] = admin_comment
    
    result = requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_request(request_id: str) -> bool:
    """Удаление запроса"""
    from bson import ObjectId
    result = requests_collection.delete_one({"_id": ObjectId(request_id)})
    return result.deleted_count > 0


# === ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ (ПО) ===

def get_all_software(category: str = None, search: str = None) -> list:
    """Получение списка ПО с фильтрами"""
    query = {}
    if category and category != 'all':
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"id": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = software_collection.find(query).sort("name", ASCENDING)
    return [serialize_doc(doc) for doc in cursor]

def get_software_by_id(po_id: str) -> dict:
    """Получение ПО по ID"""
    doc = software_collection.find_one({"id": po_id}, {"_id": 0})
    return doc

def create_software(po_data: dict) -> dict:
    """Создание нового ПО"""
    required = ["id", "name", "category", "link"]
    if not all(k in po_data for k in required):
        return None
    
    # Проверка уникальности ID
    if software_collection.find_one({"id": po_data["id"]}):
        return None
    
    document = {
        "id": po_data["id"],
        "name": po_data["name"],
        "category": po_data["category"],
        "link": po_data["link"],
        "description": po_data.get("description", ""),
        "version": po_data.get("version", ""),
        "size_mb": po_data.get("size_mb"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = software_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_software(po_id: str, update_data: dict) -> bool:
    """Обновление ПО"""
    protected = ["id", "_id", "created_at"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = software_collection.update_one(
        {"id": po_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_software(po_id: str) -> bool:
    """Удаление ПО"""
    result = software_collection.delete_one({"id": po_id})
    return result.deleted_count > 0


# === КОМПЛЕКТУЮЩИЕ ===

def get_all_components_by_type(component_type: str, search: str = None) -> list:
    """Получение компонентов по типу с поиском"""
    collection_map = {
        'cpu': 'cpu', 'gpu': 'gpu', 'ram': 'ozu', 'storage': 'storage',
        'psu': 'pzu', 'case': 'frame', 'mobo': 'motherboard', 'cooler': 'cooler'
    }
    
    if component_type not in collection_map:
        return []
    
    collection = db1[collection_map[component_type]]
    query = {}
    
    if search:
        query["$or"] = [
            {"model_name": {"$regex": search, "$options": "i"}},
            {"brand": {"$regex": search, "$options": "i"}},
            {"id": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = collection.find(query).sort("model_name", ASCENDING)
    components = []
    for doc in cursor:
        doc["component_type"] = component_type
        components.append(serialize_doc(doc))
    return components

def create_component(component_type: str, component_data: dict) -> dict:
    """Создание компонента"""
    collection_map = {
        'cpu': 'cpu', 'gpu': 'gpu', 'ram': 'ozu', 'storage': 'storage',
        'psu': 'pzu', 'case': 'frame', 'mobo': 'motherboard', 'cooler': 'cooler'
    }
    
    if component_type not in collection_map:
        return None
    
    collection = db1[collection_map[component_type]]
    
    # Генерация ID если не указан
    if not component_data.get("id"):
        component_data["id"] = f"{component_type}_{component_data.get('model_name', 'unknown').lower().replace(' ', '_')}"
    
    # Проверка уникальности
    if collection.find_one({"id": component_data["id"]}):
        return None
    
    document = {
        **component_data,
        "type": component_type,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_component(component_type: str, component_id: str, update_data: dict) -> bool:
    """Обновление компонента"""
    collection_map = {
        'cpu': 'cpu', 'gpu': 'gpu', 'ram': 'ozu', 'storage': 'storage',
        'psu': 'pzu', 'case': 'frame', 'mobo': 'motherboard', 'cooler': 'cooler'
    }
    
    if component_type not in collection_map:
        return False
    
    collection = db1[collection_map[component_type]]
    protected = ["id", "_id", "created_at", "type"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = collection.update_one(
        {"id": component_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_component(component_type: str, component_id: str) -> bool:
    """Удаление компонента"""
    collection_map = {
        'cpu': 'cpu', 'gpu': 'gpu', 'ram': 'ozu', 'storage': 'storage',
        'psu': 'pzu', 'case': 'frame', 'mobo': 'motherboard', 'cooler': 'cooler'
    }
    
    if component_type not in collection_map:
        return False
    
    collection = db1[collection_map[component_type]]
    result = collection.delete_one({"id": component_id})
    return result.deleted_count > 0


# === СБОРКИ ПК ===

def get_all_builds_admin(category: str = None, search: str = None, include_unpublished: bool = True) -> list:
    """Получение сборок для админ-панели"""
    query = {}
    if not include_unpublished:
        query["is_published"] = True
    if category and category != 'all':
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = builds_collection.find(query).sort("created_at", DESCENDING)
    return [serialize_doc(doc) for doc in cursor]

def get_build_admin(build_id: str) -> dict:
    """Получение сборки для админ-панели (с _id)"""
    from bson import ObjectId
    doc = builds_collection.find_one({"_id": ObjectId(build_id)})
    return serialize_doc(doc) if doc else None

def create_build_admin(build_data: dict, author_id: str = None) -> dict:
    """Создание сборки (админ)"""
    required = ["title", "category", "price", "components"]
    if not all(k in build_data for k in required):
        return None
    
    valid_categories = ["gaming", "work", "budget", "pro"]
    if build_data["category"] not in valid_categories:
        return None
    
    document = {
        "title": build_data["title"],
        "description": build_data.get("description", ""),
        "category": build_data["category"],
        "price": int(build_data["price"]),
        "components": build_data["components"],
        "image": build_data.get("image"),
        "is_published": build_data.get("is_published", True),
        "author_id": author_id,
        "views": 0,
        "likes": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = builds_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_build_admin(build_id: str, update_data: dict) -> bool:
    """Обновление сборки (админ)"""
    from bson import ObjectId
    protected = ["_id", "created_at", "views", "likes", "author_id"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = builds_collection.update_one(
        {"_id": ObjectId(build_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_build_admin(build_id: str) -> bool:
    """Удаление сборки (админ)"""
    from bson import ObjectId
    result = builds_collection.delete_one({"_id": ObjectId(build_id)})
    return result.deleted_count > 0


# === ПОЛЬЗОВАТЕЛИ ===

def get_all_users(search: str = None, role_filter: int = None) -> list:
    """Получение списка пользователей"""
    query = {}
    if role_filter and role_filter > 0:
        query["role"] = role_filter
    if search:
        query["$or"] = [
            {"user_name": {"$regex": search, "$options": "i"}},
            {"user_email": {"$regex": search, "$options": "i"}},
            {"nickname": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = users_collection.find(query, {"user_password": 0}).sort("created_at", DESCENDING)
    return [serialize_doc(doc) for doc in cursor]

def get_user_admin(username: str) -> dict:
    """Получение пользователя для админ-панели (без пароля)"""
    doc = users_collection.find_one({"user_name": username}, {"user_password": 0})
    return serialize_doc(doc) if doc else None

def update_user_role(username: str, new_role: int) -> bool:
    """Обновление роли пользователя"""
    valid_roles = [1, 2, 3, 4]
    if new_role not in valid_roles:
        return False
    
    result = users_collection.update_one(
        {"user_name": username},
        {"$set": {"role": new_role, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0

def update_user_profile(username: str, update_data: dict) -> bool:
    """Обновление профиля пользователя"""
    protected = ["user_name", "_id", "created_at", "user_password"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = users_collection.update_one(
        {"user_name": username},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_user(username: str) -> bool:
    """Удаление пользователя"""
    # Нельзя удалить самого себя или админа с ролью 4
    if username == "admin":
        return False
    
    result = users_collection.delete_one({"user_name": username})
    return result.deleted_count > 0

# ============================================
# === 🔥 ОПЕРАЦИИ С ГЛОССАРИЕМ ===
# ============================================

def get_all_glossary(category: str = None, search: str = None) -> list:
    """Получение терминов глоссария с фильтрами"""
    query = {}
    if category and category != 'all':
        query["category"] = category
    if search:
        query["$or"] = [
            {"term": {"$regex": search, "$options": "i"}},
            {"definition": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = db['glossary'].find(query).sort("term", ASCENDING)
    return [serialize_doc(doc) for doc in cursor]

def get_glossary_term(term: str) -> dict:
    """Получение термина по названию"""
    doc = db['glossary'].find_one({"term": term}, {"_id": 0})
    return doc

def create_glossary(term_data: dict) -> dict:
    """Создание нового термина"""
    required = ["term", "definition"]
    if not all(k in term_data for k in required):
        return None
    
    # Проверка уникальности
    if db['glossary'].find_one({"term": term_data["term"]}):
        return None
    
    document = {
        "term": term_data["term"],
        "definition": term_data["definition"],
        "category": term_data.get("category", "general"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db['glossary'].insert_one(document)
    document["_id"] = str(result.inserted_id)
    return serialize_doc(document)

def update_glossary(term: str, update_data: dict) -> bool:
    """Обновление термина"""
    protected = ["term", "_id", "created_at"]
    for field in protected:
        update_data.pop(field, None)
    update_data["updated_at"] = datetime.utcnow()
    
    result = db['glossary'].update_one(
        {"term": term},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_glossary(term: str) -> bool:
    """Удаление термина"""
    result = db['glossary'].delete_one({"term": term})
    return result.deleted_count > 0
if __name__ == "__main__":
    init()
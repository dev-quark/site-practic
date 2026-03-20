from pymongo import MongoClient
import hashlib, sys
sys.path.append("./include")
mc= MongoClient("mongodb://localhost:27017")
import include.gen_standart_image.main as gen_standart_image
 
db= mc['sitedb']

def create_users_table(admin_login, admin_password,admin_email,admin_phone,admin_url):
    coll = db['users']
    coll.insert_one(
        {
            "user_name": admin_login, 
            "user_email": admin_email,
            "user_phone": admin_phone,
            "user_img": admin_url,
            "user_password": hashlib.sha256(admin_password.encode('utf-8')).hexdigest(), 
            "role":4
            }

         )
def get_user(name):
    coll = db["users"]
    return coll.find_one({"user_name":name})
def create_user(name , password, email, phone):
    coll = db["users"]
    if check_user(name) == True:
        if check_email(email) == True:
            if check_phone(phone) == True:
                gen_standart_image.create_avatar_from_name(
                    name
                )
                coll.insert_one(
                    { 
                        "user_name": name,
                        "user_email": email,
                        "user_phone": phone,
                        "user_img": f"data/images/avatars/{name}_avatar.png",
                        "user_password": hashlib.sha256(password.encoding("UTF-8")),
                        "role": 1
                    }
                    )
        return True
    else:
        return False
def update_image(name, image_dir):
    coll = db["users"]
    coll.replace_one(
        {"user_name": name},
        {"user_img": image_dir}
                     )
def del_image(name):
    coll = db["users"]
    gen_standart_image.create_avatar_from_name(
                    name
                )
    coll.replace_one(
        {"user_name": name},
        {"user_img": f"data/images/avatars/{name}_avatar.png"}
                     )
def get_users()->list:
    cur = db["users"].find()
    return list(cur)
def check_user(name)->bool:
    result = get_users()
    for i in result:
        if i["user_name"] == name:
            return False
    return True
def check_email(email)->bool:
    result = get_users()
    for i in result:
        if i["user_email"] == email:
            return False
    return True
def check_phone(phone)->bool:
    result = get_users()
    for i in result:
        if i["user_phone"] == phone:
            return False
    return True
def get_user_data(user_name):
    data = get_users
    for i in get_users:
        if i["user_name"] == user_name:
            return i
def check_password(user_name, password):
    result = get_user_data(user_name)
    if result["user_password"] == password:
        return True
    return False
def check_user_password(user_name, password):
    hash_passw = hashlib.sha256(password.encofing("UTF-8"))
    if check_password(user_name, hash_passw) == False:
        return False
    else:
        return True
def change_role(admin_name, user_name, role):
    admin_role = get_user(admin_name)["role"]
    if admin_role < role:
        return False
    else:
        coll = db["users"]
        coll.replace_one(
        {"user_name": user_name},
        {"user_role": role}
                     )
def init():
    create_users_table("admin", "admin123")
print(check_user("quark"))
    
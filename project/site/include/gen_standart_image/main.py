"""
=== Генератор случайных аватаров для PC Builder ===
Создаёт уникальные аватары с случайными цветами, узорами и элементами
"""

from PIL import Image, ImageDraw, ImageFont
import random
import hashlib
import os

# === 🔥 ПАЛИТРЫ ЦВЕТОВ ===
COLOR_PALETTES = {
    'warm': ['#FF6B6B', '#FFD93D', '#FF8C42', '#F7C548', '#FFD166'],
    'cool': ['#00D4AA', '#4ECDC4', '#45B7D1', '#96CEB4', '#88D8B0'],
    'vivid': ['#FF0080', '#7B2CBF', '#3A0CA3', '#4361EE', '#4CC9F0'],
    'earth': ['#8B7355', '#A0826D', '#B8956A', '#D4B483', '#E8D5B5'],
    'dark': ['#1A1A2E', '#16213E', '#0F3460', '#533483', '#E94560'],
    'pastel': ['#FFB5E8', '#B5DEFF', '#DCD3FF', '#FFDFBA', '#BAFFC9'],
}

# === 🔥 ГЕОМЕТРИЧЕСКИЕ ФИГУРЫ ===
SHAPES = ['circle', 'square', 'triangle', 'hexagon', 'diamond']

# === 🔥 УЗОРЫ ===
PATTERNS = ['solid', 'gradient', 'stripes', 'dots', 'grid']


def get_deterministic_seed(username: str) -> int:
    """Генерация детерминированного seed на основе username"""
    return int(hashlib.md5(username.encode()).hexdigest()[:8], 16)


def generate_random_avatar(
    username: str,
    size: int = 200,
    output_path: str = None,
    use_deterministic: bool = True
) -> Image.Image:
    """
    Генерация случайного аватара
    
    :param username: Имя пользователя (для детерминированной генерации)
    :param size: Размер аватара в пикселях
    :param output_path: Путь для сохранения (если None — не сохранять)
    :param use_deterministic: Если True — одинаковый username = одинаковый аватар
    :return: PIL Image объект
    """
    
    # 🔥 Инициализация random seed
    if use_deterministic:
        seed = get_deterministic_seed(username)
        random.seed(seed)
    else:
        random.seed()
    
    # Создание изображения
    img = Image.new('RGB', (size, size), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # 🔥 Генерация фона
    palette_name = random.choice(list(COLOR_PALETTES.keys()))
    palette = COLOR_PALETTES[palette_name]
    bg_color = random.choice(palette)
    pattern = random.choice(PATTERNS)
    
    # Рисуем фон
    if pattern == 'solid':
        draw.rectangle([0, 0, size, size], fill=bg_color)
    
    elif pattern == 'gradient':
        color2 = random.choice(palette)
        for i in range(size):
            r1, g1, b1 = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
            r = int(r1 + (r2 - r1) * i / size)
            g = int(g1 + (g2 - g1) * i / size)
            b = int(b1 + (b2 - b1) * i / size)
            draw.line([(0, i), (size, i)], fill=(r, g, b))
    
    elif pattern == 'stripes':
        stripe_width = random.randint(10, 30)
        for i in range(0, size, stripe_width * 2):
            draw.rectangle([0, i, size, i + stripe_width], fill=bg_color)
    
    elif pattern == 'dots':
        dot_size = random.randint(5, 15)
        dot_spacing = random.randint(20, 40)
        for x in range(0, size, dot_spacing):
            for y in range(0, size, dot_spacing):
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-5, 5)
                draw.ellipse([
                    x + offset_x - dot_size//2,
                    y + offset_y - dot_size//2,
                    x + offset_x + dot_size//2,
                    y + offset_y + dot_size//2
                ], fill=bg_color)
    
    elif pattern == 'grid':
        grid_size = random.randint(20, 50)
        for x in range(0, size, grid_size):
            draw.line([(x, 0), (x, size)], fill=bg_color, width=2)
        for y in range(0, size, grid_size):
            draw.line([(0, y), (size, y)], fill=bg_color, width=2)
    
    # 🔥 Добавляем геометрические фигуры на фон
    num_shapes = random.randint(2, 5)
    for _ in range(num_shapes):
        shape = random.choice(SHAPES)
        shape_color = random.choice(palette)
        shape_size = random.randint(20, 60)
        x = random.randint(0, size - shape_size)
        y = random.randint(0, size - shape_size)
        
        if shape == 'circle':
            draw.ellipse([x, y, x + shape_size, y + shape_size], fill=shape_color, outline=shape_color)
        elif shape == 'square':
            draw.rectangle([x, y, x + shape_size, y + shape_size], fill=shape_color, outline=shape_color)
        elif shape == 'triangle':
            points = [
                (x + shape_size//2, y),
                (x, y + shape_size),
                (x + shape_size, y + shape_size)
            ]
            draw.polygon(points, fill=shape_color, outline=shape_color)
        elif shape == 'diamond':
            points = [
                (x + shape_size//2, y),
                (x + shape_size, y + shape_size//2),
                (x + shape_size//2, y + shape_size),
                (x, y + shape_size//2)
            ]
            draw.polygon(points, fill=shape_color, outline=shape_color)
        elif shape == 'hexagon':
            cx, cy = x + shape_size//2, y + shape_size//2
            r = shape_size//2
            points = []
            for i in range(6):
                angle = 3.14159 * 2 * i / 6
                px = cx + r * 0.866 * 2 * (1 if i % 2 == 0 else 0.5) * (1 if i < 3 else -1)
                py = cy + r * (1 if i < 3 else -1)
                points.append((px, py))
            draw.polygon(points, fill=shape_color, outline=shape_color)
    
    # 🔥 Добавляем первую букву ника
    initial = username[0].upper() if username else '?'
    
    # Пытаемся загрузить шрифт
    try:
        font_size = size // 2
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Цвет текста — контрастный к фону
    text_color = '#FFFFFF' if sum(int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)) < 400 else '#1A1A2E'
    
    # Рисуем текст по центру
    bbox = draw.textbbox((0, 0), initial, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2
    draw.text((text_x, text_y), initial, fill=text_color, font=font)
    
    # 🔥 Сохранение
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, 'PNG')
        print(f"✅ Аватар сохранён: {output_path}")
    
    return img


def regenerate_all_avatars():
    """Перегенерация аватаров для всех пользователей"""
    from include.database.mongo.main import users_collection
    import os
    
    users = list(users_collection.find({}))
    print(f"🔍 Найдено {len(users)} пользователей")
    
    for user in users:
        username = user.get("user_name")
        if not username:
            continue
        
        avatar_path = f"data/avatars/{username}/{username}_avatar.png"
        
        print(f"🎨 Генерация аватара для: {username}")
        generate_random_avatar(username, output_path=avatar_path)
        
        avatar_url = f"/data/avatars/{username}/{username}_avatar.png"
        users_collection.update_one(
            {"user_name": username},
            {"$set": {"user_img": avatar_url, "avatar_url": avatar_url}}
        )
        print(f"✅ Аватар обновлён: {avatar_url}")
    
    print("✅ Готово!")


if __name__ == "__main__":
    # Тест генерации
    print("🎨 Тест генерации аватара...")
    generate_random_avatar("testuser", output_path="test_avatar.png")
    print("✅ Тест завершён!")
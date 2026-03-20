from PIL import Image, ImageDraw, ImageFont
import random

def create_avatar_from_name(user_name, size=512):
    letter = user_name.strip()[0].upper()
    
    colors = [
        ((65, 105, 225), (255, 255, 255)),   # Синий
        ((46, 204, 113), (255, 255, 255)),   # Зелёный
        ((155, 89, 182), (255, 255, 255)),   # Фиолетовый
        ((231, 76, 60), (255, 255, 255)),    # Красный
        ((241, 196, 15), (0, 0, 0)),         # Жёлтый
        ((52, 152, 219), (255, 255, 255)),   # Голубой
    ]
    bg_color, text_color = random.choice(colors)
    
    img = Image.new('RGB', (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    text = letter
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill=text_color, font=font)
    filename = f"data/images/avatars/{user_name}_avatar.png"
    img.save(filename)
    return filename
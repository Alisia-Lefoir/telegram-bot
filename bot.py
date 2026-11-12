import asyncio
import json
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BotCommand

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "9165585222:AAFIxaapFWfBT46DoUAYt_dKupLwrJOHVVI"
ADMIN_IDS = {6176354358}
DATA_FILE = Path("scales_data.json")
# ===============================================

SCALES = {
    "sympathy": "Симпатия",
    "trust": "Доверие",
    "mental": "Психсостояние",
    "finance": "Финансовое удовлетворение"
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    
    return {
        "scales": {
            key: {"value": 0, "desc": "Пояснение пока не задано"} 
            for key in SCALES
        },
        "photo_id": None,
        "users": []
    }

def save_data(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def make_progress_bar(percent: int, length: int = 16) -> str:
    percent = max(0, min(100, percent))
    filled = round(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {percent}%"

def format_scales_text(data: dict) -> str:
    lines = ["📊 <b>Текущие шкалы:</b>\n"]
    for key, title in SCALES.items():
        scale = data["scales"].get(key, {"value": 0, "desc": ""})
        bar = make_progress_bar(scale["value"])
        desc = scale.get("desc", "")
        lines.append(f"<b>{title}</b>\n<code>{bar}</code>\n<i>{desc}</i>\n")
    return "\n".join(lines)

async def notify_all_users(text: str, photo_id: str | None = None):
    data = load_data()
    users = data.get("users", [])
    
    for user_id in users:
        try:
            if photo_id:
                await bot.send_photo(user_id, photo=photo_id, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(user_id, text, parse_mode="HTML")
        except Exception:
            pass

@dp.message(Command("start"))
async def cmd_start(message: Message):
    data = load_data()
    
    if message.from_user.id not in data["users"]:
        data["users"].append(message.from_user.id)
        save_data(data)
    
    text = (
        "Привет! Этот бот был создан, чтобы ты мог легко отследить моё состояние. "
        "Сама говорить я не могу, поэтому вот тебе костыль.\n\n"
        "Нажми /scales чтобы посмотреть текущие шкалы."
    )
    await message.answer(text)

@dp.message(Command("scales", "шкалы", "scale"))
async def cmd_scales(message: Message):
    data = load_data()
    text = format_scales_text(data)
    photo_id = data.get("photo_id")
    
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@dp.message(Command("set"))
async def cmd_set(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    if not command.args:
        return await message.answer("Пример: <code>/set mental 70</code>", parse_mode="HTML")
        
        parts = command.args.strip().split(maxsplit=1)
    if len(parts) != 2:
        return await message.answer("Нужно: /set <шкала> <число>")

    scale_key, value_str = parts
    scale_key = scale_key.lower()

    if scale_key not in SCALES:
        return await message.answer("Неизвестная шкала. Доступны: sympathy, trust, mental, finance")

    try:
        value = int(value_str)
        if not 0 <= value <= 100:
            raise ValueError
    except ValueError:
        return await message.answer("Число должно быть от 0 до 100")

    data = load_data()
    data["scales"][scale_key]["value"] = value
    save_data(data)

    title = SCALES[scale_key]
    await message.answer(f"✅ {title} = {value}%")

    text = format_scales_text(data)
    await notify_all_users(text, data.get("photo_id"))

@dp.message(Command("desc"))
async def cmd_desc(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    if not command.args:
        return await message.answer("Пример: <code>/desc mental Чувствую себя хорошо</code>", parse_mode="HTML")

    parts = command.args.strip().split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Нужно: /desc <шкала> <текст пояснения>")

    scale_key, desc_text = parts
    scale_key = scale_key.lower()

    if scale_key not in SCALES:
        return await message.answer("Неизвестная шкала")

    data = load_data()
    data["scales"][scale_key]["desc"] = desc_text
    save_data(data)

    title = SCALES[scale_key]
    await message.answer(f"✅ Пояснение для «{title}» обновлено")

    text = format_scales_text(data)
    await notify_all_users(text, data.get("photo_id"))

@dp.message(Command("update"))
async def cmd_update(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    if not command.args:
        return await message.answer(
            "Пример использования:\n\n"
            "<code>/update\n"
            "sympathy 70 Мне приятно\n"
            "trust 55 Пока осторожно\n"
            "mental 80 Хороший день\n"
            "finance 40 Стабильно</code>",
            parse_mode="HTML"
        )
        
        data = load_data()
    lines = command.args.strip().splitlines()
    updated = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue

        scale_key = parts[0].lower()
        if scale_key not in SCALES:
            continue

        try:
            value = int(parts[1])
            if not 0 <= value <= 100:
                continue
        except ValueError:
            continue

        desc = parts[2] if len(parts) > 2 else data["scales"][scale_key]["desc"]

        data["scales"][scale_key]["value"] = value
        data["scales"][scale_key]["desc"] = desc
        updated.append(SCALES[scale_key])

    if not updated:
        return await message.answer("Не удалось обновить ни одну шкалу. Проверь формат.")

    save_data(data)
    await message.answer(f"✅ Обновлено: {', '.join(updated)}")

    text = format_scales_text(data)
    await notify_all_users(text, data.get("photo_id"))

@dp.message(Command("photo"))
async def cmd_photo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.answer("Ответь командой /photo на сообщение с картинкой")

    photo = message.reply_to_message.photo[-1]
    file_id = photo.file_id

    data = load_data()
    data["photo_id"] = file_id
    save_data(data)

    await message.answer("✅ Картинка установлена")

    text = format_scales_text(data)
    await notify_all_users(text, file_id)

async def set_commands():
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="scales", description="Показать текущие шкалы"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_commands()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

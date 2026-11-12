import asyncio
import json
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BotCommand

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "9165585222:AAFIxaapFWfBT46DoUAYt_dKupLwrJOHVVI"
ADMIN_IDS = {6176354358}

# JSONBin
BIN_ID = "6af5cd37ffd5d16053bc48de"
MASTER_KEY = "$2a$10$xBcxd07zkBb8zVDGagT/7uoHRL/t3LaWwHhi0/e7zGibQ5Y27l7Oe"
# ===============================================

SCALES = {
    "sympathy": "Симпатия",
    "trust": "Доверие",
    "mental": "Психсостояние",
    "finance": "Финансовое удовлетворение"
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DEFAULT_DATA = {
    "scales": {
        key: {"value": 0, "desc": "Пояснение пока не задано"}
        for key in SCALES
    },
    "photo_id": None,
    "users": []
}

async def load_data() -> dict:
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    headers = {"X-Master-Key": MASTER_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("record", DEFAULT_DATA)
    except Exception as e:
        print("Ошибка загрузки данных:", e)

    return DEFAULT_DATA.copy()

async def save_data(data: dict):
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
    headers = {
        "X-Master-Key": MASTER_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=data) as resp:
                if resp.status not in (200, 201):
                    print("Ошибка сохранения:", await resp.text())
    except Exception as e:
        print("Ошибка сохранения данных:", e)

def make_progress_bar(percent: int, length: int = 16) -> str:
    percent = max(0, min(100, int(percent)))
    filled = round(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {percent}%"

def format_scales_text(data: dict) -> str:
    lines = ["📊 <b>Текущие шкалы:</b>\n"]
    for key, title in SCALES.items():
        scale = data["scales"].get(key, {"value": 0, "desc": ""})
        bar = make_progress_bar(scale.get("value", 0))
        desc = scale.get("desc", "")
        lines.append(f"<b>{title}</b>\n<code>{bar}</code>\n<i>{desc}</i>\n")
    return "\n".join(lines)

async def notify_all_users(text: str, photo_id: Optional[str] = None):
    data = await load_data()
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
    data = await load_data()

    if message.from_user.id not in data.get("users", []):
        data.setdefault("users", []).append(message.from_user.id)
        await save_data(data)

    text = (
        "Привет! Этот бот был создан, чтобы ты мог легко отследить моё состояние. "
        "Сама говорить я не могу, поэтому вот тебе костыль.\n\n"
        "Нажми /scales чтобы посмотреть текущие шкалы."
    )
    await message.answer(text)

@dp.message(Command("scales", "шкалы", "scale"))
async def cmd_scales(message: Message):
    data = await load_data()
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

    scale_key = parts[0].lower()
    if scale_key not in SCALES:
        return await message.answer("Неизвестная шкала. Доступны: sympathy, trust, mental, finance")

    try:
        value = int(parts[1])
        if not 0 <= value <= 100:
            raise ValueError
    except ValueError:
        return await message.answer("Число должно быть от 0 до 100")

    data = await load_data()
    data["scales"][scale_key]["value"] = value
    await save_data(data)

    await message.answer(f"✅ {SCALES[scale_key]} = {value}%")

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
        return await message.answer("Нужно: /desc <шкала> <текст>")

    scale_key = parts[0].lower()
    if scale_key not in SCALES:
        return await message.answer("Неизвестная шкала")

    data = await load_data()
    data["scales"][scale_key]["desc"] = parts[1]
    await save_data(data)

    await message.answer(f"✅ Пояснение для «{SCALES[scale_key]}» обновлено")

    text = format_scales_text(data)
    await notify_all_users(text, data.get("photo_id"))

@dp.message(Command("update"))
async def cmd_update(message: Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    # Пробуем получить текст разными способами
    text = (command.args or "").strip()
    
    if not text:
        raw = message.text or ""
        if raw.lower().startswith("/update"):
            text = raw[7:].strip()

    # === ОТЛАДКА ===
    await message.answer(f"Полученный текст:\n<code>{text if text else 'пусто'}</code>", parse_mode="HTML")
    # ===============

    if not text:
        return await message.answer(
            "Отправь так (одним сообщением):\n\n"
            "<code>/update\n"
            "sympathy 90 Я тебя люблю\n"
            "trust 75 Доверяю\n"
            "mental 60 Устала\n"
            "finance 80 Спокойно</code>",
            parse_mode="HTML"
        )

    data = await load_data()
    updated = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split(maxsplit=2)
        if len(parts) < 2:
            continue

        key = parts[0].lower()
        if key not in SCALES:
            continue

        try:
            value = int(parts[1])
            if not 0 <= value <= 100:
                continue
        except ValueError:
            continue

        desc = parts[2] if len(parts) > 2 else data["scales"][key].get("desc", "")
        data["scales"][key]["value"] = value
        data["scales"][key]["desc"] = desc
        updated.append(SCALES[key])

    if not updated:
        return await message.answer("Не удалось распознать ни одной шкалы.")

    await save_data(data)
    await message.answer("✅ Обновлено: " + ", ".join(updated))
    await notify_all_users(format_scales_text(data), data.get("photo_id"))

@dp.message(Command("photo"))
async def cmd_photo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Только администратор")

    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.answer("Ответь командой /photo на сообщение с картинкой")

    photo = message.reply_to_message.photo[-1]
    file_id = photo.file_id

    data = await load_data()
    data["photo_id"] = file_id
    await save_data(data)

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
    print("Бот запущен...", flush=True)
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

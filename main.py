import os
import logging
import subprocess
import socket
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from wakeonlan import send_magic_packet

# Настройка логирования для Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Важно для Railway
)
logger = logging.getLogger(__name__)

# Получение переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_USER_IDS = [int(id_) for id_ in os.getenv('ALLOWED_USER_IDS', '916373186').split(',')]
PC_MAC_ADDRESS = os.getenv('PC_MAC_ADDRESS', 'B4:2E:99:EA:D7:0E')
PC_IP_ADDRESS = os.getenv('PC_IP_ADDRESS', '192.168.31.193')

# Проверка обязательных переменных
if not TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")

logger.info('Бот запускается...')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⚠️ У вас нет доступа к этому боту.")
        logger.warning(f"Попытка доступа от неавторизованного пользователя: {user_id}")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 Статус ПК", callback_data="status")],
        [
            InlineKeyboardButton("🟢 Включить ПК", callback_data="turn_on"),
            InlineKeyboardButton("🔴 Выключить ПК", callback_data="turn_off"),
        ]
    ]
    
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n"
        "Используйте кнопки ниже для управления вашим ПК:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ALLOWED_USER_IDS:
        await query.edit_message_text("⚠️ У вас нет доступа к этой функции.")
        return
    
    try:
        if query.data == "status":
            status = check_pc_status()
            await query.edit_message_text(text=f"Статус ПК: {status}")
        elif query.data == "turn_on":
            result = await turn_on_pc()
            await query.edit_message_text(text=result)
        elif query.data == "turn_off":
            result = await turn_off_pc()
            await query.edit_message_text(text=result)
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}")
        await query.edit_message_text("⚠️ Произошла ошибка при обработке запроса")

async def check_pc_status() -> str:
    """Проверка статуса ПК с обработкой для Railway"""
    try:
        # Для Railway используем socket вместо ping
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((PC_IP_ADDRESS, 3389))  # Проверяем порт RDP
            return "🟢 Включен" if result == 0 else "🔴 Выключен"
    except Exception as e:
        logger.error(f"Ошибка проверки статуса: {e}")
        return "⚠️ Не удалось проверить статус"

async def turn_on_pc() -> str:
    """Включение ПК через WOL"""
    try:
        if "Включен" in await check_pc_status():
            return "ПК уже включен"
            
        send_magic_packet(PC_MAC_ADDRESS)
        return "🟢 Сигнал Wake-on-LAN отправлен. ПК должен включиться в течение 1-2 минут."
    except Exception as e:
        logger.error(f"Ошибка включения: {e}")
        return "⚠️ Не удалось отправить команду включения"

async def turn_off_pc() -> str:
    """Универсальное выключение для Railway"""
    try:
        # Для Railway используем HTTP-запрос к локальному серверу на ПК
        # (нужно настроить сервер на целевом ПК)
        return "🔴 Выключение через Railway не поддерживается напрямую. Используйте другие методы."
    except Exception as e:
        logger.error(f"Ошибка выключения: {e}")
        return "⚠️ Не удалось выполнить выключение"

def main() -> None:
    """Запуск приложения с обработкой ошибок для Railway"""
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработка ошибок
    application.add_error_handler(lambda u, c: logger.error(f"Ошибка: {c.error}"))
    
    logger.info("Бот запущен и ожидает сообщений...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
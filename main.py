import os
import logging
import subprocess
import socket
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from wakeonlan import send_magic_packet

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print('Бот запущен')

# Получение токена бота и других параметров из переменных окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ALLOWED_USER_IDS = [int(user_id) for user_id in os.environ.get('ALLOWED_USER_IDS', '').split(',') if user_id]
PC_MAC_ADDRESS = os.environ.get('PC_MAC_ADDRESS')
PC_IP_ADDRESS = os.environ.get('PC_IP_ADDRESS')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Приветствует пользователя и проверяет доступ."""
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⚠️ У вас нет доступа к этому боту.")
        logger.warning(f"Попытка доступа от неавторизованного пользователя: {user_id}")
        return

    keyboard = [
        [
            InlineKeyboardButton("🔄 Статус ПК", callback_data="status"),
        ],
        [
            InlineKeyboardButton("🟢 Включить ПК", callback_data="turn_on"),
            InlineKeyboardButton("🔴 Выключить ПК", callback_data="turn_off"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n"
        "Используйте кнопки ниже для управления вашим ПК:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in ALLOWED_USER_IDS:
        await query.answer("⚠️ У вас нет доступа к этой функции.")
        return

    await query.answer()

    if query.data == "status":
        status = check_pc_status()
        await query.edit_message_text(
            text=f"Статус ПК: {status}",
            reply_markup=query.message.reply_markup
        )
    elif query.data == "turn_on":
        result = turn_on_pc()
        await query.edit_message_text(
            text=f"{result}",
            reply_markup=query.message.reply_markup
        )
    elif query.data == "turn_off":
        result = turn_off_pc()
        await query.edit_message_text(
            text=f"{result}",
            reply_markup=query.message.reply_markup
        )

def check_pc_status() -> str:
    """Проверяет статус ПК (включен/выключен)."""
    try:
        # Пробуем проверить доступность хоста через ping (одна попытка с таймаутом 1 секунда)
        param = '-n' if os.name == 'nt' else '-c'
        command = ['ping', param, '1', '-w', '1', PC_IP_ADDRESS]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            return "🟢 Включен и доступен в сети"
        else:
            return "🔴 Выключен или недоступен"
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса ПК: {e}")
        return f"⚠️ Ошибка при проверке статуса: {str(e)}"

def turn_on_pc() -> str:
    """Включает ПК с помощью Wake-on-LAN."""
    try:
        # Проверяем сначала, не включен ли уже ПК
        status = check_pc_status()
        if "Включен" in status:
            return "ПК уже включен и доступен в сети."

        # Отправляем Magic Packet
        send_magic_packet(PC_MAC_ADDRESS)

        # Ждем немного и проверяем статус
        time.sleep(5)  # Даем немного времени для запуска
        status = check_pc_status()

        if "Включен" in status:
            return "✅ ПК успешно включен!"
        else:
            return "🔄 Сигнал на включение отправлен, но ПК пока не отвечает. Проверьте статус позже."

    except Exception as e:
        logger.error(f"Ошибка при включении ПК: {e}")
        return f"⚠️ Ошибка при включении ПК: {str(e)}"

def turn_off_pc() -> str:
    try:
        subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
        return "🔴 Команда выключения отправлена"
    except Exception as e:
        return f"⚠️ Критическая ошибка: {str(e)}"

def main() -> None:
    """Запускает бота."""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()

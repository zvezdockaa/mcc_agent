#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram бот для массовой рассылки сообщений
"""

import requests
import time
import datetime
import os
import sys
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройки из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')  # Опционально, для уведомлений

# Проверка наличия токена
if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не настроен!")
    sys.exit(1)

UPDATE_INTERVAL = 2

# Множество подписчиков (хранится в памяти)
subscribers = set()

# Отключаем предупреждения SSL
requests.packages.urllib3.disable_warnings()


def load_subscribers_from_history():
    """
    Загружает подписчиков из истории сообщений
    Вызывается при запуске бота
    """
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        response = requests.get(url, timeout=10, verify=False)

        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                for update in data['result']:
                    if 'message' in update:
                        chat_id = str(update['message']['chat']['id'])
                        text = update['message'].get('text', '')

                        # Если пользователь отправлял /start, добавляем в подписчики
                        if text == '/start':
                            subscribers.add(chat_id)
                            logger.info(f"✅ Восстановлен подписчик из истории: {chat_id}")

        logger.info(f"📋 Загружено {len(subscribers)} подписчиков из истории")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки подписчиков: {e}")


def send_message(chat_id, text):
    """Отправляет сообщение конкретному пользователю"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        response = requests.get(url, params=params, timeout=10, verify=False)

        if response.status_code == 200:
            return True
        else:
            logger.error(f"❌ Ошибка отправки пользователю {chat_id}: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка отправки пользователю {chat_id}: {e}")
        return False


def broadcast_message(name, email, message):
    """
    Отправляет сообщение ВСЕМ подписчикам
    """
    if not subscribers:
        logger.warning("⚠️ Нет подписчиков для рассылки")
        return 0

    # Формируем сообщение
    text = (
        f"📬 <b>НОВАЯ ОБРАТНАЯ СВЯЗЬ С САЙТА</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📧 <b>Email:</b> {email}\n"
        f"🕐 <b>Время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        f"💬 <b>Сообщение:</b>\n{message}"
    )

    logger.info(f"📢 Начинаем рассылку {len(subscribers)} подписчикам...")

    success_count = 0
    fail_count = 0
    failed_users = []

    for chat_id in subscribers:
        if send_message(chat_id, text):
            success_count += 1
        else:
            fail_count += 1
            failed_users.append(chat_id)
        time.sleep(0.05)  # Задержка чтобы не забанили

    logger.info(f"✅ Рассылка завершена: {success_count} успешно, {fail_count} ошибок")

    # Если админ указан, отправляем ему отчет
    if ADMIN_CHAT_ID:
        send_message(
            ADMIN_CHAT_ID,
            f"📊 Отчет о рассылке:\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Ошибок: {fail_count}\n"
            f"👥 Всего подписчиков: {len(subscribers)}"
        )

    return success_count


def get_updates(offset=None):
    """Получает новые сообщения от пользователей"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {'timeout': 10, 'offset': offset} if offset else {'timeout': 10}

        response = requests.get(url, params=params, timeout=15, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка getUpdates: {e}")
        return None


def handle_message(message):
    """Обрабатывает входящее сообщение от пользователя"""
    try:
        chat_id = str(message['chat']['id'])
        text = message.get('text', '')
        user = message['from']

        user_name = user.get('first_name', 'Пользователь')
        username = user.get('username', 'нет username')

        logger.info(f"📨 Сообщение от {user_name} (@{username}) [{chat_id}]: {text[:50]}")

        # Обработка команд
        if text == '/start':
            # Добавляем в подписчики
            subscribers.add(chat_id)

            response = (
                f"👋 Привет, {user_name}!\n\n"
                f"✅ Вы подписаны на уведомления о новой обратной связи с сайта MCC AI Agent.\n"
                f"Теперь вы будете получать сообщения, когда кто-то оставляет обратную связь.\n\n"
                f"📌 Ваш Chat ID: <code>{chat_id}</code>\n\n"
                f"👥 Всего подписчиков: {len(subscribers)}\n\n"
                f"Доступные команды:\n"
                f"/help - помощь\n"
                f"/status - статус\n"
                f"/stop - отписаться от рассылки"
            )
            send_message(chat_id, response)

            # Уведомляем админа о новом подписчике
            if ADMIN_CHAT_ID:
                send_message(
                    ADMIN_CHAT_ID,
                    f"👤 Новый подписчик!\n"
                    f"Имя: {user_name}\n"
                    f"Username: @{username}\n"
                    f"Chat ID: {chat_id}\n"
                    f"Всего подписчиков: {len(subscribers)}"
                )

        elif text == '/help':
            response = (
                "🤖 Доступные команды:\n\n"
                "/start - подписаться на уведомления\n"
                "/stop - отписаться от уведомлений\n"
                "/status - статус бота\n"
                "/stats - статистика\n"
                "/help - показать это сообщение"
            )
            send_message(chat_id, response)

        elif text == '/status':
            response = (
                f"✅ Бот работает!\n"
                f"📊 Всего подписчиков: {len(subscribers)}\n"
                f"🕐 Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            send_message(chat_id, response)

        elif text == '/stats':
            response = f"📊 Статистика:\n👥 Подписчиков: {len(subscribers)}"
            send_message(chat_id, response)

        elif text == '/stop':
            if chat_id in subscribers:
                subscribers.remove(chat_id)
                response = "✅ Вы отписаны от рассылки. Чтобы подписаться снова, отправьте /start"

                # Уведомляем админа
                if ADMIN_CHAT_ID:
                    send_message(
                        ADMIN_CHAT_ID,
                        f"👋 Пользователь отписался:\n"
                        f"Chat ID: {chat_id}\n"
                        f"Осталось подписчиков: {len(subscribers)}"
                    )
            else:
                response = "❌ Вы не были подписаны"
            send_message(chat_id, response)

        else:
            if text.startswith('/'):
                response = f"❌ Неизвестная команда: {text}\nИспользуйте /help"
            else:
                response = (
                    f"Я получил ваше сообщение!\n\n"
                    f"Я бот для уведомлений о новой обратной связи с сайта.\n"
                    f"Чтобы подписаться на рассылку, отправьте /start"
                )
            send_message(chat_id, response)

    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")


def check_for_new_messages():
    """
    Функция для опроса Flask приложения
    В реальности здесь может быть HTTP endpoint
    """
    # Этот метод будет вызываться из app.py
    pass


def main():
    """Основной цикл бота"""
    import signal

    def signal_handler(sig, frame):
        logger.info("👋 Бот остановлен сигналом")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 50)
    logger.info("🚀 Telegram бот для МАССОВОЙ РАССЫЛКИ запущен!")
    logger.info(f"👤 Администратор: {ADMIN_CHAT_ID or 'не указан'}")
    logger.info("🔄 Загрузка подписчиков из истории...")

    # Загружаем подписчиков из истории сообщений
    load_subscribers_from_history()

    logger.info(f"📋 Всего подписчиков: {len(subscribers)}")
    logger.info("🔄 Ожидание сообщений...")
    logger.info("=" * 50)

    last_update_id = 0

    # Отправляем уведомление админу о запуске
    if ADMIN_CHAT_ID:
        send_message(ADMIN_CHAT_ID, f"✅ Бот для массовой рассылки запущен!\n👥 Подписчиков: {len(subscribers)}")

    while True:
        try:
            # Получаем обновления от пользователей
            updates = get_updates(last_update_id + 1 if last_update_id else None)

            if updates and 'result' in updates:
                for update in updates['result']:
                    if 'message' in update:
                        handle_message(update['message'])
                        last_update_id = update['update_id']

            time.sleep(UPDATE_INTERVAL)

        except Exception as e:
            logger.error(f"❌ Ошибка в основном цикле: {e}")
            time.sleep(UPDATE_INTERVAL * 5)


if __name__ == '__main__':
    # Проверяем соединение
    logger.info("Проверка соединения с Telegram API...")

    try:
        test_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(test_url, timeout=10, verify=False)

        if response.status_code == 200:
            bot_info = response.json()
            logger.info(f"✅ Бот @{bot_info['result']['username']} успешно подключен!")
        else:
            logger.error(f"❌ Ошибка подключения: {response.status_code}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Не удалось подключиться к Telegram: {e}")
        sys.exit(1)

    main()
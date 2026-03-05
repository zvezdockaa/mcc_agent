#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram бот для массовой рассылки сообщений всем подписчикам
Запускается параллельно с основным Flask приложением
"""

import requests
import time
import datetime
import os
import sys
from dotenv import load_dotenv


load_dotenv()

# настройки из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')

if not TOKEN:
    print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не настроен в .env файле!")
    print("Скопируйте .env.example в .env и укажите ваш токен")
    sys.exit(1)

if not ADMIN_CHAT_ID:
    print("⚠️ ВНИМАНИЕ: TELEGRAM_ADMIN_CHAT_ID не настроен!")

UPDATE_INTERVAL = 2
USERS_FILE = "bot_users.txt"
MESSAGES_FILE = "telegram_messages.txt"
SENT_MESSAGES_FILE = "sent_messages.txt"

requests.packages.urllib3.disable_warnings()


def log(message):
    """Простое логирование с временем"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


def load_users():
    """Загружает список пользователей из файла"""
    users = []
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        users.append(line)
            log(f"📋 Загружено {len(users)} пользователей")
        except Exception as e:
            log(f"❌ Ошибка загрузки пользователей: {e}")
    return users


def save_user(chat_id):
    """Сохраняет нового пользователя в файл"""
    try:
        users = load_users()
        if str(chat_id) not in users:
            with open(USERS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{chat_id}\n")
            log(f"✅ Новый пользователь сохранен: {chat_id}")
            return True
    except Exception as e:
        log(f"❌ Ошибка сохранения пользователя: {e}")
    return False


def remove_user(chat_id):
    """Удаляет пользователя из файла"""
    try:
        users = load_users()
        if str(chat_id) in users:
            users.remove(str(chat_id))
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                for uid in users:
                    f.write(f"{uid}\n")
            log(f"✅ Пользователь удален: {chat_id}")
            return True
    except Exception as e:
        log(f"❌ Ошибка удаления пользователя: {e}")
    return False


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
            log(f"❌ Ошибка отправки пользователю {chat_id}: {response.status_code}")
            return False

    except Exception as e:
        log(f"❌ Ошибка отправки пользователю {chat_id}: {e}")
        return False


def broadcast_message(text):
    """Отправляет сообщение всем пользователям бота"""
    users = load_users()
    if not users:
        log("⚠️ Нет пользователей для рассылки")
        return 0, 0

    log(f"📢 Начинаем рассылку {len(users)} пользователям...")

    success_count = 0
    fail_count = 0
    failed_users = []

    for chat_id in users:
        if send_message(chat_id, text):
            success_count += 1
        else:
            fail_count += 1
            failed_users.append(chat_id)
        time.sleep(0.05)  # Небольшая задержка чтобы не забанили

    log(f"✅ Рассылка завершена: {success_count} успешно, {fail_count} ошибок")

    # Пробуем еще раз для тех, у кого не получилось
    if failed_users:
        log(f"🔄 Повторная отправка {len(failed_users)} пользователям...")
        time.sleep(2)
        for chat_id in failed_users:
            if send_message(chat_id, text):
                success_count += 1
                fail_count -= 1

    return success_count, fail_count


def check_new_messages():
    """Проверяет новые сообщения в файле и рассылает их"""
    if not os.path.exists(MESSAGES_FILE):
        return False

    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            return False

        # Разделяем сообщения
        messages = content.split('-' * 40)
        sent_count = 0

        for msg in messages:
            msg = msg.strip()
            if not msg or len(msg) < 10:
                continue

            # Проверяем, не отправляли ли уже это сообщение
            if is_message_sent(msg):
                continue

            log(f"📨 Найдено новое сообщение для рассылки")

            # Отправляем всем пользователям
            success, fail = broadcast_message(msg)

            if success > 0:
                # Отмечаем сообщение как отправленное
                mark_message_as_sent(msg)
                sent_count += 1
                log(f"✅ Сообщение разослано {success} пользователям")

        return sent_count > 0

    except Exception as e:
        log(f"❌ Ошибка при проверке сообщений: {e}")
        return False


def is_message_sent(message):
    """Проверяет, было ли сообщение уже отправлено"""
    if not os.path.exists(SENT_MESSAGES_FILE):
        return False
    try:
        with open(SENT_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            sent = f.read()
        # Берем первые 100 символов для сравнения
        return message[:100] in sent
    except:
        return False


def mark_message_as_sent(message):
    """Отмечает сообщение как отправленное"""
    try:
        with open(SENT_MESSAGES_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.datetime.now()}]\n{message[:100]}...\n")
    except Exception as e:
        log(f"❌ Ошибка при отметке сообщения: {e}")


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
        log(f"❌ Ошибка getUpdates: {e}")
        return None


def handle_message(message):
    """Обрабатывает входящее сообщение от пользователя"""
    try:
        chat_id = str(message['chat']['id'])
        text = message.get('text', '')
        user = message['from']

        user_name = user.get('first_name', 'Пользователь')
        username = user.get('username', 'нет username')

        log(f"📨 Сообщение от {user_name} (@{username}) [{chat_id}]: {text[:50]}")

        # Сохраняем пользователя (каждый, кто написал боту)
        save_user(chat_id)

        # Обработка команд
        if text == '/start':
            response = (
                f"👋 Привет, {user_name}!\n\n"
                f"✅ Вы подписаны на уведомления о новой обратной связи с сайта MCC AI Agent.\n"
                f"Теперь вы будете получать сообщения, когда кто-то оставляет обратную связь.\n\n"
                f"📌 Ваш Chat ID: <code>{chat_id}</code>\n\n"
                f"Доступные команды:\n"
                f"/help - помощь\n"
                f"/status - статус\n"
                f"/stop - отписаться от рассылки"
            )
            send_message(chat_id, response)

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
            users = load_users()
            response = (
                f"✅ Бот работает!\n"
                f"📊 Всего подписчиков: {len(users)}\n"
                f"🕐 Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            send_message(chat_id, response)

        elif text == '/stats':
            users = load_users()
            if os.path.exists(MESSAGES_FILE):
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    msg_count = len([l for l in content.split('\n') if 'Имя:' in l])
                response = f"📊 Статистика:\n👥 Подписчиков: {len(users)}\n📨 Сообщений с сайта: {msg_count}"
            else:
                response = f"📊 Статистика:\n👥 Подписчиков: {len(users)}\n📨 Сообщений с сайта: 0"
            send_message(chat_id, response)

        elif text == '/stop':
            if remove_user(chat_id):
                response = "✅ Вы отписаны от рассылки. Чтобы подписаться снова, отправьте /start"
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
        log(f"❌ Ошибка обработки сообщения: {e}")


def main():
    """Основной цикл бота"""
    log("=" * 50)
    log("🚀 Telegram бот для МАССОВОЙ РАССЫЛКИ запущен!")
    log(f"👤 Администратор: {ADMIN_CHAT_ID}")
    log(f"📋 Загружено подписчиков: {len(load_users())}")
    log("🔄 Ожидание сообщений и новых данных для рассылки...")
    log("=" * 50)

    last_update_id = 0
    last_check_time = time.time()

    # Отправляем уведомление админу о запуске
    send_message(ADMIN_CHAT_ID, "✅ Бот запущен!")

    while True:
        try:
            # Получаем обновления от пользователей
            updates = get_updates(last_update_id + 1 if last_update_id else None)

            if updates and 'result' in updates:
                for update in updates['result']:
                    if 'message' in update:
                        handle_message(update['message'])
                        last_update_id = update['update_id']

            # Проверяем новые сообщения для рассылки каждые 5 секунд
            if time.time() - last_check_time > 5:
                check_new_messages()
                last_check_time = time.time()

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            log("\n👋 Бот остановлен пользователем")
            send_message(ADMIN_CHAT_ID, "❌ Бот остановлен")
            break

        except Exception as e:
            log(f"❌ Ошибка в основном цикле: {e}")
            time.sleep(UPDATE_INTERVAL * 5)


if __name__ == '__main__':
    # Проверяем соединение
    log("Проверка соединения с Telegram API...")

    try:
        test_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(test_url, timeout=10, verify=False)

        if response.status_code == 200:
            bot_info = response.json()
            log(f"✅ Бот @{bot_info['result']['username']} успешно подключен!")
        else:
            log(f"❌ Ошибка подключения: {response.status_code}")
            sys.exit(1)

    except Exception as e:
        log(f"❌ Не удалось подключиться к Telegram: {e}")
        sys.exit(1)

    main()
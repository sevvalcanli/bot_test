from telegram.ext import Updater, CommandHandler
import logging

# Loglama ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Bot'un /start komutuna cevap verecek fonksiyon
def start(update, context):
    chat_id = update.message.chat_id
    print(f"Chat ID: {chat_id}")

# Telegram bot token
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Bot oluşturma
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# /start komutu için handler ekleme
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Bot'u başlat
updater.start_polling()

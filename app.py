from aiogram import Bot, Dispatcher, types
import re
import requests
import json
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)

# Read the token from file
with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Function to validate Ethereum address
def is_valid_ethereum_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] == "0"

# Function to validate BSC address
def is_valid_bsc_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] != "0"

@dp.message_handler()
async def handle_message(message: types.Message):
    text = message.text
    if re.match(r'^0x[a-fA-F0-9]{40}$', text) and is_valid_bsc_address(text):
        keyboard = types.InlineKeyboardMarkup()
        base_urls = [
            f"https://gopluslabs.io/token-security/56/{text}",
            f"https://www.dextools.io/app/en/bnb/pair-explorer/{text}",
            f"https://bscscan.com/token/{text}",
            f"https://dexscreener.com/bsc/{text}",
            f"https://tokensniffer.com/token/bsc/{text}",
            f"https://honeypot.is/?address={text}",
        ]
        button_labels = ["GoPlus", "Chart", "BSCScan", "Dex Screener", "Token Sniffer", "Honeypot"]

        for label, url in zip(button_labels, base_urls):
            keyboard.add(types.InlineKeyboardButton(text=label, url=url))

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

    elif re.match(r'^0x[a-fA-F0-9]{40}$', text) and is_valid_ethereum_address(text):
        keyboard = types.InlineKeyboardMarkup()
        base_urls = [
            f"https://gopluslabs.io/token-security/1/{text}",
            f"https://www.dextools.io/app/en/ether/pair-explorer/{text}",
            f"https://etherscan.io/token/{text}",
            f"https://dexscreener.com/ethereum/{text}",
            f"https://tokensniffer.com/token/eth/{text}",
            f"https://honeypot.is/ethereum?address={text}",
        ]
        button_labels = ["GoPlus", "Chart", "ETHScan", "Dex Screener", "Token Sniffer", "Honeypot"]

        for label, url in zip(button_labels, base_urls):
            keyboard.add(types.InlineKeyboardButton(text=label, url=url))

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

    elif " " not in text and 44 >= len(text) >= 40 and not text.startswith("0x"):
        keyboard = types.InlineKeyboardMarkup()
        base_urls = [
            f"https://www.dextools.io/app/en/solana/pair-explorer/{text}",
            f"https://solscan.io/token/{text}",
            f"https://dexscreener.com/solana/{text}",
            f"https://rugcheck.xyz/tokens/{text}",
        ]
        button_labels = ["Chart", "SOLScan", "Dex Screener", "Rug Check"]

        for label, url in zip(button_labels, base_urls):
            keyboard.add(types.InlineKeyboardButton(text=label, url=url))

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

# Start polling
async def on_startup():
    logging.info("Bot is online!")

if __name__ == '__main__':
    asyncio.run(dp.start_polling(on_startup=on_startup))

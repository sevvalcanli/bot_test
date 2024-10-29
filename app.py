from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils import start_polling
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import requests

with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

bot = Bot(token=TOKEN)
dp = Dispatcher()

def is_valid_ethereum_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=YOUR_API_KEY"
    response = requests.get(url)
    data = response.json()
    return data['result'] == "0"

def is_valid_bsc_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=YOUR_API_KEY"
    response = requests.get(url)
    data = response.json()
    return data['result'] != "0"

@dp.message_handler()
async def handle_message(message: types.Message):
    text = message.text
    if re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_bsc_address(text):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="GoPlus", url=f"https://gopluslabs.io/token-security/56/{text}"),
            InlineKeyboardButton(text="Chart", url=f"https://www.dextools.io/app/en/bnb/pair-explorer/{text}"),
            InlineKeyboardButton(text="BSCScan", url=f"https://bscscan.com/token/{text}"),
            InlineKeyboardButton(text="Dex Screener", url=f"https://dexscreener.com/bsc/{text}"),
            InlineKeyboardButton(text="Token Sniffer", url=f"https://tokensniffer.com/token/bsc/{text}"),
            InlineKeyboardButton(text="Honeypot", url=f"https://honeypot.is/?address={text}")
        )
        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)
    elif re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_ethereum_address(text):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="GoPlus", url=f"https://gopluslabs.io/token-security/1/{text}"),
            InlineKeyboardButton(text="Chart", url=f"https://www.dextools.io/app/en/ether/pair-explorer/{text}"),
            InlineKeyboardButton(text="ETHScan", url=f"https://etherscan.io/token/{text}"),
            InlineKeyboardButton(text="Dex Screener", url=f"https://dexscreener.com/ethereum/{text}"),
            InlineKeyboardButton(text="Token Sniffer", url=f"https://tokensniffer.com/token/eth/{text}"),
            InlineKeyboardButton(text="Honeypot", url=f"https://honeypot.is/ethereum?address={text}")
        )
        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)
    elif " " not in text and 44 >= len(text) >= 40 and not text.startswith("0x"):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="Chart", url=f"https://www.dextools.io/app/en/solana/pair-explorer/{text}"),
            InlineKeyboardButton(text="SOLScan", url=f"https://solscan.io/token/{text}"),
            InlineKeyboardButton(text="Dex Screener", url=f"https://dexscreener.com/solana/{text}"),
            InlineKeyboardButton(text="Rug Check", url=f"https://rugcheck.xyz/tokens/{text}")
        )
        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)

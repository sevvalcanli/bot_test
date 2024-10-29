from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import requests
import json

# Read the token from the file
with open("token.txt", "r") as f:
    TOKEN = f.read().strip()  # Strip any whitespace/newline characters

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def is_valid_ethereum_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] == "0"

def is_valid_bsc_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] != "0"

# Change from @dp.message_handler() to @dp.message()
@dp.message()
async def handle_message(message: types.Message):
    text = message.text
    if re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_bsc_address(text):
        base_url = f"https://gopluslabs.io/token-security/56/{text}"
        base_url1 = f"https://www.dextools.io/app/en/bnb/pair-explorer/{text}"
        base_url2 = f"https://bscscan.com/token/{text}"
        base_url3 = f"https://dexscreener.com/bsc/{text}"
        base_url4 = f"https://tokensniffer.com/token/bsc/{text}"
        base_url5 = f"https://honeypot.is/?address={text}"

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(text="GoPlus", url=base_url),
            InlineKeyboardButton(text="Chart", url=base_url1)
        ).row(
            InlineKeyboardButton(text="BSCScan", url=base_url2),
            InlineKeyboardButton(text="Dex Screener", url=base_url3)
        ).row(
            InlineKeyboardButton(text="Token Sniffer", url=base_url4),
            InlineKeyboardButton(text="Honeypot", url=base_url5)
        )

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

    elif re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_ethereum_address(text):
        base_url = f"https://gopluslabs.io/token-security/1/{text}"
        base_url1 = f"https://www.dextools.io/app/en/ether/pair-explorer/{text}"
        base_url2 = f"https://etherscan.io/token/{text}"
        base_url3 = f"https://dexscreener.com/ethereum/{text}"
        base_url4 = f"https://tokensniffer.com/token/eth/{text}"
        base_url5 = f"https://honeypot.is/ethereum?address={text}"

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(text="GoPlus", url=base_url),
            InlineKeyboardButton(text="Chart", url=base_url1)
        ).row(
            InlineKeyboardButton(text="ETHScan", url=base_url2),
            InlineKeyboardButton(text="Dex Screener", url=base_url3)
        ).row(
            InlineKeyboardButton(text="Token Sniffer", url=base_url4),
            InlineKeyboardButton(text="Honeypot", url=base_url5)
        )

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

    elif " " not in text and 44 >= len(text) >= 40 and not text.startswith("0x"):
        base_url1 = f"https://www.dextools.io/app/en/solana/pair-explorer/{text}"
        base_url2 = f"https://solscan.io/token/{text}"
        base_url3 = f"https://dexscreener.com/solana/{text}"
        base_url4 = f"https://rugcheck.xyz/tokens/{text}"

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(text="Chart", url=base_url1),
            InlineKeyboardButton(text="SOLScan", url=base_url2)
        ).row(
            InlineKeyboardButton(text="Dex Screener", url=base_url3),
            InlineKeyboardButton(text="Rug Check", url=base_url4)
        )

        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

from aiogram import Bot,Dispatcher,types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup
import re
import requests
import requests




with open("token.txt","r") as f:
     TOKEN = f.read()
bot =Bot(token=TOKEN)

dp = Dispatcher(bot)

def is_valid_ethereum_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    if data['result'] == "0":
        return True
    return False

def is_valid_bsc_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    if data['result'] != "0":
        return True
    return False



@dp.message_handler()
async def handle_message(message: types.Message):
    text=message.text
    if re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_bsc_address(text):
            base_url = f"https://gopluslabs.io/token-security/56/{text}"
            base_url1 = f"https://www.dextools.io/app/en/bnb/pair-explorer/{text}"
            base_url2 = f"https://bscscan.com/token/{text}"
            base_url3 =f"https://dexscreener.com/bsc/{text}"
            base_url4 = f"https://tokensniffer.com/token/bsc/{text}"
            base_url5 = f"https://honeypot.is/?address={text}"
            keyboard = types.InlineKeyboardMarkup()
            url_button = types.InlineKeyboardButton(text="GoPlus", url=base_url)
            url_button1 = types.InlineKeyboardButton(text="Chart", url=base_url1)
            url_button2 = types.InlineKeyboardButton(text="BSCScan", url=base_url2)
            url_button3 = types.InlineKeyboardButton(text="Dex Screener", url=base_url3)
            url_button4 = types.InlineKeyboardButton(text="Token Sniffer", url=base_url4)
            url_button5 = types.InlineKeyboardButton(text="Honeypot", url=base_url5)
            keyboard.row(url_button,url_button1).row(url_button2,url_button3).row(url_button4,url_button5)
            await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)
    elif re.match('^0x[a-fA-F0-9]{40}$', text) and is_valid_ethereum_address(text):
            base_url = f"https://gopluslabs.io/token-security/1/{text}"
            base_url1 = f"https://www.dextools.io/app/en/ether/pair-explorer/{text}"
            base_url2 = f"https://etherscan.io/token/{text}"
            base_url3 = f"https://dexscreener.com/ethereum/{text}"
            base_url4 = f"https://tokensniffer.com/token/eth/{text}"
            base_url5 = f"https://honeypot.is/ethereum?address={text}"
            keyboard = types.InlineKeyboardMarkup()
            url_button = types.InlineKeyboardButton(text="GoPlus", url=base_url)
            url_button1 = types.InlineKeyboardButton(text="Chart", url=base_url1)
            url_button2 = types.InlineKeyboardButton(text="ETHScan", url=base_url2)
            url_button3 = types.InlineKeyboardButton(text="Dex Screener", url=base_url3)
            url_button4 = types.InlineKeyboardButton(text="Token Sniffer", url=base_url4)
            url_button5 = types.InlineKeyboardButton(text="Honeypot", url=base_url5)
            keyboard.row(url_button,url_button1).row(url_button2,url_button3).row(url_button4,url_button5)
            await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)
    else:
            base_url1 = f"https://www.dextools.io/app/en/solana/pair-explorer/{text}"
            base_url2 = f"https://solscan.io/token/{text}"
            base_url3 = f"https://dexscreener.com/solana/{text}"
            base_url4 = f"https://rugcheck.xyz/tokens/{text}"
            keyboard = types.InlineKeyboardMarkup()
            url_button1 = types.InlineKeyboardButton(text="Chart", url=base_url1)
            url_button2 = types.InlineKeyboardButton(text="SOLScan", url=base_url2)
            url_button3 = types.InlineKeyboardButton(text="Dex Screener", url=base_url3)
            url_button4 = types.InlineKeyboardButton(text="Rug Check", url=base_url4)
            keyboard.row(url_button1,url_button2).row(url_button3,url_button4)
            await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

executor.start_polling(dp)
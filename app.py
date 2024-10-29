import re
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Token'ı dosyadan oku
with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

# Bot ve Dispatcher nesnelerini oluştur
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def is_valid_ethereum_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] == "0"

async def is_valid_bsc_address(address):
    url = f"https://api.bscscan.com/api?module=stats&action=tokenCsupply&contractaddress={address}&apikey=3XS9YREEBUZ3HS5CBQMI7UA97CYSRMTI2M"
    response = requests.get(url)
    data = response.json()
    return data['result'] != "0"

@dp.message()
async def handle_message(message: types.Message):
    text = message.text
    if text is None:
        return  # Eğer metin yoksa, fonksiyonu burada sonlandır

    if re.match('^0x[a-fA-F0-9]{40}$', text):
        if await is_valid_bsc_address(text):
            base_urls = [
                f"https://gopluslabs.io/token-security/56/{text}",
                f"https://www.dextools.io/app/en/bnb/pair-explorer/{text}",
                f"https://bscscan.com/token/{text}",
                f"https://dexscreener.com/bsc/{text}",
                f"https://tokensniffer.com/token/bsc/{text}",
                f"https://honeypot.is/?address={text}"
            ]
            button_labels = [
                "GoPlus Security",
                "Dextools BNB",
                "BSCScan",
                "Dex Screener",
                "Token Sniffer",
                "Honeypot Check"
            ]
        elif await is_valid_ethereum_address(text):
            base_urls = [
                f"https://gopluslabs.io/token-security/1/{text}",
                f"https://www.dextools.io/app/en/ether/pair-explorer/{text}",
                f"https://etherscan.io/token/{text}",
                f"https://dexscreener.com/ethereum/{text}",
                f"https://tokensniffer.com/token/eth/{text}",
                f"https://honeypot.is/ethereum?address={text}"
            ]
            button_labels = [
                "GoPlus Security",
                "Dextools ETH",
                "ETHScan",
                "Dex Screener",
                "Token Sniffer",
                "Honeypot Check"
            ]
        
        buttons = [InlineKeyboardButton(text=label, url=url) for label, url in zip(button_labels, base_urls)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)
    
    elif " " not in text and 44 >= len(text) >= 40 and not text.startswith("0x"):
        base_urls = [
            f"https://www.dextools.io/app/en/solana/pair-explorer/{text}",
            f"https://solscan.io/token/{text}",
            f"https://dexscreener.com/solana/{text}",
            f"https://rugcheck.xyz/tokens/{text}"
        ]
        button_labels = [
            "Dextools Solana",
            "SOLScan",
            "Dex Screener",
            "Rug Check"
        ]
        
        buttons = [InlineKeyboardButton(text=label, url=url) for label, url in zip(button_labels, base_urls)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.reply("Hoş geldin, geleceğin kripto zengini!", reply_markup=keyboard)

if __name__ == "__main__":
    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())

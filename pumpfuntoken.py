import json
import time
import websockets
import asyncio
import requests
import os
import logging
from datetime import datetime
from collections import deque
from telegram.ext import Application

# Log ayarları
logging.basicConfig(
    filename='solana_pumpfun_graduated.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

class SolanaPumpfunBot:
    def __init__(self):
        self.pair_url = "https://api.dexscreener.com/token-pairs/v1/solana/{tokenAddress}"
        self.pairs_data = {}
        self.new_tokens = deque(maxlen=100)
        self.marketcap_threshold = 1_000_000
        self.check_interval = 60
        self.monitor_duration = 2 * 60 * 60
        self.telegram_bot_token = "7586619568:AAE2Au8AhKVDldZuSHbG43ggS3i6lzTVkdA"
        self.chat_id = "-1002309534365"
        self.reconnect_delay = 5
        self.running = False
        self.application = Application.builder().token(self.telegram_bot_token).build()

    async def send_telegram_notification(self, message: str):
        logging.info("send_telegram_notification fonksiyonu çağrıldı.")
        if not self.telegram_bot_token or not self.chat_id:
            logging.error("Telegram bot token veya chat_id eksik!")
            return
        try:
            await self.application.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
            logging.info(f"Telegram bildirimi gönderildi: {message}")
        except Exception as e:
            logging.error(f"Telegram bildirimi gönderilemedi: {e}")

    async def check_token(self, token_address: str, detect_time: float):
        url = self.pair_url.format(tokenAddress=token_address)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            pairs = response.json()
            raydium_pairs = [p for p in pairs if p.get('dexId') == 'raydium']
            if not raydium_pairs:
                return False

            pair = raydium_pairs[0]
            pair_address = pair.get('pairAddress')
            if self.pairs_data.get(pair_address, {}).get('notified', False):
                return True

            fdv = float(pair.get('fdv', 0) or 0)
            if fdv >= self.marketcap_threshold:
                token_name = pair.get('baseToken', {}).get('symbol', 'Unknown')
                price_usd = float(pair.get('priceUsd', 0) or 0)
                created_at = pair.get('pairCreatedAt', 0) / 1000
                info = pair.get('info', {})
                websites = info.get('websites', [])
                socials = info.get('socials', [])
                website = next((w['url'] for w in websites if w.get('label') == 'Website'), '')
                twitter = next((s['url'] for s in socials if s.get('type') == 'twitter'), '')
                telegram = next((s['url'] for s in socials if s.get('type') == 'telegram'), '')
                liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                volume_24h = float(pair.get('volume', {}).get('h24', 0) or 0)
                age_minutes = (time.time() - created_at) / 60
                price_change_h1 = pair.get("priceChange", {}).get("h1", 0)
                price_change_h24 = pair.get("priceChange", {}).get("h24", 0)

                message = (
                    f"🚀 *Yeni Pump.fun Mezunu Solana Token!* \n"
                    f"🌐 *Solana @ Raydium* \n"
                    f"🔹 *Token Adı:* {token_name} \n"
                    f"📍 *Token Adresi:* `{token_address}` \n"
                    f"🕰️ *Yaş:* {int(age_minutes)}m \n\n"
                    f"📊 *Token Stats* \n"
                    f" ├ USD: ${price_usd:.4f} {price_change_h24}% \n"
                    f" ├ MC: ${fdv:,.2f} \n"
                    f" ├ Vol: ${volume_24h/1000:.1f}K \n"
                    f" ├ LP: ${liquidity/1000:.1f}K \n"
                    f" ├ 1H: {price_change_h1}% 🅑 {pair.get('txns', {}).get('h1', {}).get('buys', 0)} Ⓢ {pair.get('txns', {}).get('h1', {}).get('sells', 0)} \n\n"
                    f"🔗 *Linkler:* \n"
                    f" - [DEX](https://dexscreener.com/solana/{pair_address}) \n"
                    f" - [PumpFun](https://pump.fun/{token_address}) \n"
                    f" - [Bullx](https://bullx.io/terminal?chainId=1399811149&address={token_address}) \n"
                )

                if website:
                    message += f"🌍 [Website]({website}) \n"
                if twitter:
                    message += f"🐦 [Twitter]({twitter}) \n"
                if telegram:
                    message += f"💬 [Telegram]({telegram}) \n"

                logging.info(message)
                await self.send_telegram_notification(message)  # Asenkron çağrı
                self.pairs_data[pair_address] = {'notified': True}
                return True
            else:
                logging.info(f"Kontrol: {token_address} - FDV: {fdv}")
                return False
        except Exception as e:
            logging.error(f"Token kontrol hatası: {token_address} - {e}")
            return False

    async def monitor_raydium_liquidity(self):
        uri = "wss://pumpportal.fun/api/data"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({"method": "subscribeRaydiumLiquidity"}))
                    logging.info("PumpPortal’a abone olundu, Raydium likidite eklenmeleri dinleniyor...")
                    
                    while self.running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        token_address = data.get("mint")
                        if token_address:  # Sadece mint varsa işlem yap
                            detect_time = time.time()
                            logging.info(f"Raydium’a likidite eklendi: {token_address} - Tespit zamanı: {datetime.fromtimestamp(detect_time)}")
                            # Token zaten listede mi diye kontrol et
                            if not any(t[0] == token_address for t in self.new_tokens):
                                if await self.check_token(token_address, detect_time):
                                    continue
                                self.new_tokens.append((token_address, detect_time))

                        current_time = time.time()
                        tokens_to_remove = []
                        for token_address, detect_time in list(self.new_tokens):
                            if current_time - detect_time >= self.monitor_duration:
                                tokens_to_remove.append((token_address, detect_time))
                                logging.info(f"Token izleme süresi doldu: {token_address}")
                            elif current_time - detect_time >= self.check_interval:
                                if await self.check_token(token_address, detect_time):
                                    tokens_to_remove.append((token_address, detect_time))

                        for token in tokens_to_remove:
                            if token in self.new_tokens:
                                self.new_tokens.remove(token)

                        await asyncio.sleep(1)
            except websockets.ConnectionClosed as e:
                logging.error(f"WebSocket bağlantısı kesildi (ConnectionClosed): {e}. {self.reconnect_delay} saniye sonra yeniden bağlanılıyor...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)
            except Exception as e:
                logging.error(f"WebSocket bağlantısı kesildi (Genel Hata): {e}. {self.reconnect_delay} saniye sonra yeniden bağlanılıyor...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)

    async def start_monitoring(self):
        logging.info("Bot çalışmaya başladı, hoş geldiniz mesajı gönderiliyor.")
        self.running = True
        await self.send_telegram_notification(
            "🚀 *CryptoGemTR topluluğuna hoş geldiniz!* \n"
            "Pump.fun’dan Raydium’a geçen potansiyelli tokenları sizin için buluyorum. "
            "*Botunuz hizmetinizde!*"
        )
        await self.monitor_raydium_liquidity()

    def run_bot(self):
        asyncio.run(self.start_monitoring())
        self.application.run_polling()

if __name__ == "__main__":
    bot = SolanaPumpfunBot()
    bot.run_bot()

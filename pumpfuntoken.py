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
        self.marketcap_threshold = 1_000_000  # 1M MC üstü için bildirim
        self.min_marketcap_threshold = 20_000  # 20K MC altı için listeden çıkarma
        self.check_interval = 60  # Her dakika periyodik kontrol
        self.monitor_duration = 2 * 60 * 60  # 2 saat izleme süresi
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
                return True  # Zaten bildirilmişse tekrar kontrol etme

            mc = float(pair.get('marketCap', 0) or 0)  # MC’ye bakıyoruz
            if mc >= self.marketcap_threshold:  # 1M üstü için bildirim
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
                    f" ├ MC: ${mc:,.2f} \n"
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
                await self.send_telegram_notification(message)
                self.pairs_data[pair_address] = {'notified': True}
                return True
            elif mc < self.min_marketcap_threshold:  # 20K altına düşerse çıkarma sinyali
                logging.info(f"MC 20K altına düştü, listeden çıkarılıyor: {token_address} - MC: {mc}")
                return False
            else:
                logging.debug(f"Kontrol: {token_address} - MC: {mc}")  # Daha az log için DEBUG’e düşür
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
                        if token_address:  # Yeni token geldiyse
                            detect_time = time.time()
                            logging.info(f"Raydium’a likidite eklendi: {token_address} - Tespit zamanı: {datetime.fromtimestamp(detect_time)}")
                            if not any(t[0] == token_address for t in self.new_tokens):
                                if await self.check_token(token_address, detect_time):
                                    continue
                                self.new_tokens.append((token_address, detect_time))
            except websockets.ConnectionClosed as e:
                logging.error(f"WebSocket bağlantısı kesildi (ConnectionClosed): {e}. {self.reconnect_delay} saniye sonra yeniden bağlanılıyor...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)
            except Exception as e:
                logging.error(f"WebSocket bağlantısı kesildi (Genel Hata): {e}. {self.reconnect_delay} saniye sonra yeniden bağlanılıyor...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)

    async def periodic_check_tokens(self):
        while self.running:
            logging.info("Periyodik token kontrolü başlatıldı...")
            current_time = time.time()
            tokens_to_remove = []
            for token_address, detect_time in list(self.new_tokens):
                if current_time - detect_time >= self.monitor_duration:
                    tokens_to_remove.append((token_address, detect_time))
                    logging.info(f"Token izleme süresi doldu: {token_address}")
                else:
                    result = await self.check_token(token_address, detect_time)
                    if result:  # 1M üstüne çıktıysa çıkar
                        tokens_to_remove.append((token_address, detect_time))
                    elif result is False and float(requests.get(self.pair_url.format(tokenAddress=token_address)).json()[0].get('marketCap', 0) or 0) < self.min_marketcap_threshold:
                        tokens_to_remove.append((token_address, detect_time))  # 20K altına düştüyse çıkar

            for token in tokens_to_remove:
                if token in self.new_tokens:
                    self.new_tokens.remove(token)
            await asyncio.sleep(self.check_interval)  # Her dakika kontrol et

    async def start_monitoring(self):
        logging.info("Bot çalışmaya başladı, hoş geldiniz mesajı gönderiliyor.")
        self.running = True
        await self.send_telegram_notification(
            "🚀 *CryptoGemTR topluluğuna hoş geldiniz!* \n"
            "Pump.fun’dan Raydium’a geçen potansiyelli tokenları sizin için buluyorum. "
            "*Botunuz hizmetinizde!*"
        )
        # WebSocket dinlemesini ve periyodik kontrolü paralel çalıştır
        await asyncio.gather(
            self.monitor_raydium_liquidity(),
            self.periodic_check_tokens()
        )

    def run_bot(self):
        asyncio.run(self.start_monitoring())
        self.application.run_polling()

if __name__ == "__main__":
    bot = SolanaPumpfunBot()
    bot.run_bot()

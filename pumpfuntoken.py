import json
import time
import websockets
import asyncio
import aiohttp  # requests yerine aiohttp kullanıyoruz
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
        max_retries = 2  # İlk deneme + 1 tekrar
        retry_delay = 5  # Saniye cinsinden tekrar deneme aralığı

        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response.raise_for_status()
                        pairs = await response.json()
                        logging.info(f"API yanıtı (deneme {attempt + 1}): {pairs}")
                        pumpswap_pairs = [p for p in pairs if p.get('dexId') == 'pumpswap']
                        
                        if not pumpswap_pairs:
                            logging.info(f"{token_address} için PumpSwap’te eşleşme bulunamadı (deneme {attempt + 1}).")
                            if attempt < max_retries - 1:
                                logging.info(f"{retry_delay} saniye sonra tekrar denenecek...")
                                await asyncio.sleep(retry_delay)
                            continue

                        pair = pumpswap_pairs[0]
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
                                f"🌐 *Solana @ PumpSwap* \n"
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
                            await self.send_telegram_notification(message)
                            self.pairs_data[pair_address] = {'notified': True}
                            return True
                        else:
                            logging.info(f"Kontrol: {token_address} - FDV: {fdv} (deneme {attempt + 1})")
                            if attempt < max_retries - 1:
                                logging.info(f"{retry_delay} saniye sonra tekrar denenecek...")
                                await asyncio.sleep(retry_delay)
                            else:
                                return False
                except Exception as e:
                    logging.error(f"Token kontrol hatası: {token_address} - {e} (deneme {attempt + 1})")
                    if attempt < max_retries - 1:
                        logging.info(f"{retry_delay} saniye sonra tekrar denenecek...")
                        await asyncio.sleep(retry_delay)
                    else:
                        return False
            return False

    async def monitor_raydium_liquidity(self):
        uri = "wss://pumpportal.fun/api/data"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({"method": "subscribeMigration"}))
                    logging.info("PumpPortal’a abone olundu, Raydium likidite eklenmeleri dinleniyor...")
                    
                    while self.running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        logging.info(f"PumpPortal’dan ham veri alındı: {data}")
                        token_address = data.get("mint")
                        if token_address:
                            detect_time = time.time()
                            logging.info(f"Likidite eklendi: {token_address} - Tespit zamanı: {datetime.fromtimestamp(detect_time)}")
                            if await self.check_token(token_address, detect_time):
                                continue
                            self.new_tokens.append((token_address, detect_time))
                        else:
                            logging.info("Alınan veride 'mint' anahtarı yok.")

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
            except (websockets.ConnectionClosed, Exception) as e:
                logging.error(f"WebSocket bağlantısı kesildi: {e}. {self.reconnect_delay} saniye sonra yeniden bağlanılıyor...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)

    async def start_monitoring(self):
        logging.info("Bot çalışmaya başladı, hoş geldiniz mesajı gönderiliyor.")
        self.running = True
        await self.send_telegram_notification(
            "🚀 *CryptoGemTR topluluğuna hoş geldiniz!* \n"
            "Pump.fun’dan PumpSwap'a geçen 1M+ market cap’li tokenları sizin için buluyorum. "
            "*Botunuz hizmetinizde!*"
        )
        await self.monitor_raydium_liquidity()

    async def run_bot(self):
        # Telegram botunu başlat
        await self.application.initialize()
        await self.application.start()
        
        # Monitoring görevini aynı olay döngüsünde çalıştır
        await self.start_monitoring()

if __name__ == "__main__":
    bot = SolanaPumpfunBot()
    asyncio.run(bot.run_bot())

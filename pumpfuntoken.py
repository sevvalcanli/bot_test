import json
import time
import websockets
import asyncio
import requests
from datetime import datetime
import logging

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
        self.pairs_data = {}  # Bildirilen tokenları takip için
        self.new_tokens = {}  # Yeni tokenları ve tespit zamanlarını saklar
        self.marketcap_threshold = 1_000_000  # 1M USD
        self.check_interval = 60  # 1 dakika (saniye)
        self.monitor_duration = 2 * 60 * 60  # 2 saat (saniye)
        self.telegram_bot_token = "7956360443:AAFZdJRht7r-g5oqBF4uCb6ssB6__Pjt21w"
        self.telegram_chat_id = "1324789502"

    def send_telegram_notification(self, message: str):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            params = {"chat_id": self.telegram_chat_id, "text": message}
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            logging.info(f"Telegram bildirimi gönderildi: {message}")
        except requests.RequestException as e:
            logging.error(f"Telegram bildirimi gönderilemedi: {e}")

    def check_token(self, token_address: str, detect_time: float):
        url = self.pair_url.format(tokenAddress=token_address)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            pairs = response.json()
            raydium_pairs = [p for p in pairs if p.get('dexId') == 'raydium']

            if raydium_pairs:
                pair = raydium_pairs[0]
                pair_address = pair.get('pairAddress')
                if pair_address in self.pairs_data and self.pairs_data[pair_address].get('notified', False):
                    return True  # Daha önce bildirildiyse izlemeyi bırak

                fdv = float(pair.get('fdv', 0))
                if fdv >= self.marketcap_threshold:
                    token_name = pair.get('baseToken', {}).get('symbol', 'Unknown')
                    price_usd = float(pair.get('priceUsd', 0))
                    created_at = pair.get('pairCreatedAt', 0)
                    info = pair.get('info', {})
                    websites = info.get('websites', [])
                    socials = info.get('socials', [])
                    website = next((w['url'] for w in websites if w.get('label') == 'Website'), '')
                    twitter = next((s['url'] for s in socials if s.get('type') == 'twitter'), '')
                    telegram = next((s['url'] for s in socials if s.get('type') == 'telegram'), '')

                    message = (
                        f"Pump.fun’dan Mezun 1M+ Market Cap Yeni Solana Tokenı!\n"
                        f"Token Adresi: {token_address}\n"
                        f"Çift Adresi: {pair_address}\n"
                        f"Token: {token_name}\n"
                        f"Piyasa Değeri: ${fdv:,.2f}\n"
                        f"Fiyat: ${price_usd:.4f}\n"
                        f"Raydium’a Geçiş: {datetime.fromtimestamp(created_at / 1000)}"
                    )
                    if website:
                        message += f"\nWebsite: {website}"
                    if twitter:
                        message += f"\nTwitter: {twitter}"
                    if telegram:
                        message += f"\nTelegram: {telegram}"

                    logging.info(message)
                    self.send_telegram_notification(message)
                    self.pairs_data[pair_address] = {'notified': True}
                    return True  # Bildirildiyse izlemeyi bırak
                else:
                    logging.info(f"Kontrol: {token_address} - FDV: {fdv}")
                    return False  # Henüz 1M+ değil, izlemeye devam et
            return False  # Raydium çifti yoksa
        except Exception as e:
            logging.error(f"Token kontrol hatası: {token_address} - {e}")
            return False

    async def monitor_raydium_liquidity(self):
        uri = "wss://pumpportal.fun/api/data"
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"method": "subscribeRaydiumLiquidity"}))
            logging.info("PumpPortal’a abone olundu, Raydium likidite eklenmeleri dinleniyor...")
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                token_address = data.get("mint")  # Varsayım: Mint adresi mesajda geliyor
                if token_address:
                    detect_time = time.time()
                    logging.info(f"Raydium’a likidite eklendi: {token_address} - Tespit zamanı: {datetime.fromtimestamp(detect_time)}")
                    self.new_tokens[token_address] = detect_time

                # Tokenları periyodik olarak kontrol et
                current_time = time.time()
                tokens_to_remove = []
                for token_address, detect_time in list(self.new_tokens.items()):
                    if current_time - detect_time >= self.monitor_duration:
                        tokens_to_remove.append(token_address)
                        logging.info(f"Token izleme süresi doldu: {token_address}")
                    elif current_time - detect_time >= self.check_interval:
                        if self.check_token(token_address, detect_time):
                            tokens_to_remove.append(token_address)
                        self.new_tokens[token_address] = current_time  # Son kontrol zamanını güncelle

                for token in tokens_to_remove:
                    if token in self.new_tokens:
                        del self.new_tokens[token]

                await asyncio.sleep(1)  # CPU’yu yormamak için

async def main():
    bot = SolanaPumpfunBot()
    await bot.monitor_raydium_liquidity()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot kullanıcı tarafından durduruldu")
        bot = SolanaPumpfunBot()
        bot.send_telegram_notification("Solana/Pump.fun Çift Botu durduruldu")

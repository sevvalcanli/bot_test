import json
import time
import asyncio
import requests
import logging
from web3 import Web3
from telegram.ext import Application
from telegram import error as telegram_error

# Log ayarları
logging.basicConfig(
    filename='bsc_pancakeswap_v2_v3_subscribe_liquidity.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

# PancakeSwap V2 Factory ABI (PairCreated olayı)
FACTORY_V2_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "pair", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "PairCreated",
        "type": "event"
    }
]

# PancakeSwap V3 Factory ABI (PoolCreated olayı)
FACTORY_V3_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": True, "internalType": "uint24", "name": "fee", "type": "uint24"},
            {"indexed": False, "internalType": "int24", "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "internalType": "address", "name": "pool", "type": "address"}
        ],
        "name": "PoolCreated",
        "type": "event"
    }
]

# PancakeSwap V2 Pair ABI (Mint olayı)
PAIR_V2_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount0", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "amount1", "type": "uint256"}
        ],
        "name": "Mint",
        "type": "event"
    }
]

# PancakeSwap V3 Pool ABI (Mint olayı)
POOL_V3_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount0", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "amount1", "type": "uint256"},
            {"indexed": False, "internalType": "uint128", "name": "liquidity", "type": "uint128"}
        ],
        "name": "Mint",
        "type": "event"
    }
]

class BSCPancakeSwapBot:
    def __init__(self):
        self.websocket_url = "wss://bsc-mainnet.core.chainstack.com/3b9eb2666965991ede217be32233969e"
        self.w3 = None
        self.factory_v2_address = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"  # Güncel V2 Factory
        self.factory_v2_old_address = "0xBCfCcbde45cE874adCB698cC183deBcF17952812"  # Eski V2 Factory
        self.factory_v3_address = "0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7"  # V3 Factory
        self.dexscreener_url = "https://api.dexscreener.com/token-pairs/v1/bsc/{tokenAddress}"
        self.pools_v2 = {}
        self.pools_v3 = {}
        self.filters = {}
        self.pairs_data = {}  # Uzun vadeli izleme: {pair_address: {'token': token_address, 'timestamp': time.time(), 'notified': False}}
        self.pending_pairs = {}  # Kısa vadeli tekrar deneme: {pair_address: {'token': token_address, 'timestamp': time.time(), 'amount': int}}
        self.marketcap_threshold = 1_000_000  # Bildirim eşiği
        self.min_marketcap_threshold = 20_000  # Listeye ekleme eşiği
        self.reconnect_delay = 5
        self.telegram_bot_token = "7623165271:AAFbGUboSDk2R8xcmsKduYAx48sPACi5wK0"
        self.chat_id = "-4758339028"
        self.running = False
        self.wbnb_address = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"  # WBNB adresi
        self.usdt_address = "0x55d398326f99059fF775485246999027B3197955"  # USDT adresi
        self.application = Application.builder().token(self.telegram_bot_token).build()

    async def baglantiyi_kur(self):
        """WebSocket bağlantısını kurar ve koparsa otomatik yeniden bağlanır."""
        while self.running:
            try:
                if not self.w3 or not self.w3.is_connected():
                    self.w3 = Web3(Web3.WebsocketProvider(self.websocket_url))
                    if self.w3.is_connected():
                        logging.info("WebSocket bağlantısı başarıyla kuruldu.")
                        break
                    else:
                        logging.warning(f"WebSocket bağlantısı başarısız, {self.reconnect_delay} saniye sonra yeniden denenecek.")
                else:
                    break
            except Exception as e:
                logging.error(f"Bağlantı kurma hatası: {e}")
            await asyncio.sleep(self.reconnect_delay)

    async def telegram_bildirim_gonder(self, mesaj: str):
        """Telegram'a asenkron bildirim gönderir, zaman aşımı için yeniden dener."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logging.info("Telegram bildirimi gönderiliyor.")
                await self.application.bot.send_message(chat_id=self.chat_id, text=mesaj, parse_mode="Markdown")
                logging.info(f"Telegram bildirimi gönderildi: {mesaj}")
                break
            except telegram_error.TimedOut:
                logging.warning(f"Telegram zaman aşımı, yeniden deneme {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)
            except telegram_error.TelegramError as e:
                logging.error(f"Telegram hatası: {e}")
                break
            except Exception as e:
                logging.error(f"Beklenmeyen Telegram hatası: {e}")
                break

    async def token_piyasa_degeri_kontrol_et(self, token_adresi: str, pool_adresi: str, amount: int, version: str = "V2"):
        """DexScreener ile tokenın piyasa değerini kontrol eder ve bildirim gönderir."""
        if token_adresi.lower() in [self.wbnb_address.lower(), self.usdt_address.lower()]:
            return False

        url = self.dexscreener_url.format(tokenAddress=token_adresi)
        try:
            cevap = requests.get(url, timeout=10)
            cevap.raise_for_status()
            veri = cevap.json()
            pancakeswap_pairs = [p for p in veri if p.get('dexId') == 'pancakeswap' and p.get('chainId') == 'bsc']
            if not pancakeswap_pairs:
                logging.info(f"DexScreener'dan PancakeSwap çifti bulunamadı: {token_adresi}")
                # DexScreener’da çifti bulamadıysa pending_pairs’e ekle
                if pool_adresi not in self.pending_pairs:
                    self.pending_pairs[pool_adresi] = {
                        'token': token_adresi,
                        'timestamp': time.time(),
                        'amount': amount
                    }
                return False

            cift = pancakeswap_pairs[0]
            cift_adresi = cift.get('pairAddress')
            if self.pairs_data.get(cift_adresi, {}).get('notified', False):
                return True

            fdv = float(cift.get('fdv', 0) or 0)
            logging.info(f"Token: {token_adresi}, FDV: {fdv}")

            if fdv < self.min_marketcap_threshold:
                logging.info(f"Token {token_adresi} FDV ({fdv}) 20K altında, listeye eklenmedi.")
                return False

            if fdv >= self.marketcap_threshold:
                token_adi = cift.get('baseToken', {}).get('symbol', 'Bilinmiyor')
                fiyat_usd = float(cift.get('priceUsd', 0) or 0)
                olusturulma_zamani = int(cift.get('pairCreatedAt', 0)) / 1000 if cift.get('pairCreatedAt') else time.time()
                likidite = float(cift.get('liquidity', {}).get('usd', 0) or 0)
                hacim_24s = float(cift.get('volume', {}).get('h24', 0) or 0)
                yas_dakika = (time.time() - olusturulma_zamani) / 60
                fiyat_degisim_h1 = cift.get("priceChange", {}).get("h1", 0)
                fiyat_degisim_h24 = cift.get("priceChange", {}).get("h24", 0)

                mesaj = (
                    f"🚀 *PancakeSwap {version}’ye Likidite Eklendi!* \n"
                    f"🌐 *BSC @ PancakeSwap* \n"
                    f"🔹 *Token Adı:* {token_adi} \n"
                    f"📍 *Token Adresi:* `{token_adresi}` \n"
                    f"🏊 *Havuz Adresi:* `{pool_adresi}` \n"
                    f"💧 *Eklenen Miktar:* {amount} \n"
                    f"🕰️ *Yaş:* {int(yas_dakika)}dk \n\n"
                    f"📊 *Token İstatistikleri* \n"
                    f" ├ USD: ${fiyat_usd:.4f} {fiyat_degisim_h24}% \n"
                    f" ├ MC: ${fdv:,.2f} \n"
                    f" ├ Hacim: ${hacim_24s/1000:.1f}K \n"
                    f" ├ LP: ${likidite/1000:.1f}K \n"
                    f" ├ 1S: {fiyat_degisim_h1}% 🅑 {cift.get('txns', {}).get('h1', {}).get('buys', 0)} Ⓢ {cift.get('txns', {}).get('h1', {}).get('sells', 0)} \n\n"
                    f"🔗 *Bağlantılar:* \n"
                    f" - [DEX](https://dexscreener.com/bsc/{cift_adresi}) \n"
                    f" - [BscScan](https://bscscan.com/token/{token_adresi}) \n"
                    f" - [PancakeSwap](https://pancakeswap.finance/swap?outputCurrency={token_adresi}) \n"
                )

                await self.telegram_bildirim_gonder(mesaj)
                self.pairs_data[cift_adresi] = {
                    'token': token_adresi,
                    'timestamp': time.time(),
                    'notified': True
                }
                # Pending_pairs’ten çıkar (eğer varsa)
                if pool_adresi in self.pending_pairs:
                    del self.pending_pairs[pool_adresi]
                return True
            else:
                if cift_adresi not in self.pairs_data:
                    self.pairs_data[cift_adresi] = {
                        'token': token_adresi,
                        'timestamp': time.time(),
                        'notified': False
                    }
                # Pending_pairs’ten çıkar (eğer varsa)
                if pool_adresi in self.pending_pairs:
                    del self.pending_pairs[pool_adresi]
                return False
        except requests.exceptions.Timeout:
            logging.error(f"DexScreener zaman aşımı: {token_adresi}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"DexScreener isteği hatası: {token_adresi} - {e}")
            return False
        except Exception as e:
            logging.error(f"Token piyasa değeri kontrol hatası: {token_adresi} - {e}")
            return False

    async def pending_pairs_tekrar_kontrol_et(self):
        """DexScreener’da bulunmayan tokenları kısa vadeli tekrar kontrol eder."""
        while self.running:
            current_time = time.time()
            to_remove = []

            for pool_address, data in list(self.pending_pairs.items()):
                elapsed_time = (current_time - data['timestamp']) / 60  # Dakika cinsinden
                if elapsed_time > 10:  # 10 dakika geçtiyse çıkar
                    to_remove.append(pool_address)
                else:
                    token_adresi = data['token']
                    amount = data['amount']
                    logging.info(f"Pending token tekrar kontrol ediliyor: {token_adresi}")
                    notified = await self.token_piyasa_degeri_kontrol_et(token_adresi, pool_address, amount)
                    if notified:
                        logging.info(f"Pending token {token_adresi} için bildirim gönderildi")

            # Süresi dolanları temizle
            for pool_address in to_remove:
                logging.info(f"Pending token süresi doldu ve listeden çıkarıldı: {self.pending_pairs[pool_address]['token']}")
                del self.pending_pairs[pool_address]

            await asyncio.sleep(30)  # Her 30 saniyede bir kontrol et

    async def tokenlari_tekrar_kontrol_et(self):
        """2 saat boyunca tokenları izler ve tekrar kontrol eder."""
        while self.running:
            current_time = time.time()
            to_remove = []

            for pair_address, data in list(self.pairs_data.items()):
                elapsed_time = (current_time - data['timestamp']) / 60  # Dakika cinsinden
                if elapsed_time > 120:  # 2 saat (120 dakika) geçtiyse temizle
                    to_remove.append(pair_address)
                elif not data['notified']:
                    token_adresi = data['token']
                    logging.info(f"Token tekrar kontrol ediliyor: {token_adresi}")
                    notified = await self.token_piyasa_degeri_kontrol_et(token_adresi, pair_address, 0)
                    if notified:
                        logging.info(f"Token {token_adresi} için bildirim gönderildi (tekrar kontrol)")

            # Süresi dolanları temizle
            for pair_address in to_remove:
                logging.info(f"Token izleme süresi doldu ve listeden çıkarıldı: {self.pairs_data[pair_address]['token']}")
                del self.pairs_data[pair_address]

            await asyncio.sleep(300)  # Her 5 dakikada bir kontrol et (300 saniye)

    async def subscribe_pancakeswap_v2_liquidity(self, pool_adresi: str):
        """V2 havuzlarındaki Mint olaylarını asenkron dinler ve hemen DexScreener kontrolü yapar."""
        await self.baglantiyi_kur()
        if not self.w3.is_connected():
            return

        filter_id = self.w3.eth.filter({
            "address": pool_adresi,
            "topics": ["0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"]
        }).filter_id
        self.filters[pool_adresi] = filter_id

        try:
            initial_events = self.w3.eth.get_filter_logs(filter_id)
            for event in initial_events:
                data = event['data'].hex()
                if len(data) >= 128:
                    amount0 = int(data[2:66], 16)
                    amount1 = int(data[66:130], 16)
                    token0 = self.pools_v2[pool_adresi]['token0']
                    token1 = self.pools_v2[pool_adresi]['token1']
                    logging.info(f"V2 Likidite eklendi (ilk kontrol) - Havuz: {pool_adresi}, Token0: {token0}, Token1: {token1}, Miktar: {amount0}/{amount1}")
                    await self.token_piyasa_degeri_kontrol_et(token0, pool_adresi, amount0, "V2")
                    await self.token_piyasa_degeri_kontrol_et(token1, pool_adresi, amount1, "V2")
                else:
                    logging.warning(f"V2 Havuz {pool_adresi} için eksik data (ilk kontrol): {data}")
        except Exception as e:
            logging.error(f"V2 İlk olayları alma hatası: {pool_adresi} - {e}")

        while self.running and pool_adresi in self.pools_v2:
            try:
                events = self.w3.eth.get_filter_changes(filter_id)
                for event in events:
                    data = event['data'].hex()
                    if len(data) >= 128:
                        amount0 = int(data[2:66], 16)
                        amount1 = int(data[66:130], 16)
                        token0 = self.pools_v2[pool_adresi]['token0']
                        token1 = self.pools_v2[pool_adresi]['token1']
                        logging.info(f"V2 Likidite eklendi - Havuz: {pool_adresi}, Token0: {token0}, Token1: {token1}, Miktar: {amount0}/{amount1}")
                        await self.token_piyasa_degeri_kontrol_et(token0, pool_adresi, amount0, "V2")
                        await self.token_piyasa_degeri_kontrol_et(token1, pool_adresi, amount1, "V2")
                    else:
                        logging.warning(f"V2 Havuz {pool_adresi} için eksik data: {data}")
                await asyncio.sleep(2)
            except ValueError as e:
                logging.error(f"V2 Havuz dinleme hatası (ValueError): {pool_adresi} - {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()
            except Exception as e:
                logging.error(f"V2 Havuz dinleme hatası: {pool_adresi} - {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()

    async def subscribe_pancakeswap_v3_liquidity(self, pool_adresi: str):
        """V3 havuzlarındaki Mint olaylarını asenkron dinler ve hemen DexScreener kontrolü yapar."""
        await self.baglantiyi_kur()
        if not self.w3.is_connected():
            return

        filter_id = self.w3.eth.filter({
            "address": pool_adresi,
            "topics": ["0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae162af2b1c"]
        }).filter_id
        self.filters[pool_adresi] = filter_id

        try:
            initial_events = self.w3.eth.get_filter_logs(filter_id)
            for event in initial_events:
                data = event['data'].hex()
                if len(data) >= 192:
                    amount0 = int(data[2:66], 16)
                    amount1 = int(data[66:130], 16)
                    token0 = self.pools_v3[pool_adresi]['token0']
                    token1 = self.pools_v3[pool_adresi]['token1']
                    logging.info(f"V3 Likidite eklendi (ilk kontrol) - Havuz: {pool_adresi}, Token0: {token0}, Token1: {token1}, Miktar: {amount0}/{amount1}")
                    await self.token_piyasa_degeri_kontrol_et(token0, pool_adresi, amount0, "V3")
                    await self.token_piyasa_degeri_kontrol_et(token1, pool_adresi, amount1, "V3")
                else:
                    logging.warning(f"V3 Havuz {pool_adresi} için eksik data (ilk kontrol): {data}")
        except Exception as e:
            logging.error(f"V3 İlk olayları alma hatası: {pool_adresi} - {e}")

        while self.running and pool_adresi in self.pools_v3:
            try:
                events = self.w3.eth.get_filter_changes(filter_id)
                for event in events:
                    data = event['data'].hex()
                    if len(data) >= 192:
                        amount0 = int(data[2:66], 16)
                        amount1 = int(data[66:130], 16)
                        token0 = self.pools_v3[pool_adresi]['token0']
                        token1 = self.pools_v3[pool_adresi]['token1']
                        logging.info(f"V3 Likidite eklendi - Havuz: {pool_adresi}, Token0: {token0}, Token1: {token1}, Miktar: {amount0}/{amount1}")
                        await self.token_piyasa_degeri_kontrol_et(token0, pool_adresi, amount0, "V3")
                        await self.token_piyasa_degeri_kontrol_et(token1, pool_adresi, amount1, "V3")
                    else:
                        logging.warning(f"V3 Havuz {pool_adresi} için eksik data: {data}")
                await asyncio.sleep(2)
            except ValueError as e:
                logging.error(f"V3 Havuz dinleme hatası (ValueError): {pool_adresi} - {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()
            except Exception as e:
                logging.error(f"V3 Havuz dinleme hatası: {pool_adresi} - {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()

    async def factory_v2_olaylarini_dinle(self, factory_address: str, pools_dict: dict):
        """V2 Factory’deki PairCreated olaylarını asenkron dinler."""
        await self.baglantiyi_kur()
        if not self.w3.is_connected():
            logging.error("WebSocket bağlantısı sağlanamadı, bot duruyor.")
            return

        filter_id = self.w3.eth.filter({
            "address": factory_address,
            "topics": ["0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"]
        }).filter_id

        while self.running:
            try:
                events = self.w3.eth.get_filter_changes(filter_id)
                for event in events:
                    token0 = self.w3.to_checksum_address(event['topics'][1].hex()[-40:])
                    token1 = self.w3.to_checksum_address(event['topics'][2].hex()[-40:])
                    pool_adresi = self.w3.to_checksum_address(event['data'].hex()[26:66])
                    logging.info(f"V2 Yeni havuz oluşturuldu: {pool_adresi} - {token0}/{token1}")
                    pools_dict[pool_adresi] = {'token0': token0, 'token1': token1}
                    asyncio.create_task(self.subscribe_pancakeswap_v2_liquidity(pool_adresi))
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"V2 Factory ({factory_address}) dinleme hatası: {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()

    async def factory_v3_olaylarini_dinle(self):
        """V3 Factory’deki PoolCreated olaylarını asenkron dinler."""
        await self.baglantiyi_kur()
        if not self.w3.is_connected():
            logging.error("WebSocket bağlantısı sağlanamadı, bot duruyor.")
            return

        filter_id = self.w3.eth.filter({
            "address": self.factory_v3_address,
            "topics": ["0x783cca1c0412dd0d695e784568c96da2e9c22cb7ebbea2b1307275b7f5a6104e"]
        }).filter_id

        while self.running:
            try:
                events = self.w3.eth.get_filter_changes(filter_id)
                for event in events:
                    token0 = self.w3.to_checksum_address(event['topics'][1].hex()[-40:])
                    token1 = self.w3.to_checksum_address(event['topics'][2].hex()[-40:])
                    pool_adresi = self.w3.to_checksum_address(event['data'].hex()[66:106])
                    logging.info(f"V3 Yeni havuz oluşturuldu: {pool_adresi} - {token0}/{token1}")
                    self.pools_v3[pool_adresi] = {'token0': token0, 'token1': token1}
                    asyncio.create_task(self.subscribe_pancakeswap_v3_liquidity(pool_adresi))
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"V3 Factory dinleme hatası: {e}")
                await asyncio.sleep(self.reconnect_delay)
                await self.baglantiyi_kur()

    async def izlemeyi_baslat(self):
        """Botu başlatır ve V2/V3 likidite eklenmesini izler."""
        logging.info("Bot başlatıldı, hoş geldiniz mesajı gönderiliyor.")
        self.running = True
        await self.telegram_bildirim_gonder(
            "🚀 *CryptoGemTR Topluluğuna Hoş Geldiniz!* \n"
            "BSC ağında PancakeSwap her yeni likidite eklenmesini (1M+ piyasa değeri) gerçek zamanlı izliyorum. "
            "*Botunuz hizmetinizde!*"
        )
        asyncio.create_task(self.factory_v2_olaylarini_dinle(self.factory_v2_address, self.pools_v2))
        asyncio.create_task(self.factory_v2_olaylarini_dinle(self.factory_v2_old_address, self.pools_v2))
        asyncio.create_task(self.factory_v3_olaylarini_dinle())
        asyncio.create_task(self.tokenlari_tekrar_kontrol_et())
        asyncio.create_task(self.pending_pairs_tekrar_kontrol_et())  # Yeni eklenen kısa vadeli kontrol
        while self.running:
            await asyncio.sleep(10)

    def botu_calistir(self):
        """Botu çalıştırır ve Telegram polling’i başlatır."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.izlemeyi_baslat())
        self.application.run_polling()

if __name__ == "__main__":
    bot = BSCPancakeSwapBot()
    bot.botu_calistir()

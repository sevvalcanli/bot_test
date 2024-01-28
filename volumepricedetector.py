import requests
from binance.client import Client
from telegram import Bot
import time
from telegram.error import TimedOut
from telegram.error import NetworkError
import asyncio

# Binance API anahtarları
binance_api_key = "WUYmf7MkDmmhmMXEambiZfPgXN5aKDfpNX2TVIS6MoCVesuGdGYqHRNAUcB8pJJw"
binance_api_secret = "iFlPsS4l2xxG7Ac9TS3JBdTnCen2t97h8QL8mqoD0FfvMJsPA2NO1GYHnhPWrywt"
client = Client(binance_api_key, binance_api_secret)
# Telegram bot token
telegram_bot_token = "6785803733:AAEpf6b5DhfCLVBC6CZILZUe86My0Kaz7x8"
telegram_chat_id = "-4052303995"

# Binance ve Telegram bağlantıları
binance_client = Client(api_key=binance_api_key, api_secret=binance_api_secret)
telegram_bot = Bot(token=telegram_bot_token)

# Eşik değerleri
min_price_change_percentage = 0.5
min_volume_threshold = 5000

async def send_telegram_message(message):
    retries = 3  # İstenen sayıda tekrar deneme
    for attempt_number in range(1, retries + 1):
        try:
            # Telegram mesaj gönderme işlemi
            await telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode='HTML')
            print("Mesaj başarıyla gönderildi.")
            break  # Başarılı gönderimde döngüden çık
        except TimedOut as e:
            print(f"Timed out hatası! Tekrar denenecek. Hata: {e}")
            if attempt_number < retries:
                print("Tekrar deneniyor...")
                await asyncio.sleep(5)  # Belirli bir süre bekleme
            else:
                print("İstenen sayıda deneme yapıldı, işlem başarısız.")
        except NetworkError as e:
            print(f"Network hatası! Tekrar denenecek. Hata: {e}")
            if attempt_number < retries:
                print("Tekrar deneniyor...")
                await asyncio.sleep(5)  # Belirli bir süre bekleme
            else:
                print("İstenen sayıda deneme yapıldı, işlem başarısız.")

def get_quote_asset(symbol):
    ticker = binance_client.get_ticker(symbol=symbol)
    if 'symbol' in ticker:
        symbol_info = binance_client.get_symbol_info(ticker['symbol'])
        base_asset = symbol_info['baseAsset']
        quote_asset = symbol_info['quoteAsset']
        tradingview_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
        return base_asset, quote_asset, tradingview_url
    return None, None, None
    
def get_binance_symbols():
    exchange_info = client.get_exchange_info()
    symbols = exchange_info['symbols']
    usdt_pairs = [symbol['symbol'] for symbol in symbols if symbol['quoteAsset'] == 'USDT']
    return usdt_pairs

def format_value(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"

async def scan_usdt_pairs():
    while True:
        symbols = get_binance_symbols()

        for symbol in symbols:
            
            # Sadece USDT çiftlerini kontrol et
            if symbol.endswith("USDT"):
                try:
                    kline_data = binance_client.get_klines(symbol=symbol, interval="1m", limit=2)
                    response = requests.get(f"https://api.binance.com/api/v3/ticker?symbol={symbol}&windowSize=1m", timeout=20).json()
                    response_24h = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=20).json()
                    
                    last_price = float(response["lastPrice"])
                    quote_volume_1min = float(response['quoteVolume'])
                    volume_1min = float(response['volume'])
                    price_change_percentage_1min = float(response['priceChangePercent'])
                    price_change_1min = float(response['priceChange'])
                    weightedAvgPrice = float(response['weightedAvgPrice'])
                    price_change_percentage_24h = float(response_24h['priceChangePercent'])
                    quote_volume_24h = float(response_24h['quoteVolume'])
                    buys_amount = float(kline_data[0][9])
                    high_price = float(response['highPrice'])
                    low_price = float(response['lowPrice'])
                    open_price = float(response['openPrice'])
                    num_trades = kline_data[0][8]
                    # 1 dakikalık alım yüzdesi
                    if quote_volume_1min != 0:
                        buy_percentage_1min = (buys_amount / quote_volume_1min) * 100
                    else:
                        buy_percentage_1min = 0
    
                    if price_change_percentage_1min > min_price_change_percentage and quote_volume_1min > min_volume_threshold:
                        base_asset, quote_asset, tradingview_url = get_quote_asset(symbol)
                        if base_asset and quote_asset:
                            message = (
                                f"${symbol} | #{symbol} |  <a href='{tradingview_url}'>TradingView</a>\n"
                                f"Son Fiyat: {last_price:.4f} ({price_change_percentage_24h:.1f}% in 24h)\n"
                                f"└1 Dakikalık Değişim: {price_change_percentage_1min:.4f}% 📈\n"
                                f"Yüksek Fiyat: {high_price:.4f}\n"
                                f"Düşük Fiyat: {low_price:.4f}\n"
                                f"Açılış Fiyatı: {open_price:.4f}\n"
                                f"Fiyat Değişimi: {price_change_1min:.4f}\n"
                                f"Ortalama Fiyat: {weightedAvgPrice:.4f}\n"
                                f"{format_value(quote_volume_1min)} USDT 1 Dakikadaki İşlem\n"
                                f"└Alım: {format_value(buys_amount)} USDT [{buy_percentage_1min:.0f}%] 🟢\n"
                                f"Yapılan İşlem Sayısı:{num_trades}\n"
                                f"24 Saatlik Hacim: {format_value(quote_volume_24h)} USDT"
                            )
                            await send_telegram_message(message)
                except Exception as e:
                    print(f"Hata oluştu: {e}")
        await asyncio.sleep(5)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(scan_usdt_pairs())

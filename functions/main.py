from firebase_functions import https_fn, scheduler_fn
from firebase_admin import initialize_app, storage

# This file aims to gather share information and update them
#   in real time. A default list has been specified.

import yfinance as yf
import time
import json

share_tickers = [
    # Share Tickers
    "AAPL",      # Apple Inc.
    "MSFT",      # Microsoft Corporation
    "GOOGL",     # Alphabet Inc.
    "AMZN",      # Amazon.com, Inc.
    "TSLA",      # Tesla, Inc.
    "META",      # Meta Platforms, Inc. (Facebook)
    "NVDA",      # NVIDIA Corporation
    "BRK-B",     # Berkshire Hathaway Inc.
    "JNJ",       # Johnson & Johnson
    "V",         # Visa Inc.
    "WMT",       # Walmart Inc.
    "PG",        # Procter & Gamble Co.
    "JPM",       # JPMorgan Chase & Co.
    "DIS",       # The Walt Disney Company
    "HD",        # The Home Depot, Inc.
    "MA",        # Mastercard Incorporated
    "XOM",       # Exxon Mobil Corporation
    "NFLX",      # Netflix, Inc.
    "INTC",      # Intel Corporation
    "PYPL",      # PayPal Holdings, Inc.
]

crypto_tickers = [
    # Crypto Tickers
    "BTC-USD",   # Bitcoin
    "ETH-USD",   # Ethereum
    "BNB-USD",   # Binance Coin
    "ADA-USD",   # Cardano
    "SOL-USD",   # Solana
    "XRP-USD",   # Ripple (XRP)
    "DOT-USD",   # Polkadot
    "LTC-USD",   # Litecoin
    "DOGE-USD",  # Dogecoin
    "MATIC-USD"  # Polygon
]


# List of updated shares
_shares = {}


# Stores information about a particular share
class Share(dict):
    # Share Type i.e. share or crypto
    # Short Name e.g. BTC-USD
    # Long Name e.g. Bitcoin
    # Price in a specific currency
    # History is [{Open: xxx, Close: xxx, High: xxx, ...}, ...] from yfinance
    # Esg is environental, social, and governance scores as a JSON
    def __init__(self, share_type: str, short_name: str, long_name: str, price: float, currency: str, history: list[dict], esg):
        self.share_type = share_type
        self.short_name = short_name
        self.long_name = long_name
        self.price = price
        self.currency = currency
        self.history = history
        self.esg = esg
        dict.__init__(self, short_name=short_name, long_name=long_name, price=price, currency=currency, history=history, esg=esg)
        

def _research_share(ticker: str, share_type: str) -> Share:
    stock = yf.Ticker(ticker)
    info = stock.info
    history = stock.history(period="1mo").to_dict("records")
    try:
        if share_type == "share":
            esg = {
                "total": stock.get_sustainability(as_dict=True)["esgScores"]["totalEsg"],
                "environment": stock.get_sustainability(as_dict=True)["esgScores"]["environmentScore"],
                "social": stock.get_sustainability(as_dict=True)["esgScores"]["socialScore"],
                "governance": stock.get_sustainability(as_dict=True)["esgScores"]["governanceScore"]
            }
        else:
            esg = {}

        return Share(share_type, ticker, info["longName"], info.get("currentPrice", info["open"]), info["currency"], history, esg)
    except KeyError as e:
        print(e)
        print(info)
        print("Cannot retrieve data, possibly ratelimited?")


# Private subroutine to look up shares
def _research_shares(share_tickers, crypto_tickers) -> None:
    print("Looking up shares...")

    for ticker in share_tickers:
        # Research particular share
        print(f"Searching share {ticker}...")
        _shares[ticker] = _research_share(ticker, "share")

        # Wait to avoid being ratelimited
        time.sleep(2)

    for ticker in crypto_tickers:
        # Research particular crypto
        print(f"Searching crypto {ticker}...")
        _shares[ticker] = _research_share(ticker, "crypto")

        # Wait to avoid being ratelimited
        time.sleep(2)

    storage.bucket().blob("stocks.json").upload_from_string(json.dumps(_shares))


# Get updated share information
def get_share_information() -> list[Share]:
    try:
        stock_data = storage.bucket().blob("stocks.json").download_as_text()
        load_stocks_from_text(stock_data)
    except:
        pass

    return _shares.copy()


def jsonify_shares() -> str:
    return json.dumps(list(get_share_information().values()), default=lambda s: vars(s))


def load_stocks_from_text(data: str):
    global _shares

    if len(data) == 0:
        return
    
    _shares = json.loads(data)

initialize_app()


@https_fn.on_request()
def get_stocks(req: https_fn.Request) -> https_fn.Response:
    return json.loads(jsonify_shares())


# @https_fn.on_request()
# def TODO_REMOVE_research(req: https_fn.Request) -> https_fn.Response:
#     _research_shares(share_tickers, crypto_tickers)


@scheduler_fn.on_schedule(schedule="every 60 minutes")
def update_stock_list(event: scheduler_fn.ScheduledEvent) -> None:
    _research_shares(share_tickers, crypto_tickers)


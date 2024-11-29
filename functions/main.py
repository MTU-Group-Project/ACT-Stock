# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn, scheduler_fn
from firebase_admin import initialize_app, storage

# This file aims to gather share information and update them
#   in real time. A default list has been specified.

import yfinance as yf
import time
import json
import threading

tickers = [
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
    # Short Name e.g. BTC-USD
    # Long Name e.g. Bitcoin
    # Price in a specific currency
    # History is [{Open: xxx, Close: xxx, High: xxx, ...}, ...] from yfinance
    def __init__(self, short_name: str, long_name: str, price: float, currency: str, history: list[dict]):
        self.short_name = short_name
        self.long_name = long_name
        self.price = price
        self.currency = currency
        self.history = history
        dict.__init__(self, short_name=short_name, long_name=long_name, price=price, currency=currency, history=history)


# Private subroutine to look up shares
def _research_shares() -> None:
    print("Looking up shares...")

    for ticker in tickers:
        print(f"Searching {ticker}...")
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period="1mo").to_dict("records")
        try:
            _shares[ticker] = Share(ticker, info["longName"], info.get("currentPrice", info["open"]), info["currency"], history)
        except KeyError as e:
            print(e)
            print(info)
            print("Cannot retrieve data, possibly ratelimited?")
            break

        time.sleep(2)

    storage.bucket().blob("stocks.json").upload_from_string(json.dumps(_shares))


# Get updated share information
def get_share_information() -> list[Share]:
    try:
        stock_data = storage.bucket().blob("stocks.json").download_as_text()
        load_stocks_from_text(stock_data)
    except Exception:
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
    return https_fn.Response(
        jsonify_shares(),
		status=200,
		headers=[
			("Content-Type", "application/json")
		]
    )


@scheduler_fn.on_schedule(schedule="every 60 minutes")
def update_stock_list(event: scheduler_fn.ScheduledEvent) -> None:
    _research_shares()


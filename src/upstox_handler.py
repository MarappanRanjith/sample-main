import requests
from urllib.parse import quote
from src.config import UPSTOX_ACCESS_TOKEN, UPSTOX_BASE_URL
from src.utils import logger


def get_auth_headers():
    """Return read-only Authorization headers using the analytics token.

    This function intentionally uses a single long-lived access token
    (UPSTOX_ACCESS_TOKEN). No OAuth flow or token generation is performed
    by this codebase.
    """
    if not UPSTOX_ACCESS_TOKEN:
        logger.error("UPSTOX_ACCESS_TOKEN is not set. Set it in your .env before running.")
        raise RuntimeError("UPSTOX_ACCESS_TOKEN is not set. Set it in your .env before running.")
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}"
    }


class UpstoxHandler:
    """Read-only Upstox API client using a long-lived analytics token.

    Provides methods to fetch option chains, historical candles, and
    live quotes. All methods are read-only; there are no order APIs.
    """
    def __init__(self):
        logger.info("UpstoxHandler (read-only) initialized.")

    def get_options_chain(self, symbol, expiry_date):
        encoded_symbol = quote(symbol)
        endpoint = f"{UPSTOX_BASE_URL}/option/chain?instrument_key={encoded_symbol}&expiry_date={expiry_date}"
        try:
            response = requests.get(endpoint, headers=get_auth_headers(), timeout=10)
            if response.status_code != 200:
                logger.error(f"RAW OI API ERROR: {response.text}")
                return None
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, 'text', None)
            status_code = getattr(e.response, 'status_code', None)
            logger.error(
                f"Failed to fetch options chain: {e} | status={status_code} text={error_text}"
            )
            return None

    def get_historical_data(self, symbol, interval, from_date, to_date):
        encoded_symbol = quote(symbol)
        endpoint = f"{UPSTOX_BASE_URL}/historical-candle/{encoded_symbol}/{interval}/{to_date}/{from_date}"
        try:
            response = requests.get(endpoint, headers=get_auth_headers(), timeout=15)
            if response.status_code != 200:
                logger.error(
                    f"Upstox historical data failed: {response.status_code} {response.text} | symbol={symbol} interval={interval} from={from_date} to={to_date}"
                )
                return None
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, 'text', None)
            status_code = getattr(e.response, 'status_code', None)
            logger.error(
                f"Failed to fetch historical data: {e} | status={status_code} text={error_text}"
            )
            return None

    def get_live_quote(self, symbol):
        endpoint = f"{UPSTOX_BASE_URL}/market-quote/ltp"
        params = {"instrument_key": symbol}
        try:
            response = requests.get(endpoint, headers=get_auth_headers(), params=params, timeout=10)
            if response.status_code != 200:
                logger.error(
                    f"Upstox live quote failed: {response.status_code} {response.text} | symbol={symbol}"
                )
                return None
            return response.json()
        except requests.RequestException as e:
            error_text = getattr(e.response, 'text', None)
            status_code = getattr(e.response, 'status_code', None)
            logger.error(
                f"Failed to fetch live quote: {e} | status={status_code} text={error_text}"
            )
            return None

    def get_intraday_data(self, symbol, interval="1minute"):
        from urllib.parse import quote
        import time
        import datetime
        from src.utils import logger

        encoded_symbol = quote(symbol)
        intraday_endpoint = f"{UPSTOX_BASE_URL}/historical-candle/intraday/{encoded_symbol}/{interval}"

        for attempt in range(3):
            try:
                # 1. Try the standard Intraday endpoint first
                response = requests.get(intraday_endpoint, headers=get_auth_headers(), timeout=15)

                if response.status_code == 200:
                    data = response.json()
                    candles = data.get('data', {}).get('candles', [])

                    # 2. If candles exist, return them!
                    if candles:
                        return data

                    # 3. If candles are EMPTY (Weekend Cache Flush), fallback to Historical
                    logger.info(f"Intraday cache empty for {symbol}. Attempting weekend historical fallback...")

                    # Calculate the date of the last Friday
                    today = datetime.date.today()
                    if today.weekday() >= 5: # 5 is Saturday, 6 is Sunday
                        days_to_subtract = today.weekday() - 4
                        friday = today - datetime.timedelta(days=days_to_subtract)
                    else:
                        friday = today - datetime.timedelta(days=1) # Fallback to yesterday

                    date_str = friday.strftime('%Y-%m-%d')

                    # Upstox Historical API requires to_date and from_date
                    hist_endpoint = f"{UPSTOX_BASE_URL}/historical-candle/{encoded_symbol}/{interval}/{date_str}/{date_str}"
                    hist_response = requests.get(hist_endpoint, headers=get_auth_headers(), timeout=15)

                    if hist_response.status_code == 200:
                        logger.info(f"Successfully fetched historical data for {date_str}")
                        return hist_response.json()
                    else:
                        logger.error(f"Historical Fallback Failed: {hist_response.text}")
                        return None

                logger.error(f"Intraday API Error: {response.text}")
            except Exception as e:
                logger.warning(f"Data request timeout/error (Attempt {attempt+1}/3): {e}")

            time.sleep(2) # Wait 2 seconds before retrying

        return None

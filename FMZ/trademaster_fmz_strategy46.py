# This is trademaster_fmz_strategy45.py
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import ta

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_15m/btc_15min_data_2023.csv'

# Load data function
def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_data: {e}")
        raise

# Calculate indicators function
def calculate_indicators(data):
    # EMA calculations
    data['ema_fast'] = data['Close'].ewm(span=3, adjust=False).mean()
    data['ema_slow'] = data['Close'].ewm(span=4, adjust=False).mean()
    data['ema_long'] = data['Close'].ewm(span=5, adjust=False).mean()

    # MACD calculation
    macd_fast = data['Close'].ewm(span=1, adjust=False).mean()
    macd_slow = data['Close'].ewm(span=2, adjust=False).mean()
    data['macd_line'] = macd_fast - macd_slow
    data['signal_line'] = data['macd_line'].ewm(span=3, adjust=False).mean()

    # RSI calculation
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=42).mean()
    avg_loss = loss.rolling(window=42).mean()
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))

    # ATR calculation
    data['tr'] = np.maximum(data['High'] - data['Low'], 
                            np.maximum(abs(data['High'] - data['Close'].shift()), abs(data['Low'] - data['Close'].shift())))
    data['atr'] = data['tr'].rolling(window=12).mean()

    return data

# Strategy class
class MisterBuySellSignalsStrategy(Strategy):
    def init(self):
        self.data = calculate_indicators(self.data)

    def next(self):
        close = self.data.Close[-1]
        atr_value = self.data.atr[-1]
        rsi = self.data.rsi[-1]
        macd_line = self.data.macd_line[-1]
        signal_line = self.data.signal_line[-1]
        ema_fast = self.data.ema_fast[-1]
        ema_slow = self.data.ema_slow[-1]

        # Conditions
        buy_condition = ((ema_fast > ema_slow and ema_fast < ema_slow) or (macd_line > signal_line)) and rsi > 30
        sell_condition = ((ema_fast < ema_slow and ema_fast > ema_slow) or (macd_line < signal_line)) and rsi < 70

        # ATR-based stops
        long_stop = close - atr_value
        short_stop = close + atr_value

        # Buy position
        if buy_condition and not self.position.is_long:
            self.buy()
            self.position.exit(stop=long_stop)
            print(f"Long entry at {close} with stop at {long_stop}")

        # Sell position
        elif sell_condition and not self.position.is_short:
            self.sell()
            self.position.exit(stop=short_stop)
            print(f"Short entry at {close} with stop at {short_stop}")

# Main code
data = load_data(data_path)
bt = Backtest(data, MisterBuySellSignalsStrategy, cash=1000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)

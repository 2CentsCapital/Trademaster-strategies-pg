import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta



data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'


def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return data
    except Exception as e:
        logging.error(f"Error in load_data: {e}")
        raise

# Strategy Class
class IchimokuStrategy(Strategy):
    def init(self):
        # Ichimoku Cloud parameters
        tenkan_period = 9
        kijun_period = 26
        senkou_b_period = 52
        displacement = 26

        # Calculate Ichimoku components
        high = self.data.High
        low = self.data.Low
        close = self.data.Close

        # Tenkan-sen (Conversion Line)
        self.tenkan_sen = self.I(
            lambda h, l: (pd.Series(h).rolling(window=tenkan_period).max() + pd.Series(l).rolling(window=tenkan_period).min()) / 2,
            high, low
        )

        # Kijun-sen (Base Line)
        self.kijun_sen = self.I(
            lambda h, l: (pd.Series(h).rolling(window=kijun_period).max() + pd.Series(l).rolling(window=kijun_period).min()) / 2,
            high, low
        )

        # Senkou Span A (Leading Span A)
        self.senkou_span_a = self.I(
            lambda ts, ks: ((pd.Series(ts) + pd.Series(ks)) / 2).shift(displacement),
            self.tenkan_sen, self.kijun_sen
        )

        # Senkou Span B (Leading Span B)
        self.senkou_span_b = self.I(
            lambda h, l: ((pd.Series(h).rolling(window=senkou_b_period).max() + pd.Series(l).rolling(window=senkou_b_period).min()) / 2).shift(displacement),
            high, low
        )

        # Chikou Span (Lagging Span)
        self.chikou_span = self.I(
            lambda c: pd.Series(c).shift(-displacement),
            close
        )

        # Initialize trade parameters
        self.stop_loss_percentage = 0.05  # 5% Stop Loss
        self.take_profit_percentage = 0.10  # 10% Take Profit
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None

    def next(self):
        # Current index
        i = len(self.data) - 1

        # Fetch current values
        current_close = self.data.Close[-1]
        tenkan_sen = self.tenkan_sen[-1]
        kijun_sen = self.kijun_sen[-1]
        senkou_span_a = self.senkou_span_a[-1]
        senkou_span_b = self.senkou_span_b[-1]

        # Define long and short conditions
        long_condition = (tenkan_sen > kijun_sen) and (current_close > senkou_span_a) and (current_close > senkou_span_b)
        short_condition = (tenkan_sen < kijun_sen) and (current_close < senkou_span_a) and (current_close < senkou_span_b)

        # Entry logic
        if long_condition and not self.position.is_long:
            self.entry_price = current_close
            self.stop_loss = self.entry_price * (1 - self.stop_loss_percentage)
            self.take_profit = self.entry_price * (1 + self.take_profit_percentage)
            self.buy()
        elif short_condition and not self.position.is_short:
            self.entry_price = current_close
            self.stop_loss = self.entry_price * (1 + self.stop_loss_percentage)
            self.take_profit = self.entry_price * (1 - self.take_profit_percentage)
            self.sell()

        # Exit logic for long positions
        if self.position.is_long:
            if current_close <= self.stop_loss or current_close >= self.take_profit:
                self.position.close()
        # Exit logic for short positions
        elif self.position.is_short:
            if current_close >= self.stop_loss or current_close <= self.take_profit:
                self.position.close()


data = load_data(data_path)

bt = Backtest(data,  IchimokuStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)
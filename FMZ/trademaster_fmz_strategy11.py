import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
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
class ElliottWaveTDStrategy(Strategy):
    def init(self):
        # Accessing data
        self.close = pd.Series(self.data.Close)

        # Calculate EMA for Elliott Wave
        self.ema = self.I(ta.ema, self.close, length=21)

        # Initialize TD Sequential counts
        self.td_up_count = np.zeros(len(self.close))
        self.td_down_count = np.zeros(len(self.close))

        # Calculate TD Sequential counts
        for i in range(4, len(self.close)):
            if self.close[i] > self.close[i - 4]:
                self.td_up_count[i] = self.td_up_count[i - 1] + 1 if self.td_up_count[i - 1] != 0 else 1
                self.td_down_count[i] = 0
            elif self.close[i] < self.close[i - 4]:
                self.td_down_count[i] = self.td_down_count[i - 1] + 1 if self.td_down_count[i - 1] != 0 else 1
                self.td_up_count[i] = 0
            else:
                self.td_up_count[i] = 0
                self.td_down_count[i] = 0

        # Generate buy/sell setups
        self.td_buy_setup = (self.td_down_count == 9).astype(int)
        self.td_sell_setup = (self.td_up_count == 9).astype(int)

        # Elliott Wave trend
        self.wave_trend = np.where(self.close > self.ema, 1, -1)
        # Forward fill - not necessary as we use the current value in 'next'

        # Placeholder for wave calculations
        self.wave1 = np.full(len(self.close), np.nan)
        self.wave3 = np.full(len(self.close), np.nan)

        # Calculate wave1 and wave3
        for i in range(1, len(self.close)):
            if self.wave_trend[i] == 1 and self.wave_trend[i - 1] == -1:
                self.wave1[i] = self.close[i]
            elif self.wave_trend[i] == 1:
                self.wave1[i] = self.wave1[i - 1]

            if self.wave_trend[i] == -1 and self.wave_trend[i - 1] == 1:
                self.wave3[i] = self.close[i]
            elif self.wave_trend[i] == -1:
                self.wave3[i] = self.wave3[i - 1]

        # Fibonacci Retracement Levels (placeholders)
        self.wave2_fib = self.wave1 + (self.wave3 - self.wave1) * 0.618
        self.wave4_fib = self.wave3 + (self.wave1 - self.wave3) * 0.382

    def next(self):
        i = len(self.data) - 1  # Current index

        # Buy signal: TD Buy Setup completed and wave trend is upward
        if self.td_buy_setup[i] == 1 and self.wave_trend[i] == 1 and not self.position:
            self.buy()

        # Sell signal: TD Sell Setup completed and wave trend is downward
        elif self.td_sell_setup[i] == 1 and self.wave_trend[i] == -1 and not self.position:
            self.sell()

        # Exit strategy based on wave levels
        if self.position.is_long:
            # Exit long position if price falls below wave1 or rises above wave3
            if self.close[i] <= self.wave1[i] or self.close[i] >= self.wave3[i]:
                self.position.close()

        elif self.position.is_short:
            # Exit short position if price rises above wave1 or falls below wave3
            if self.close[i] >= self.wave1[i] or self.close[i] <= self.wave3[i]:
                self.position.close()


data = load_data(data_path)

bt = Backtest(data, ElliottWaveTDStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)
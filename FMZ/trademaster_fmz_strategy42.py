# This is trademaster_fmz_strategy42.py
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy


data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_2h/btc_2h_data_2023.csv'

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
        return data
    except Exception as e:
        print(f"Error in load_data: {e}")
        raise

# Strategy class
class EnhancedShortStrategy(Strategy):
    # Parameters
    short_duration = 7  # days
    price_drop_percentage = 30  # 30%
    risk_per_trade = 0.02  # 2% risk per trade
    stop_loss_percent = 2  # 2% stop loss
    take_profit_percent = 30  # 30% take profit

    def init(self):
        self.entry_price = None
        self.short_end = None

    def next(self):
        close = self.data.Close[-1]
        equity = self.equity

        # Calculate position size
        risk_amount = equity * self.risk_per_trade
        stop_loss_price = close * (1 + self.stop_loss_percent / 100)
        stop_loss_pips = abs(stop_loss_price - close)
        pip_value = 1  # Assuming 1 pip value for BTC_USDT; adjust if necessary
        position_size = risk_amount / (stop_loss_pips * pip_value)

        # Entry condition
        if not self.position().is_short:
            self.sell(size=position_size)
            self.entry_price = close
            self.short_end = self.data.index[-1] + timedelta(days=self.short_duration)
            print(f"Entering short at {close} on {self.data.index[-1]}")

        # Exit conditions
        exit_condition = self.data.index[-1] >= self.short_end or close <= self.entry_price * (1 - self.price_drop_percentage / 100)
        stop_loss_condition = close >= self.entry_price * (1 + self.stop_loss_percent / 100)
        take_profit_condition = close <= self.entry_price * (1 - self.take_profit_percent / 100)

        # Close the short position based on conditions
        if self.position().is_short and (exit_condition or stop_loss_condition or take_profit_condition):
            self.position().close()
            print(f"Exiting short at {close} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
bt = Backtest(data, EnhancedShortStrategy, cash=1000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)

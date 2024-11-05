import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
import logging
import coloredlogs
import numpy as np
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'

# 2. Indicator Calculation

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
class EMARSI_Cross(Strategy):
    rsi_period = 7
    ema_period = 50
    atr_length = 14

    def init(self):
        # Access data
        self.close = self.data.Close
        self.open = self.data.Open
        self.high = self.data.High
        self.low = self.data.Low

        # Calculate indicators
        # Shift close prices by 1 for RSI calculation as in your original code
        shifted_close = pd.Series(self.close).shift(1)

        # Calculate RSI
        self.rsi = self.I(ta.rsi, shifted_close, length=self.rsi_period)

        # Calculate EMA
        self.ema = self.I(ta.ema, pd.Series(self.data.Close), length=self.ema_period)

        # Calculate ATR
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=self.atr_length)


    def next(self):
        # Get the current index
        i = len(self.data) - 1

        # Ensure we have enough data
        if i < 1:
            return

        # Current and previous prices
        current_close = self.close[-1]
        previous_close = self.close[-2]

        current_open = self.open[-1]

        # Indicator values
        current_ema = self.ema[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # Check if indicators are valid (not NaN)
        if np.isnan(current_ema) or np.isnan(current_rsi) or np.isnan(current_atr):
            return  # Skip this iteration

        # Calculate candle body
        candle_body = abs(current_close - current_open)

        # Define buyFlag and sellFlag
        buyFlag = current_ema > current_close
        sellFlag = current_ema < current_close

        # Define green and red candles
        green_candle = current_close > previous_close
        red_candle = current_close < previous_close

        # Define RSI conditions for buying and selling
        buyRsiFlag = current_rsi < 20
        sellRsiFlag = current_rsi > 80

        # Set reward to risk ratio
        reward_to_risk_ratio = 1.2

        # Long Trade Conditions
        if buyFlag and buyRsiFlag and green_candle:
            # Calculate stop loss distance based on ATR and candle body
            slDist = current_atr + candle_body
            if slDist <= 0 or np.isnan(slDist):
                return  # Cannot proceed with invalid slDist
            # Calculate stop loss and take profit levels
            stop_loss = current_close - slDist  # Stop loss for long position
            take_profit = current_close + (slDist * reward_to_risk_ratio)  # Take profit for long position

            # Close existing short positions if any
            if self.position.is_short:
                self.position.close()

            # Ensure that stop_loss < current_close < take_profit
            if stop_loss >= current_close:
                stop_loss = current_close - 0.0001  # Adjust to be less than current_close

            # Execute the buy order with stop loss and take profit
            self.buy(stop=stop_loss, limit=take_profit)

        # Short Trade Conditions
        elif sellFlag and sellRsiFlag and red_candle:
            # Calculate stop loss distance based on ATR and candle body
            slDist = current_atr + candle_body
            if slDist <= 0 or np.isnan(slDist):
                return  # Cannot proceed with invalid slDist

            # Check for unrealistic slDist values
            max_slDist = current_close * 0.1  # For example, limit slDist to 10% of current_close
            if slDist > max_slDist:
                slDist = max_slDist

            # Calculate stop loss and take profit levels
            stop_loss = current_close + slDist  # Stop loss for short position
            take_profit = current_close - (slDist * reward_to_risk_ratio)  # Take profit for short position

            # Close existing long positions if any
            if self.position.is_long:
                self.position.close()

            # Ensure that take_profit < current_close < stop_loss
            if take_profit >= current_close:
                take_profit = current_close - 0.0001  # Adjust to be less than current_close

            if stop_loss <= current_close:
                stop_loss = current_close + 0.0001  # Adjust to be greater than current_close

            # Add validation to ensure correct ordering
            if not (take_profit < current_close < stop_loss):
                return  # Skip placing the order if the condition is not met

            # Execute the sell order with stop loss and take profit
            self.sell(stop=stop_loss, limit=take_profit)



data = load_data(data_path)

bt = Backtest(data, EMARSI_Cross, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)
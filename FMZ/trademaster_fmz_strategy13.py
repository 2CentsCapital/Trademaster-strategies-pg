import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
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
class SupertrendStrategy(Strategy):
    def init(self):
        # Parameters for Supertrend
        atr_period = 10
        atr_multiplier = 5.0

        # Create a DataFrame to hold the data
        df = pd.DataFrame({
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close
        })

        # Calculate Supertrend with append=False
        supertrend = ta.supertrend(high=df['High'], low=df['Low'], close=df['Close'],
                                   length=atr_period, multiplier=atr_multiplier, append=False)

        # Check if supertrend is not None
        if supertrend is not None:
            # Extract the Supertrend and Direction values
            supertrend_values = supertrend[f'SUPERT_{atr_period}_{atr_multiplier}']
            direction_values = supertrend[f'SUPERTd_{atr_period}_{atr_multiplier}']

            # Register the indicators using self.I()
            self.supertrend = self.I(lambda: supertrend_values.values)
            self.direction = self.I(lambda: direction_values.values)
        else:
            raise ValueError("Supertrend calculation failed. Ensure that the input data is correct.")

    def next(self):
        i = len(self.data) - 1  # Current index

        # Access current and previous values
        current_supertrend = self.supertrend[i]
        previous_supertrend_2 = self.supertrend[i - 2] if i >= 2 else None
        previous_supertrend_3 = self.supertrend[i - 3] if i >= 3 else None
        current_direction = self.direction[i]

        # Initialize signal variables
        signal = 0
        signal_direction = 0

        if current_direction < 0:
            if previous_supertrend_2 is not None and current_supertrend > previous_supertrend_2:
                signal = 1  # Buy signal (long)
                signal_direction = 1

        elif current_direction > 0:
            if previous_supertrend_3 is not None and current_supertrend < previous_supertrend_3:
                signal = -1  # Sell signal (short)
                signal_direction = -1

        # Trade execution
        if signal == 1 and not self.position.is_long:
            self.buy()
        elif signal == -1 and not self.position.is_short:
            self.sell()

        # Position management
        if signal_direction < 0 and self.position.is_short:
            self.position.close()
        elif signal_direction > 0 and self.position.is_long:
            self.position.close()




data = load_data(data_path)

bt = Backtest(data, SupertrendStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)


  


  

       






      
                    

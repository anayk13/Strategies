import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class MovingAverageCrossoverStrategy(Strategy):
    """
    Moving Average Crossover Strategy
    
    This strategy identifies long-term trend shifts using two moving averages of different lengths.
    It aims to enter during the start of an uptrend and exit when the trend reverses.
    
    Entry: When 50-day MA crosses above 200-day MA (Golden Cross)
    Exit: When 50-day MA crosses below 200-day MA (Death Cross)
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'short_ma_period': 50,
            'long_ma_period': 200,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.position = 0  # 0 = flat, 1 = long, -1 = short

    def preprocess_data(self, data, context=None):
        """
        Preprocess input data before signal generation.
        Can handle missing values, normalization, resampling, 
        feature engineering, etc.
        
        Args:
            data (pd.DataFrame): Input OHLCV or feature data.
            context (dict, optional): Extra datasets or metadata.
        
        Returns:
            pd.DataFrame: Preprocessed data.
        """
        if data is None or len(data) == 0:
            return data
        
        # Ensure we have required columns
        required_cols = ['close']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if 'date' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date if date column exists
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)
        
        return data

    def generate_signals(self, data, context=None):
        """
        Core strategy logic: generate trading signals.
        
        Args:
            data (pd.DataFrame): Input OHLCV (and optionally other features).
            context (dict, optional): Additional datasets (pairs, options, ML predictions).
        
        Returns:
            pd.DataFrame: Must include a 'Signal' column 
                          (1=long, -1=short, 0=flat, or fractional weights).
        """
        if data is None or len(data) < self.params['long_ma_period']:
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate moving averages
        short_ma = data['close'].rolling(window=self.params['short_ma_period']).mean()
        long_ma = data['close'].rolling(window=self.params['long_ma_period']).mean()
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic for crossover detection
        for i in range(self.params['long_ma_period'], len(data)):
            current_short_ma = short_ma.iloc[i]
            current_long_ma = long_ma.iloc[i]
            prev_short_ma = short_ma.iloc[i-1]
            prev_long_ma = long_ma.iloc[i-1]
            
            # Skip if we don't have enough data for indicators
            if pd.isna(current_short_ma) or pd.isna(current_long_ma) or \
               pd.isna(prev_short_ma) or pd.isna(prev_long_ma):
                continue
            
            # Golden Cross: Short MA crosses above Long MA (Entry)
            if (self.position == 0 and 
                prev_short_ma <= prev_long_ma and 
                current_short_ma > current_long_ma):
                signals.iloc[i] = 1  # Buy signal
                self.position = 1
                
            # Death Cross: Short MA crosses below Long MA (Exit)
            elif (self.position == 1 and 
                  prev_short_ma >= prev_long_ma and 
                  current_short_ma < current_long_ma):
                signals.iloc[i] = -1  # Sell signal
                self.position = 0
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Moving Average Crossover Strategy
        
        This strategy identifies long-term trend shifts using two moving averages of different lengths.
        It aims to enter during the start of an uptrend and exit when the trend reverses.
        
        Entry: When 50-day moving average crosses above 200-day moving average (Golden Cross)
        Exit: When 50-day moving average crosses below 200-day moving average (Death Cross)
        
        Position Management:
        - One position at a time
        - No pyramiding
        - Long-only strategy
        """

    def parameter_schema(self):
        """
        Define the parameters with metadata (for no-code UI).
        
        Returns:
            dict: Example format:
                {
                    "lookback": {"type": "int", "min": 5, "max": 200, "default": 20},
                    "threshold": {"type": "float", "min": 0.1, "max": 5.0, "default": 2.0}
                }
        """
        return {
            "short_ma_period": {
                "type": "int", 
                "min": 5, 
                "max": 100, 
                "default": 50,
                "description": "Period for short-term moving average (50-day MA)"
            },
            "long_ma_period": {
                "type": "int", 
                "min": 50, 
                "max": 500, 
                "default": 200,
                "description": "Period for long-term moving average (200-day MA)"
            },
            "position_size": {
                "type": "float", 
                "min": 0.1, 
                "max": 10.0, 
                "default": 1.0,
                "description": "Position size multiplier"
            }
        }

    def entry_rules(self, data):
        """
        Define conditions for entering trades.
        By default, uses 'Signal' values directly.
        
        Args:
            data (pd.DataFrame): Data with 'Signal' column.
        
        Returns:
            pd.Series: Series of entry signals (1, -1, or 0).
        """
        if self.signals is not None:
            return (self.signals == 1).astype(int)
        return pd.Series(0, index=data.index)

    def exit_rules(self, data):
        """
        Define conditions for exiting trades.
        Supports holding periods, trailing stops, custom exit logic.
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.Series: Series of exit signals (1=exit, 0=hold).
        """
        if self.signals is not None:
            return (self.signals == -1).astype(int)
        return pd.Series(0, index=data.index)

    def position_sizing(self, data):
        """
        Define how much to allocate per trade.
        Default is equal sizing (1 unit).
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.Series: Position sizes per timestamp.
        """
        return pd.Series(self.params['position_size'], index=data.index)

    def risk_management(self, data):
        """
        Apply stop-loss, take-profit, or max drawdown rules.
        Override for custom risk logic.
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.DataFrame: Adjusted data after applying risk management.
        """
        return data

    def reset_position(self):
        """Reset position state (useful for backtesting)."""
        self.position = 0


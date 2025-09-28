import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class WeeklyBollingerBreakoutStrategy(Strategy):
    """
    Weekly Bollinger Breakout with 200 MA Exit Strategy
    
    This strategy aims to capture strong upward breakouts on weekly charts by entering 
    when price closes above the upper Bollinger Band and exiting only when long-term 
    weakness is confirmed via the 200-period moving average.
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'bollinger_period': 50,
            'bollinger_std': 2.0,
            'ma_period': 200,
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
        if data is None or len(data) < max(self.params['bollinger_period'], self.params['ma_period']):
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate Bollinger Bands
        sma_50 = data['close'].rolling(window=self.params['bollinger_period']).mean()
        std_50 = data['close'].rolling(window=self.params['bollinger_period']).std()
        upper_band = sma_50 + (self.params['bollinger_std'] * std_50)
        
        # Calculate 200-period Moving Average
        ma_200 = data['close'].rolling(window=self.params['ma_period']).mean()
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic
        for i in range(max(self.params['bollinger_period'], self.params['ma_period']), len(data)):
            current_close = data['close'].iloc[i]
            current_upper_band = upper_band.iloc[i]
            current_ma_200 = ma_200.iloc[i]
            
            # Skip if we don't have enough data for indicators
            if pd.isna(current_upper_band) or pd.isna(current_ma_200):
                continue
                
            # Entry Rule: Close > Upper Bollinger Band (only if no position)
            if self.position == 0 and current_close > current_upper_band:
                signals.iloc[i] = 1  # Buy signal
                self.position = 1
                
            # Exit Rule: Close < 200 MA (only if we have a position)
            elif self.position == 1 and current_close < current_ma_200:
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
        Weekly Bollinger Breakout with 200 MA Exit Strategy
        
        Entry: When weekly closing price breaks above the upper Bollinger Band (50-period, 2 std dev)
        Exit: When weekly closing price falls below the 200-period moving average
        
        This strategy captures strong upward breakouts while using the 200 MA as a 
        long-term trend filter for risk management. It maintains only one position 
        at a time with no pyramiding.
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
            "bollinger_period": {
                "type": "int", 
                "min": 10, 
                "max": 100, 
                "default": 50,
                "description": "Period for Bollinger Bands calculation"
            },
            "bollinger_std": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 2.0,
                "description": "Standard deviation multiplier for Bollinger Bands"
            },
            "ma_period": {
                "type": "int", 
                "min": 50, 
                "max": 500, 
                "default": 200,
                "description": "Period for moving average exit signal"
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

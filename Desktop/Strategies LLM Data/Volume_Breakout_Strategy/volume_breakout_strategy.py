import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class VolumeBreakoutStrategy(Strategy):
    """
    Volume Breakout Buy Strategy
    
    This strategy aims to capture potential upward momentum by buying stocks 
    when their current volume exceeds the 100-day average volume.
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'volume_period': 100,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None

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
        
        # Ensure we have the required columns
        required_cols = ['volume']
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
        if data is None or len(data) < self.params['volume_period']:
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate 100-day average volume
        avg_volume = data['volume'].rolling(window=self.params['volume_period']).mean()
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # Generate buy signals when current volume > average volume
        for i in range(self.params['volume_period'], len(data)):
            current_volume = data['volume'].iloc[i]
            current_avg_volume = avg_volume.iloc[i]
            
            # Skip if we don't have enough data for average volume
            if pd.isna(current_avg_volume):
                continue
            
            # Entry Rule: Current day's volume > 100-day average volume
            if current_volume > current_avg_volume:
                signals.iloc[i] = 1  # Buy signal
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Volume Breakout Buy Strategy
        
        This strategy captures potential upward momentum by buying stocks when their 
        current volume exceeds the 100-day average volume. High volume often indicates 
        increased interest and potential price movement.
        
        Entry: When current day's volume > 100-day average volume
        Exit: No specific exit rules (position management not specified)
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
            "volume_period": {
                "type": "int",
                "min": 10,
                "max": 200,
                "default": 100,
                "description": "Number of days for volume average calculation"
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


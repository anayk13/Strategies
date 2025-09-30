import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class GapUpBollingerStrategy(Strategy):
    """
    Gap-Up + Bollinger Band Exit Strategy
    
    This strategy aims to capture short-term profit opportunities and protect gains 
    by selling stocks that exhibit strong upward price spikes (gap-ups) combined 
    with being overextended relative to recent volatility (above upper Bollinger Band).
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
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.previous_closes = {}  # {symbol: previous_close}
        self.bollinger_data = {}   # {symbol: {'sma': [], 'std': [], 'upper_band': []}}

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
        required_cols = ['symbol', 'date', 'open', 'close', 'high']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date
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
        if data is None or len(data) == 0:
            return pd.DataFrame(columns=['Signal'])
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # Process each row
        for i in range(len(data)):
            row = data.iloc[i]
            symbol = row['symbol']
            current_open = row['open']
            current_close = row['close']
            current_high = row['high']
            
            # Initialize data structures for new symbols
            if symbol not in self.previous_closes:
                self.previous_closes[symbol] = None
                self.bollinger_data[symbol] = {'sma': [], 'std': [], 'upper_band': []}
            
            # Store current close as previous close for next iteration
            prev_close = self.previous_closes[symbol]
            self.previous_closes[symbol] = current_close
            
            # Skip if we don't have previous close (first day)
            if prev_close is None:
                continue
            
            # Calculate Bollinger Bands
            self._update_bollinger_bands(symbol, current_close)
            
            # Check if we have enough data for Bollinger Bands
            if len(self.bollinger_data[symbol]['sma']) < self.params['bollinger_period']:
                continue
            
            # Get current Bollinger Band values
            current_upper_band = self.bollinger_data[symbol]['upper_band'][-1]
            
            # Check for Gap-Up + Bollinger Band exit signal
            if self._is_gap_up_exit_signal(current_open, prev_close, current_high, current_upper_band):
                signals.iloc[i] = -1  # Sell signal
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def _update_bollinger_bands(self, symbol, current_close):
        """Update Bollinger Band calculations for a symbol."""
        # Add current close to the data
        closes = self.bollinger_data[symbol]['sma']
        closes.append(current_close)
        
        # Keep only the required period
        if len(closes) > self.params['bollinger_period']:
            closes.pop(0)
        
        # Calculate SMA
        sma = np.mean(closes)
        self.bollinger_data[symbol]['sma'].append(sma)
        
        # Calculate standard deviation
        std = np.std(closes, ddof=0)  # Population standard deviation
        self.bollinger_data[symbol]['std'].append(std)
        
        # Calculate upper Bollinger Band
        upper_band = sma + (self.params['bollinger_std'] * std)
        self.bollinger_data[symbol]['upper_band'].append(upper_band)
        
        # Keep only the required period for all arrays
        for key in ['sma', 'std', 'upper_band']:
            if len(self.bollinger_data[symbol][key]) > self.params['bollinger_period']:
                self.bollinger_data[symbol][key].pop(0)

    def _is_gap_up_exit_signal(self, current_open, prev_close, current_high, upper_band):
        """
        Check if conditions for gap-up exit signal are met.
        """
        # Condition 1: Gap-up (today's open > previous close)
        gap_up = current_open > prev_close
        
        # Condition 2: Current price (high) > Upper Bollinger Band
        above_upper_band = current_high > upper_band
        
        return gap_up and above_upper_band

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Gap-Up + Bollinger Band Exit Strategy
        
        This strategy identifies profit-taking opportunities by selling stocks that:
        1. Open with a gap-up (today's open > previous close)
        2. Are trading above the upper Bollinger Band (overextended)
        
        This combination often indicates overbought conditions and potential
        reversal points, making it an effective risk management tool.
        
        Entry: N/A (this is an exit-only strategy)
        Exit: Gap-up + above upper Bollinger Band
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


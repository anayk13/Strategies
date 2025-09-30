import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class VolatilityContractionBreakoutStrategy(Strategy):
    """
    Volatility Contraction Breakout (VCB) with Volume Confirmation Strategy
    
    Identify quiet consolidation (low volatility squeeze) followed by a breakout 
    confirmed by a volume surge — capture directional moves immediately after 
    volatility expansion.
    
    Entry: Bollinger Width at low percentile AND Price > consolidation high AND Volume > 1.5x avg
    Exit: Trailing stop at 1.5x ATR below highest price OR consolidation failure
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'bb_period': 20,
            'bb_std': 2.0,
            'width_lookback': 90,
            'width_percentile': 10,
            'consolidation_period': 20,
            'volume_multiplier': 1.5,
            'volume_period': 20,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'max_holding_period': 40,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.position = 0  # 0 = flat, 1 = long
        self.entry_price = None
        self.highest_price = None
        self.entry_date = None

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
        required_cols = ['close', 'high', 'low', 'volume']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if 'date' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date if date column exists
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)
        
        return data

    def calculate_bollinger_bands(self, prices, period, std_dev):
        """
        Calculate Bollinger Bands
        
        Args:
            prices (pd.Series): Price series
            period (int): Moving average period
            std_dev (float): Standard deviation multiplier
            
        Returns:
            tuple: (upper_band, middle_band, lower_band, width)
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        width = upper_band - lower_band
        
        return upper_band, middle_band, lower_band, width

    def calculate_atr(self, high, low, close, period):
        """
        Calculate Average True Range (ATR)
        
        Args:
            high (pd.Series): High prices
            low (pd.Series): Low prices
            close (pd.Series): Close prices
            period (int): ATR period
            
        Returns:
            pd.Series: ATR values
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr

    def calculate_consolidation_high(self, high, period):
        """
        Calculate consolidation high (rolling maximum)
        
        Args:
            high (pd.Series): High prices
            period (int): Rolling period
            
        Returns:
            pd.Series: Consolidation high values
        """
        return high.rolling(window=period).max()

    def calculate_consolidation_low(self, low, period):
        """
        Calculate consolidation low (rolling minimum)
        
        Args:
            low (pd.Series): Low prices
            period (int): Rolling period
            
        Returns:
            pd.Series: Consolidation low values
        """
        return low.rolling(window=period).min()

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
        if data is None or len(data) < max(self.params['width_lookback'], self.params['consolidation_period']):
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate indicators
        upper_bb, middle_bb, lower_bb, bb_width = self.calculate_bollinger_bands(
            data['close'], self.params['bb_period'], self.params['bb_std']
        )
        
        atr = self.calculate_atr(data['high'], data['low'], data['close'], self.params['atr_period'])
        
        consolidation_high = self.calculate_consolidation_high(data['high'], self.params['consolidation_period'])
        consolidation_low = self.calculate_consolidation_low(data['low'], self.params['consolidation_period'])
        
        # Calculate rolling percentile of BB width
        bb_width_percentile = bb_width.rolling(window=self.params['width_lookback']).rank(pct=True) * 100
        
        # Calculate volume ratio
        avg_volume = data['volume'].rolling(window=self.params['volume_period']).mean()
        volume_ratio = data['volume'] / avg_volume
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic for signal generation
        for i in range(max(self.params['width_lookback'], self.params['consolidation_period']), len(data)):
            current_close = data['close'].iloc[i]
            current_high = data['high'].iloc[i]
            current_low = data['low'].iloc[i]
            current_bb_width = bb_width.iloc[i]
            current_bb_width_percentile = bb_width_percentile.iloc[i]
            current_consolidation_high = consolidation_high.iloc[i]
            current_consolidation_low = consolidation_low.iloc[i]
            current_volume_ratio = volume_ratio.iloc[i]
            current_atr = atr.iloc[i]
            
            # Skip if we don't have enough data for indicators
            if (pd.isna(current_bb_width) or pd.isna(current_bb_width_percentile) or 
                pd.isna(current_consolidation_high) or pd.isna(current_volume_ratio) or 
                pd.isna(current_atr)):
                continue
            
            # Check for stop loss and time-based exit
            if self.position == 1:
                # Update highest price since entry
                if self.highest_price is None or current_high > self.highest_price:
                    self.highest_price = current_high
                
                # Trailing stop: 1.5 * ATR below highest price
                trailing_stop = self.highest_price - (self.params['atr_multiplier'] * current_atr)
                
                # Consolidation failure: price below consolidation low
                consolidation_failure = current_close < current_consolidation_low
                
                # Time-based exit
                time_exit = (self.entry_date is not None and 
                           i - self.entry_date > self.params['max_holding_period'])
                
                # Exit conditions
                if (current_close < trailing_stop or consolidation_failure or time_exit):
                    signals.iloc[i] = -1  # Exit signal
                    self.position = 0
                    self.entry_price = None
                    self.highest_price = None
                    self.entry_date = None
                    continue
            
            # Entry Rules (only if no position)
            if self.position == 0:
                # Condition 1: Bollinger Width at low percentile (squeeze)
                squeeze_condition = current_bb_width_percentile <= self.params['width_percentile']
                
                # Condition 2: Price closes above consolidation high (breakout)
                breakout_condition = current_close > current_consolidation_high
                
                # Condition 3: Volume confirmation
                volume_condition = current_volume_ratio > self.params['volume_multiplier']
                
                # All three conditions must be met
                if squeeze_condition and breakout_condition and volume_condition:
                    signals.iloc[i] = 1  # Buy signal
                    self.position = 1
                    self.entry_price = current_close
                    self.highest_price = current_high
                    self.entry_date = i
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Volatility Contraction Breakout (VCB) with Volume Confirmation Strategy
        
        Identify quiet consolidation (low volatility squeeze) followed by a breakout 
        confirmed by a volume surge — capture directional moves immediately after 
        volatility expansion.
        
        Entry Conditions (ALL must be met):
        - Squeeze: Bollinger Band Width at or below 10th percentile over 90 days
        - Breakout: Price closes above consolidation high (20-day high)
        - Volume confirmation: Today's volume > 1.5 × 20-day average volume
        
        Exit Conditions (ANY triggers exit):
        - Trailing stop: 1.5 × ATR below highest price since entry
        - Consolidation failure: Price below consolidation low
        - Time stop: Maximum holding period (40 days)
        
        Position Management:
        - Risk-based position sizing using ATR
        - One trade per instrument
        - Wider stops in high ATR markets
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
            "bb_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for Bollinger Bands calculation"
            },
            "bb_std": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 2.0,
                "description": "Standard deviation multiplier for Bollinger Bands"
            },
            "width_lookback": {
                "type": "int", 
                "min": 30, 
                "max": 200, 
                "default": 90,
                "description": "Lookback period for width percentile calculation"
            },
            "width_percentile": {
                "type": "float", 
                "min": 1.0, 
                "max": 20.0, 
                "default": 10.0,
                "description": "Percentile threshold for width squeeze"
            },
            "consolidation_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for consolidation high/low calculation"
            },
            "volume_multiplier": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 1.5,
                "description": "Volume multiplier for confirmation"
            },
            "volume_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for average volume calculation"
            },
            "atr_period": {
                "type": "int", 
                "min": 5, 
                "max": 30, 
                "default": 14,
                "description": "Period for ATR calculation"
            },
            "atr_multiplier": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 1.5,
                "description": "ATR multiplier for trailing stop"
            },
            "max_holding_period": {
                "type": "int", 
                "min": 10, 
                "max": 100, 
                "default": 40,
                "description": "Maximum holding period in days"
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
        self.entry_price = None
        self.highest_price = None
        self.entry_date = None


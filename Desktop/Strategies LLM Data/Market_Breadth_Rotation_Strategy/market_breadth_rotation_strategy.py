import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class MarketBreadthRotationStrategy(Strategy):
    """
    Market Breadth Rotation Strategy
    
    Rotate into strong sectors (or ETFs) and avoid weak markets using market-breadth indicators. 
    Trade top sector ETF(s) while market breadth confirms strength.
    
    Entry: A/D Ratio > 1.0 AND New Highs - New Lows > 0 AND Sector RS top ranked AND Sector > 50MA
    Exit: A/D Ratio < 0.9 OR New Highs - New Lows < 0 OR Sector < 50MA
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'ad_ratio_threshold': 1.0,
            'ad_ratio_exit': 0.9,
            'net_new_highs_threshold': 0,
            'rs_period': 90,
            'ma_period': 50,
            'top_sectors': 2,
            'rebalance_frequency': 20,
            'negative_breadth_days': 3,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.position = 0  # 0 = flat, 1 = long
        self.current_sector = None
        self.last_rebalance = 0

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

    def calculate_advance_decline_ratio(self, advances, declines):
        """
        Calculate Advance-Decline Ratio
        
        Args:
            advances (pd.Series): Number of advancing stocks
            declines (pd.Series): Number of declining stocks
            
        Returns:
            pd.Series: A/D Ratio
        """
        # Avoid division by zero
        return advances / (declines + 1e-8)

    def calculate_net_new_highs(self, new_highs, new_lows):
        """
        Calculate Net New Highs (New Highs - New Lows)
        
        Args:
            new_highs (pd.Series): Number of new highs
            new_lows (pd.Series): Number of new lows
            
        Returns:
            pd.Series: Net new highs
        """
        return new_highs - new_lows

    def calculate_relative_strength(self, sector_returns, market_returns, period):
        """
        Calculate Relative Strength of sector vs market
        
        Args:
            sector_returns (pd.Series): Sector returns
            market_returns (pd.Series): Market returns
            period (int): Rolling period for calculation
            
        Returns:
            pd.Series: Relative strength
        """
        sector_cumulative = (1 + sector_returns).rolling(window=period).apply(lambda x: x.prod() - 1)
        market_cumulative = (1 + market_returns).rolling(window=period).apply(lambda x: x.prod() - 1)
        
        return sector_cumulative / (market_cumulative + 1e-8)

    def calculate_market_breadth(self, data):
        """
        Calculate market breadth indicators
        
        Args:
            data (pd.DataFrame): Market data with breadth indicators
            
        Returns:
            dict: Dictionary of breadth indicators
        """
        # For demo purposes, we'll simulate breadth data
        # In practice, you'd have actual advance/decline data
        np.random.seed(42)
        n = len(data)
        
        # Simulate advancing/declining stocks
        advances = np.random.randint(1000, 3000, n)
        declines = np.random.randint(1000, 3000, n)
        
        # Simulate new highs/lows
        new_highs = np.random.randint(50, 200, n)
        new_lows = np.random.randint(50, 200, n)
        
        # Calculate breadth indicators
        ad_ratio = self.calculate_advance_decline_ratio(
            pd.Series(advances, index=data.index),
            pd.Series(declines, index=data.index)
        )
        
        net_new_highs = self.calculate_net_new_highs(
            pd.Series(new_highs, index=data.index),
            pd.Series(new_lows, index=data.index)
        )
        
        return {
            'ad_ratio': ad_ratio,
            'net_new_highs': net_new_highs
        }

    def calculate_sector_rankings(self, data, context=None):
        """
        Calculate sector relative strength rankings
        
        Args:
            data (pd.DataFrame): Market data
            context (dict, optional): Sector data
            
        Returns:
            pd.Series: Top sector rankings
        """
        # For demo purposes, we'll simulate sector data
        # In practice, you'd have actual sector ETF data
        np.random.seed(42)
        n = len(data)
        
        # Simulate sector returns
        sectors = ['Technology', 'Healthcare', 'Financial', 'Energy', 'Consumer']
        sector_returns = {}
        
        for sector in sectors:
            # Generate correlated but different returns
            base_returns = data['close'].pct_change()
            sector_returns[sector] = base_returns + np.random.normal(0, 0.01, n)
        
        # Calculate relative strength for each sector
        market_returns = data['close'].pct_change()
        sector_rs = {}
        
        for sector in sectors:
            rs = self.calculate_relative_strength(
                sector_returns[sector], 
                market_returns, 
                self.params['rs_period']
            )
            sector_rs[sector] = rs
        
        # Rank sectors by relative strength
        rs_df = pd.DataFrame(sector_rs)
        rankings = rs_df.rank(axis=1, ascending=False)
        
        return rankings

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
        if data is None or len(data) < max(self.params['rs_period'], self.params['ma_period']):
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate market breadth
        breadth = self.calculate_market_breadth(data)
        ad_ratio = breadth['ad_ratio']
        net_new_highs = breadth['net_new_highs']
        
        # Calculate sector rankings
        sector_rankings = self.calculate_sector_rankings(data, context)
        
        # Calculate moving average
        ma = data['close'].rolling(window=self.params['ma_period']).mean()
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic for signal generation
        for i in range(max(self.params['rs_period'], self.params['ma_period']), len(data)):
            current_ad_ratio = ad_ratio.iloc[i]
            current_net_highs = net_new_highs.iloc[i]
            current_close = data['close'].iloc[i]
            current_ma = ma.iloc[i]
            
            # Skip if we don't have enough data
            if (pd.isna(current_ad_ratio) or pd.isna(current_net_highs) or 
                pd.isna(current_close) or pd.isna(current_ma)):
                continue
            
            # Check for rebalancing
            should_rebalance = (i - self.last_rebalance) >= self.params['rebalance_frequency']
            
            # Market breadth conditions
            breadth_healthy = (current_ad_ratio > self.params['ad_ratio_threshold'] and 
                             current_net_highs > self.params['net_new_highs_threshold'])
            
            # Trend condition
            trend_healthy = current_close > current_ma
            
            # Exit conditions
            if self.position == 1:
                # Exit if breadth turns negative
                breadth_negative = (current_ad_ratio < self.params['ad_ratio_exit'] or 
                                  current_net_highs < self.params['net_new_highs_threshold'])
                
                # Exit if trend breaks
                trend_broken = current_close < current_ma
                
                if breadth_negative or trend_broken:
                    signals.iloc[i] = -1  # Exit signal
                    self.position = 0
                    self.current_sector = None
                    continue
            
            # Entry conditions
            if self.position == 0 and breadth_healthy and trend_healthy:
                # Check if we should rebalance or enter
                if should_rebalance or self.current_sector is None:
                    # Find top ranked sector
                    current_rankings = sector_rankings.iloc[i]
                    top_sectors = current_rankings.nsmallest(self.params['top_sectors'])
                    
                    if len(top_sectors) > 0:
                        # Select the top sector
                        selected_sector = top_sectors.index[0]
                        
                        # For demo purposes, we'll use the main data as our "sector"
                        # In practice, you'd check the actual sector ETF data
                        signals.iloc[i] = 1  # Buy signal
                        self.position = 1
                        self.current_sector = selected_sector
                        self.last_rebalance = i
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Market Breadth Rotation Strategy
        
        Rotate into strong sectors (or ETFs) and avoid weak markets using market-breadth indicators. 
        Trade top sector ETF(s) while market breadth confirms strength.
        
        Entry Conditions (ALL must be met):
        - Market Breadth Confirmation: A/D Ratio > 1.0 AND New Highs - New Lows > 0
        - Sector Selection: Rank sectors by RS over trailing 3-6 months, pick top 1-2
        - Trend Filter: Sector ETF close > 50-day MA
        
        Exit Conditions (ANY triggers exit):
        - A/D Ratio falls below 0.9 OR New Highs - New Lows turns negative
        - Sector ETF closes below its 50-day MA
        - Rotate to next ranked sector at rebalance
        
        Position Management:
        - Equal-weight across chosen sector ETFs
        - Rebalance monthly or biweekly
        - Can hold cash if market breadth is negative
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
            "ad_ratio_threshold": {
                "type": "float", 
                "min": 0.5, 
                "max": 2.0, 
                "default": 1.0,
                "description": "A/D Ratio threshold for market breadth confirmation"
            },
            "ad_ratio_exit": {
                "type": "float", 
                "min": 0.5, 
                "max": 1.5, 
                "default": 0.9,
                "description": "A/D Ratio threshold for exit"
            },
            "net_highs_threshold": {
                "type": "int", 
                "min": -100, 
                "max": 100, 
                "default": 0,
                "description": "Net new highs threshold"
            },
            "rs_period": {
                "type": "int", 
                "min": 30, 
                "max": 200, 
                "default": 90,
                "description": "Period for relative strength calculation"
            },
            "ma_period": {
                "type": "int", 
                "min": 20, 
                "max": 100, 
                "default": 50,
                "description": "Period for moving average trend filter"
            },
            "top_sectors": {
                "type": "int", 
                "min": 1, 
                "max": 5, 
                "default": 2,
                "description": "Number of top sectors to select"
            },
            "rebalance_frequency": {
                "type": "int", 
                "min": 5, 
                "max": 50, 
                "default": 20,
                "description": "Rebalancing frequency in days"
            },
            "negative_breadth_days": {
                "type": "int", 
                "min": 1, 
                "max": 10, 
                "default": 3,
                "description": "Days of negative breadth before exit"
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
        self.current_sector = None
        self.last_rebalance = 0

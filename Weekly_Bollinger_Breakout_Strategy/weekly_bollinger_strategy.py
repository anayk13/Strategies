from strategies.base_strategy import BaseStrategy
from datetime import datetime
from typing import Dict, Any, List
from engine.event_engine import MarketEvent, FillEvent, SignalEvent, EventEngine
import logging
import pandas as pd
import numpy as np

class WeeklyBollingerStrategy(BaseStrategy):
    """
    Weekly Bollinger Breakout with 200 MA Exit Strategy
    
    This strategy aims to capture strong upward breakouts on weekly charts by entering 
    when price closes above the upper Bollinger Band and exiting only when long-term 
    weakness is confirmed via the 200-period moving average.
    """
    
    def __init__(self, 
                 event_engine: EventEngine, 
                 logger: logging.Logger, 
                 executor_account_name: str,
                 bollinger_period: int = 50,
                 bollinger_std: float = 2.0,
                 ma_period: int = 200,
                 trade_quantity: int = 100):
        super().__init__(event_engine, logger, executor_account_name)
        
        self.bollinger_period = bollinger_period
        self.bollinger_std = bollinger_std
        self.ma_period = ma_period
        self.trade_quantity = trade_quantity
        
        # Data storage for weekly calculations
        self.weekly_data = {}  # {symbol: {'prices': [], 'timestamps': [], 'volumes': []}}
        self.positions = {}    # {symbol: 'LONG' or 'FLAT'}
        self.last_week = {}    # {symbol: last_processed_week}
        
        # For weekly data aggregation
        self.current_week_data = {}  # {symbol: {'prices': [], 'volumes': [], 'start_time': None}}
        
        self.logger.info(f"[{self.strategy_name}] Initialized with Bollinger Period: {bollinger_period}, "
                        f"Bollinger Std: {bollinger_std}, MA Period: {ma_period}, "
                        f"Trade Quantity: {trade_quantity}")

    async def handle_market_event(self, event: MarketEvent):
        """Handle incoming market data and aggregate to weekly data."""
        symbol = event.instrument_token
        price = event.ltp
        volume = getattr(event, 'volume', 0)
        timestamp = event.timestamp
        
        await self.process_tick(symbol, price, volume, timestamp)

    async def process_tick(self, symbol: str, price: float, volume: float, timestamp: datetime):
        """Process individual tick and aggregate to weekly data."""
        # Get current week
        current_week = timestamp.isocalendar()[1]  # Week number
        current_year = timestamp.year
        
        # Initialize data structures if needed
        if symbol not in self.weekly_data:
            self.weekly_data[symbol] = {'prices': [], 'volumes': [], 'timestamps': []}
            self.positions[symbol] = 'FLAT'
            self.last_week[symbol] = None
            self.current_week_data[symbol] = {'prices': [], 'volumes': [], 'start_time': None}
        
        # Check if this is a new week
        if self.last_week[symbol] is not None and self.last_week[symbol] != current_week:
            # Process the completed week
            await self.process_weekly_data(symbol)
            # Reset current week data
            self.current_week_data[symbol] = {'prices': [], 'volumes': [], 'start_time': None}
        
        # Add current tick to current week data
        if self.current_week_data[symbol]['start_time'] is None:
            self.current_week_data[symbol]['start_time'] = timestamp
        
        self.current_week_data[symbol]['prices'].append(price)
        self.current_week_data[symbol]['volumes'].append(volume)
        
        # Update last week
        self.last_week[symbol] = current_week

    async def process_weekly_data(self, symbol: str):
        """Process completed weekly data and generate signals."""
        if not self.current_week_data[symbol]['prices']:
            return
        
        # Calculate weekly OHLCV
        prices = self.current_week_data[symbol]['prices']
        volumes = self.current_week_data[symbol]['volumes']
        
        weekly_open = prices[0]
        weekly_high = max(prices)
        weekly_low = min(prices)
        weekly_close = prices[-1]
        weekly_volume = sum(volumes)
        weekly_timestamp = self.current_week_data[symbol]['start_time']
        
        # Add to weekly data
        self.weekly_data[symbol]['prices'].append(weekly_close)
        self.weekly_data[symbol]['volumes'].append(weekly_volume)
        self.weekly_data[symbol]['timestamps'].append(weekly_timestamp)
        
        # Keep only enough data for calculations
        max_period = max(self.bollinger_period, self.ma_period)
        if len(self.weekly_data[symbol]['prices']) > max_period:
            self.weekly_data[symbol]['prices'] = self.weekly_data[symbol]['prices'][-max_period:]
            self.weekly_data[symbol]['volumes'] = self.weekly_data[symbol]['volumes'][-max_period:]
            self.weekly_data[symbol]['timestamps'] = self.weekly_data[symbol]['timestamps'][-max_period:]
        
        # Need enough data for both indicators
        if len(self.weekly_data[symbol]['prices']) < max_period:
            return
        
        # Calculate indicators
        prices_series = pd.Series(self.weekly_data[symbol]['prices'])
        
        # Bollinger Bands
        sma_50 = prices_series.rolling(window=self.bollinger_period).mean()
        std_50 = prices_series.rolling(window=self.bollinger_period).std()
        upper_band = sma_50 + (self.bollinger_std * std_50)
        
        # 200-period Moving Average
        ma_200 = prices_series.rolling(window=self.ma_period).mean()
        
        # Get current values
        current_close = weekly_close
        current_upper_band = upper_band.iloc[-1]
        current_ma_200 = ma_200.iloc[-1]
        
        # Skip if we don't have enough data
        if pd.isna(current_upper_band) or pd.isna(current_ma_200):
            return
        
        # Generate signals
        signal_type = None
        
        # Entry Rule: Close > Upper Bollinger Band (only if no position)
        if self.positions[symbol] == 'FLAT' and current_close > current_upper_band:
            signal_type = 'BUY'
            self.positions[symbol] = 'LONG'
            self.logger.info(f"[{self.strategy_name}] {symbol}: Weekly close {current_close:.2f} > "
                           f"Upper BB {current_upper_band:.2f}. BUY signal generated.")
        
        # Exit Rule: Close < 200 MA (only if we have a position)
        elif self.positions[symbol] == 'LONG' and current_close < current_ma_200:
            signal_type = 'SELL'
            self.positions[symbol] = 'FLAT'
            self.logger.info(f"[{self.strategy_name}] {symbol}: Weekly close {current_close:.2f} < "
                           f"200 MA {current_ma_200:.2f}. SELL signal generated.")
        
        # Send signal if generated
        if signal_type:
            signal = SignalEvent(
                instrument_token=symbol,
                strategy_id=self.strategy_name,
                signal_type=signal_type,
                quantity=self.trade_quantity,
                price=current_close,
                order_type="MARKET"
            )
            await self.event_engine.put(signal)

    async def handle_fill_event(self, event: FillEvent):
        """Handle fill events for the WeeklyBollingerStrategy."""
        symbol = event.instrument_token
        transaction_type = event.transaction_type
        
        self.logger.info(f"[{self.strategy_name}] Received fill: {transaction_type} {event.quantity} "
                        f"of {symbol} @ {event.price}")
        
        # Update position status based on fill
        if transaction_type == 'BUY':
            self.positions[symbol] = 'LONG'
        elif transaction_type == 'SELL':
            self.positions[symbol] = 'FLAT'

    def get_strategy_status(self, symbol: str = None):
        """Get current strategy status for monitoring."""
        if symbol:
            return {
                'symbol': symbol,
                'position': self.positions.get(symbol, 'FLAT'),
                'weekly_data_points': len(self.weekly_data.get(symbol, {}).get('prices', [])),
                'last_week': self.last_week.get(symbol)
            }
        else:
            return {
                'positions': self.positions,
                'weekly_data_counts': {s: len(data['prices']) for s, data in self.weekly_data.items()},
                'last_weeks': self.last_week
            }

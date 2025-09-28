# Weekly Bollinger Breakout Strategy

This contains the implementation and test files for the Weekly Bollinger Breakout with 200 MA Exit strategy.

### 1. `weekly_bollinger_breakout_strategy.py`
The standalone strategy implementation that follows the format of `strat2.py`. This is a pure strategy class that can be used independently.

**Key Features:**
- Entry: When weekly closing price breaks above upper Bollinger Band (50-period, 2 std dev)
- Exit: When weekly closing price falls below 200-period moving average
- State-based position management (one position at a time)
- Configurable parameters
- Performance metrics calculation

### 2. `weekly_bollinger_strategy.py`
The trading system integration version that inherits from `BaseStrategy`. This version is designed to work with your existing trading system.

**Key Features:**
- Inherits from `BaseStrategy` for trading system compatibility
- Handles real-time market events
- Aggregates tick data to weekly data
- Generates trading signals
- Position tracking and management

### 3. `test_weekly_strategy.py`
Full integration test that works with the trading system. Requires the trading system to be in the path.

**Usage:**
```bash
python test_weekly_strategy.py
```

### 4. `simple_weekly_test.py`
Standalone test that doesn't require the trading system. Tests the core strategy logic.

**Usage:**
```bash
python simple_weekly_test.py
```

### 5. `weekly_strategy_config.yaml`
Configuration file for the trading system integration.

**Usage:**
Copy this file to your trading system's config directory and update the main.py to use it.

## Strategy Logic

### Entry Conditions
- Weekly closing price > Upper Bollinger Band (50-period, 2 standard deviations)
- Only enters when no existing position

### Exit Conditions
- Weekly closing price < 200-period moving average
- Only exits when holding a long position

### Position Management
- One position at a time
- No pyramiding (adding to existing positions)
- State-based logic prevents duplicate signals

## Parameters

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `bollinger_period` | Period for Bollinger Bands calculation | 50 | 10-100 |
| `bollinger_std` | Standard deviation multiplier for Bollinger Bands | 2.0 | 1.0-3.0 |
| `ma_period` | Period for moving average exit signal | 200 | 50-500 |
| `position_size` | Position size multiplier | 1.0 | 0.1-10.0 |
| `trade_quantity` | Number of shares to trade (trading system version) | 100 | Any positive integer |

## Testing

### Quick Test (Standalone)
```bash
python simple_weekly_test.py
```

### Full Integration Test
```bash
python test_weekly_strategy.py
```

### Trading System Integration
1. Copy `weekly_bollinger_strategy.py` to your trading system's strategies directory
2. Copy `weekly_strategy_config.yaml` to your trading system's config directory
3. Update the config file path in main.py
4. Run the trading system

## Expected Output

The test scripts will show:
- Number of buy/sell signals generated
- Sample signal details with prices and indicator values
- Strategy parameters and description
- Performance metrics (in full integration test)

## Notes

- The strategy is designed for weekly timeframes
- It aggregates tick data to weekly OHLCV for analysis
- The standalone version can be used for backtesting
- The trading system version handles real-time data
- All parameters are configurable through the parameter schema

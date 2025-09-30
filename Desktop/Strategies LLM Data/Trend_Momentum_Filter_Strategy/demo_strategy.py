#!/usr/bin/env python3
"""
Demo script for Trend + Momentum Filter Strategy
Shows the strategy working with realistic parameters and data
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import strat2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trend_momentum_filter_strategy import TrendMomentumFilterStrategy

def create_realistic_trending_data():
    """Create realistic stock data with clear trends and momentum patterns"""
    np.random.seed(42)
    data = []
    
    # Create 400 days of data with different market phases
    for i in range(400):
        if i < 100:
            # Bear market - declining prices with low momentum
            price = 100 - i * 0.3 + np.random.normal(0, 1)
        elif i < 200:
            # Recovery phase - gradual increase with building momentum
            price = 70 + (i - 100) * 0.4 + np.random.normal(0, 1)
        elif i < 300:
            # Bull market - strong upward trend with high momentum
            price = 110 + (i - 200) * 0.6 + np.random.normal(0, 1)
        else:
            # Peak and decline - high volatility, mixed signals
            price = 170 - (i - 300) * 0.2 + np.random.normal(0, 2)
            
        data.append({
            'date': pd.Timestamp('2022-01-01') + pd.Timedelta(days=i),
            'open': price,
            'high': price + abs(np.random.normal(0, 0.5)),
            'low': price - abs(np.random.normal(0, 0.5)),
            'close': price,
            'volume': np.random.randint(1000, 10000)
        })
    
    return pd.DataFrame(data)

def test_strategy_indicators():
    """Test the strategy's indicator calculations"""
    print("Testing Trend + Momentum Filter Strategy Indicators...")
    
    # Create test data
    data = create_realistic_trending_data()
    print(f"Created test data with {len(data)} periods")
    
    # Initialize strategy
    strategy = TrendMomentumFilterStrategy()
    
    # Test RSI calculation
    rsi = strategy.calculate_rsi(data['close'], 14)
    print(f"RSI calculation test - Min: {rsi.min():.2f}, Max: {rsi.max():.2f}, Mean: {rsi.mean():.2f}")
    
    # Test Bollinger Bands calculation
    upper_bb, middle_bb, lower_bb = strategy.calculate_bollinger_bands(data['close'], 20, 2.0)
    print(f"Bollinger Bands test - Upper: {upper_bb.iloc[-1]:.2f}, Middle: {middle_bb.iloc[-1]:.2f}, Lower: {lower_bb.iloc[-1]:.2f}")
    
    # Test moving averages
    short_ma = data['close'].rolling(window=50).mean()
    long_ma = data['close'].rolling(window=200).mean()
    print(f"Moving Averages test - Short MA: {short_ma.iloc[-1]:.2f}, Long MA: {long_ma.iloc[-1]:.2f}")
    
    return True

def demo_strategy():
    """Demonstrate the Trend + Momentum Filter Strategy"""
    print("=" * 70)
    print("TREND + MOMENTUM FILTER STRATEGY DEMO")
    print("=" * 70)
    
    # Create realistic data
    data = create_realistic_trending_data()
    print(f"Created realistic stock data with {len(data)} periods")
    print(f"Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"Price range: ${data['close'].min():.2f} to ${data['close'].max():.2f}")
    
    # Test different parameter sets
    strategies = [
        {
            'name': 'Standard (50/200, RSI 40-70)',
            'params': {
                'short_ma_period': 50,
                'long_ma_period': 200,
                'rsi_period': 14,
                'rsi_lower': 40,
                'rsi_upper': 70,
                'rsi_exit': 75,
                'bb_period': 20,
                'bb_std': 2.0,
                'position_size': 1.0
            }
        },
        {
            'name': 'Aggressive (30/100, RSI 30-80)',
            'params': {
                'short_ma_period': 30,
                'long_ma_period': 100,
                'rsi_period': 14,
                'rsi_lower': 30,
                'rsi_upper': 80,
                'rsi_exit': 85,
                'bb_period': 20,
                'bb_std': 2.0,
                'position_size': 1.0
            }
        },
        {
            'name': 'Conservative (60/250, RSI 50-65)',
            'params': {
                'short_ma_period': 60,
                'long_ma_period': 250,
                'rsi_period': 14,
                'rsi_lower': 50,
                'rsi_upper': 65,
                'rsi_exit': 70,
                'bb_period': 20,
                'bb_std': 2.0,
                'position_size': 1.0
            }
        }
    ]
    
    for strategy_config in strategies:
        print(f"\n{'-' * 50}")
        print(f"Testing {strategy_config['name']} Strategy")
        print(f"{'-' * 50}")
        
        # Initialize strategy
        strategy = TrendMomentumFilterStrategy(strategy_config['params'])
        
        # Generate signals
        signals_df = strategy.generate_signals(data)
        signals = signals_df['Signal']
        
        # Analyze results
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        
        print(f"Parameters: {strategy_config['params']}")
        print(f"Buy signals: {buy_signals}")
        print(f"Sell signals: {sell_signals}")
        print(f"Total signals: {buy_signals + sell_signals}")
        
        # Show signal dates
        if buy_signals > 0:
            buy_dates = data[signals == 1]['date'].tolist()
            print(f"Buy dates: {[str(d)[:10] for d in buy_dates]}")
        
        if sell_signals > 0:
            sell_dates = data[signals == -1]['date'].tolist()
            print(f"Sell dates: {[str(d)[:10] for d in sell_dates]}")
        
        # Simulate trading
        if buy_signals > 0 or sell_signals > 0:
            print(f"\nTrading Simulation:")
            position = 0
            trades = []
            entry_price = 0
            
            for i, signal in enumerate(signals):
                if signal == 1 and position == 0:  # Buy
                    position = 1
                    entry_price = data.iloc[i]['close']
                    trades.append({
                        'date': data.iloc[i]['date'],
                        'action': 'BUY',
                        'price': entry_price
                    })
                    print(f"  BUY  at {data.iloc[i]['date'].strftime('%Y-%m-%d')} - Price: ${entry_price:.2f}")
                    
                elif signal == -1 and position == 1:  # Sell
                    position = 0
                    exit_price = data.iloc[i]['close']
                    trades.append({
                        'date': data.iloc[i]['date'],
                        'action': 'SELL',
                        'price': exit_price
                    })
                    print(f"  SELL at {data.iloc[i]['date'].strftime('%Y-%m-%d')} - Price: ${exit_price:.2f}")
            
            # Calculate performance
            if len(trades) >= 2:
                total_return = 0
                for i in range(0, len(trades), 2):
                    if i + 1 < len(trades):
                        buy_price = trades[i]['price']
                        sell_price = trades[i + 1]['price']
                        trade_return = (sell_price - buy_price) / buy_price * 100
                        total_return += trade_return
                        print(f"  Trade {i//2 + 1}: {trade_return:.2f}% return")
                
                print(f"  Total return: {total_return:.2f}%")
            
            # Calculate performance metrics
            metrics = strategy.get_performance_metrics(data)
            print(f"\nPerformance Metrics:")
            print(f"  Total Return: {metrics['total_return']:.2f}%")
            print(f"  Volatility: {metrics['volatility']:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.2f}%")
    
    # Test indicator calculations
    print(f"\n{'-' * 50}")
    print("INDICATOR CALCULATION TESTS")
    print(f"{'-' * 50}")
    test_strategy_indicators()
    
    # Show strategy description
    print(f"\n{'-' * 50}")
    print("STRATEGY DESCRIPTION")
    print(f"{'-' * 50}")
    strategy = TrendMomentumFilterStrategy()
    print(strategy.description())
    
    print(f"\n{'-' * 50}")
    print("PARAMETER SCHEMA")
    print(f"{'-' * 50}")
    schema = strategy.parameter_schema()
    for param, details in schema.items():
        print(f"{param}: {details}")
    
    print(f"\n✅ Demo completed successfully!")
    print("=" * 70)

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\nTesting Edge Cases...")
    
    # Test with insufficient data
    small_data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'date': pd.date_range('2023-01-01', periods=5)
    })
    
    strategy = TrendMomentumFilterStrategy()
    signals = strategy.generate_signals(small_data)
    print(f"Small data test - Signals generated: {len(signals)}")
    
    # Test with empty data
    empty_data = pd.DataFrame()
    empty_signals = strategy.generate_signals(empty_data)
    print(f"Empty data test - Signals generated: {len(empty_signals)}")
    
    # Test with missing columns
    try:
        bad_data = pd.DataFrame({'price': [100, 101, 102]})
        strategy.generate_signals(bad_data)
    except ValueError as e:
        print(f"Missing column test - Error caught: {e}")
    
    print("Edge case tests completed!")

if __name__ == "__main__":
    demo_strategy()
    test_edge_cases()


#!/usr/bin/env python3
"""
Demo script for Moving Average Crossover Strategy
Shows the strategy working with realistic parameters
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import strat2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moving_average_crossover_strategy import MovingAverageCrossoverStrategy

def create_realistic_data():
    """Create realistic stock data with clear trends"""
    np.random.seed(42)
    data = []
    
    # Create 500 days of data
    for i in range(500):
        if i < 100:
            # Bear market - declining prices
            price = 100 - i * 0.2 + np.random.normal(0, 1)
        elif i < 200:
            # Recovery phase - gradual increase
            price = 80 + (i - 100) * 0.3 + np.random.normal(0, 1)
        elif i < 300:
            # Bull market - strong upward trend
            price = 110 + (i - 200) * 0.5 + np.random.normal(0, 1)
        elif i < 400:
            # Peak and consolidation
            price = 160 + (i - 300) * 0.1 + np.random.normal(0, 1)
        else:
            # Decline phase
            price = 170 - (i - 400) * 0.3 + np.random.normal(0, 1)
            
        data.append({
            'date': pd.Timestamp('2022-01-01') + pd.Timedelta(days=i),
            'open': price,
            'high': price + abs(np.random.normal(0, 0.5)),
            'low': price - abs(np.random.normal(0, 0.5)),
            'close': price,
            'volume': np.random.randint(1000, 10000)
        })
    
    return pd.DataFrame(data)

def demo_strategy():
    """Demonstrate the Moving Average Crossover Strategy"""
    print("=" * 60)
    print("MOVING AVERAGE CROSSOVER STRATEGY DEMO")
    print("=" * 60)
    
    # Create realistic data
    data = create_realistic_data()
    print(f"Created realistic stock data with {len(data)} periods")
    print(f"Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"Price range: ${data['close'].min():.2f} to ${data['close'].max():.2f}")
    
    # Test with different parameter sets
    strategies = [
        {
            'name': 'Standard (50/200)',
            'params': {'short_ma_period': 50, 'long_ma_period': 200, 'position_size': 1.0}
        },
        {
            'name': 'Fast (20/50)',
            'params': {'short_ma_period': 20, 'long_ma_period': 50, 'position_size': 1.0}
        },
        {
            'name': 'Medium (30/100)',
            'params': {'short_ma_period': 30, 'long_ma_period': 100, 'position_size': 1.0}
        }
    ]
    
    for strategy_config in strategies:
        print(f"\n{'-' * 40}")
        print(f"Testing {strategy_config['name']} Strategy")
        print(f"{'-' * 40}")
        
        # Initialize strategy
        strategy = MovingAverageCrossoverStrategy(strategy_config['params'])
        
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
            
            for i, signal in enumerate(signals):
                if signal == 1 and position == 0:  # Buy
                    position = 1
                    trades.append({
                        'date': data.iloc[i]['date'],
                        'action': 'BUY',
                        'price': data.iloc[i]['close']
                    })
                    print(f"  BUY  at {data.iloc[i]['date'].strftime('%Y-%m-%d')} - Price: ${data.iloc[i]['close']:.2f}")
                    
                elif signal == -1 and position == 1:  # Sell
                    position = 0
                    trades.append({
                        'date': data.iloc[i]['date'],
                        'action': 'SELL',
                        'price': data.iloc[i]['close']
                    })
                    print(f"  SELL at {data.iloc[i]['date'].strftime('%Y-%m-%d')} - Price: ${data.iloc[i]['close']:.2f}")
            
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
    
    # Show strategy description
    print(f"\n{'-' * 40}")
    print("STRATEGY DESCRIPTION")
    print(f"{'-' * 40}")
    strategy = MovingAverageCrossoverStrategy()
    print(strategy.description())
    
    print(f"\n{'-' * 40}")
    print("PARAMETER SCHEMA")
    print(f"{'-' * 40}")
    schema = strategy.parameter_schema()
    for param, details in schema.items():
        print(f"{param}: {details}")
    
    print(f"\n✅ Demo completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    demo_strategy()



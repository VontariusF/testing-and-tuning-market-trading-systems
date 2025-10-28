#!/usr/bin/env python3
"""
Run Experiment Tool
Executes backtest or training runs for trading strategies
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import time
import uuid


def load_request(request_path: str) -> Dict[str, Any]:
    """Load JSON request from inbox"""
    with open(request_path, 'r') as f:
        return json.load(f)


def get_run_directories(request_path: str) -> tuple:
    """Derive run directories from request file path"""
    request_file = Path(request_path)
    run_dir = request_file.parent.parent  # inbox/../ = run_dir
    
    inbox_dir = run_dir / "inbox"
    outbox_dir = run_dir / "outbox" 
    state_dir = run_dir / "state"
    results_dir = run_dir / "results"
    
    return inbox_dir, outbox_dir, state_dir, results_dir


def run_strategy_backtest(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run strategy backtest using existing StratVal system"""
    try:
        # Import configuration and StratVal components
        sys.path.append(str(Path(__file__).parent.parent))
        sys.path.append(str(Path(__file__).parent.parent / "config"))
        from config.config_manager import get_data_config, get_timeout_config
        from stratval.pipeline.orchestrator import ValidationOrchestrator
        
        orchestrator = ValidationOrchestrator()
        
        # Generate strategy description if not provided
        strategy_desc = params.get('strategy', 'moving average crossover strategy')
        if not strategy_desc.lower().startswith(('rsi', 'macd', 'bollinger', 'volume')):
            # Generate default strategy based on parameters
            fast = params.get('parameters', {}).get('fast_period', 10)
            slow = params.get('parameters', {}).get('slow_period', 30)
            strategy_desc = f"moving average crossover strategy with {fast} and {slow} periods"
        
        # Create temporary strategy file
        strategy_dir = Path("temp_strategies")
        strategy_dir.mkdir(exist_ok=True)
        strategy_file = strategy_dir / f"strategy_{params.get('request_id', 'temp')}.cpp"
        
        # Generate strategy code
        from stratval.generator.strategy_generator import StrategyGenerator
        generator = StrategyGenerator()
        strategy_code = generator.from_natural_language(strategy_desc)
        
        with open(strategy_file, 'w') as f:
            f.write(strategy_code)
        
        # Extract market data parameters
        market_data = params.get('market_data', {})
        pair = market_data.get('pair', 'BTC/USDT')
        timeframe = market_data.get('timeframe', '1h')
        start_date = market_data.get('start_date', '2020-01-01')
        end_date = market_data.get('end_date', '2023-12-31')
        
        # Get configuration for timeout and data source
        timeout_config = get_timeout_config('standard')
        data_config = get_data_config()
        
        # Run validation with configuration
        results = orchestrator.validate(
            strategy_path=str(strategy_file),
            pair=pair,
            timeframe=timeframe,
            mode='standard',
            output_dir='temp_results',
            timeouts=timeout_config,
            data_source=data_config
        )
        
        # Clean up temporary files
        if strategy_file.exists():
            strategy_file.unlink()
        
        return {
            "status": "OK",
            "strategy": strategy_desc,
            "results": results,
            "artifacts": {
                "log_file": f"temp_results/validation_{params.get('request_id')}.log"
            }
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "strategy": params.get('strategy', 'unknown')
        }


def save_response(request_id: str, response: Dict[str, Any], request_path: str) -> str:
    """Save response to outbox"""
    _, outbox_dir, _, _ = get_run_directories(request_path)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    response_file = outbox_dir / f"{request_id}.json"
    
    response_with_meta = {
        "request_id": request_id,
        "timestamp": time.time(),
        **response
    }
    
    with open(response_file, 'w') as f:
        json.dump(response_with_meta, f, indent=2)
    
    return str(response_file)


def main():
    """Main tool execution"""
    parser = argparse.ArgumentParser(description="Run experiment tool")
    parser.add_argument("request_file", help="Path to JSON request file")
    
    args = parser.parse_args()
    
    try:
        # Load request
        request = load_request(args.request_file)
        request_id = request.get('request_id', str(uuid.uuid4()))
        params = request.get('params', {})
        
        print(f"Running experiment: {request_id}")
        print(f"Strategy: {params.get('strategy', 'unknown')}")
        
        # Execute experiment
        result = run_strategy_backtest(params)
        
        # Save response
        response_file = save_response(request_id, result, args.request_file)
        print(f"Results saved to: {response_file}")
        
        # Return 0 for success, 1 for error
        return 0 if result.get('status') == 'OK' else 1
        
    except Exception as e:
        print(f"Error running experiment: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

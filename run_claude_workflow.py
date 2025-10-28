#!/usr/bin/env python3
"""
Claude Code Trading System Workflow Runner
Executes the complete agentic trading system workflow
"""

import json
import sys
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List
import argparse
import subprocess
import threading
from tools.file_watcher import ToolRequestHandler, ensure_directories


class ClaudeWorkflowRunner:
    """Manages the complete Claude Code trading system workflow"""
    
    def __init__(self, run_dir: str = "current", base_path: str = "runs"):
        self.base_path = Path(base_path) / run_dir
        self.run_id = run_dir
        
        # Setup directories
        self.inbox_dir, self.outbox_dir = ensure_directories(self.base_path)
        self.state_dir = self.base_path / "state"
        self.results_dir = self.base_path / "results"
        
        self.state_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize file watcher
        self.file_watcher = None
        self.processing_thread = None
        
    def start_file_watcher(self):
        """Start the file watcher system"""
        print("🚀 Starting file watcher...")
        
        # Create event handler
        event_handler = ToolRequestHandler(self.inbox_dir, self.outbox_dir)
        
        # Start processing thread
        self.processing_thread = event_handler.start_processing_thread()
        
        # Start file system monitoring in a separate thread
        from watchdog.observers import Observer
        observer = Observer()
        observer.schedule(event_handler, str(self.inbox_dir), recursive=False)
        observer.start()
        
        self.file_watcher = observer
        
        # Wait a moment for watcher to initialize
        time.sleep(2)
        
        return observer, event_handler
    
    def stop_file_watcher(self):
        """Stop the file watcher system"""
        if self.file_watcher:
            self.file_watcher.stop()
            self.file_watcher.join()
            print("👋 File watcher stopped")
    
    def create_tool_request(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Create a tool request file"""
        request_id = f"{tool_name}_{uuid.uuid4().hex[:8]}"
        
        request_data = {
            "tool": tool_name,
            "request_id": request_id,
            "params": params
        }
        
        request_file = self.inbox_dir / f"{request_id}.json"
        
        with open(request_file, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        print(f"📝 Created {tool_name} request: {request_file.name}")
        return str(request_file)
    
    def update_digest(self, content: str):
        """Update the shared digest file"""
        digest_file = self.state_dir / "digest.md"
        
        # Read existing content
        existing_content = ""
        if digest_file.exists():
            with open(digest_file, 'r') as f:
                existing_content = f.read()
        
        # Append new content
        with open(digest_file, 'a') as f:
            f.write(f"\n{content}")
    
    def wait_for_response(self, request_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for tool response"""
        response_file = self.outbox_dir / f"{request_id}.json"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if response_file.exists():
                with open(response_file, 'r') as f:
                    return json.load(f)
            time.sleep(2)
        
        raise TimeoutError(f"Response timeout for {request_id}")
    
    def run_workflow(self, objective: str, market_data: Dict[str, Any], 
                    experiment_count: int = 5) -> Dict[str, Any]:
        """Run the complete Claude Code workflow"""
        
        print("🎯 Starting Claude Code Trading System Workflow")
        print(f"📊 Objective: {objective}")
        print(f"📈 Market Data: {market_data}")
        print(f"🔬 Experiment Count: {experiment_count}")
        print()
        
        # Start file watcher
        observer, event_handler = self.start_file_watcher()
        
        try:
            # Initialize workflow
            self.update_digest("## Workflow Started")
            self.update_digest(f"- Objective: {objective}")
            self.update_digest(f"- Market Data: {market_data}")
            self.update_digest(f"- Experiment Count: {experiment_count}")
            
            # Phase 1: Experiment Planning
            print("📋 Phase 1: Planning Experiments...")
            experiment_requests = self.plan_experiments(market_data, experiment_count)
            
            # Wait for experiments to complete
            experiment_results = []
            for request_id in [req.split('/')[-1].replace('.json', '') for req in experiment_requests]:
                print(f"⏳ Waiting for {request_id}...")
                response = self.wait_for_response(request_id)
                if response.get('status') == 'OK':
                    experiment_results.append(request_id)
                else:
                    print(f"❌ Experiment {request_id} failed: {response.get('error')}")
            
            print(f"✅ Completed {len(experiment_results)} experiments")
            self.update_digest(f"## Experiment Results")
            self.update_digest(f"- Completed {len(experiment_results)}/{len(experiment_requests)} experiments")
            
            # Phase 2: Feature Evaluation  
            print("\n🔍 Phase 2: Evaluating Features...")
            feature_request = self.evaluate_features(experiment_results)
            feature_request_id = feature_request.split('/')[-1].replace('.json', '')
            
            feature_response = self.wait_for_response(feature_request_id)
            if feature_response.get('status') == 'OK':
                print("✅ Feature evaluation completed")
                self.update_digest("## Feature Analysis Completed")
                self.update_digest(f"- Key findings: {len(feature_response.get('recommendations', []))} recommendations")
            else:
                print(f"❌ Feature evaluation failed: {feature_response.get('error')}")
                return {"status": "ERROR", "phase": "feature_evaluation"}
            
            # Phase 3: Strategy Scoring
            print("\n📊 Phase 3: Scoring Strategies...")
            scoring_request = self.score_strategies(experiment_results)
            scoring_request_id = scoring_request.split('/')[-1].replace('.json', '')
            
            scoring_response = self.wait_for_response(scoring_request_id)
            if scoring_response.get('status') == 'OK':
                print("✅ Strategy scoring completed")
                self.update_digest("## Strategy Scoring Completed")
                rankings = scoring_response.get('rankings', [])
                if rankings:
                    top_strategy = rankings[0]
                    self.update_digest(f"- Top strategy: {top_strategy.get('strategy_name')} (Score: {top_strategy.get('composite_score', 0):.3f})")
            else:
                print(f"❌ Strategy scoring failed: {scoring_response.get('error')}")
                return {"status": "ERROR", "phase": "strategy_scoring"}
            
            # Phase 4: Final Selection and Reporting
            print("\n📋 Phase 4: Final Selection and Reporting...")
            top_strategy = rankings[0].get('strategy_name', 'Unknown Strategy') if rankings else 'Unknown Strategy'
            report_request = self.generate_report(top_strategy, [scoring_request_id])
            report_request_id = report_request.split('/')[-1].replace('.json', '')
            
            report_response = self.wait_for_response(report_request_id)
            if report_response.get('status') == 'OK':
                print("✅ Report generation completed")
                self.update_digest("## Final Selection Completed")
                self.update_digest(f"- Selected strategy: {top_strategy}")
                self.update_digest(f"- Report: {report_response.get('report_file')}")
            else:
                print(f"❌ Report generation failed: {report_response.get('error')}")
                return {"status": "ERROR", "phase": "report_generation"}
            
            # Workflow completion
            print("\n🎉 Claude Code Workflow Completed Successfully!")
            self.update_digest("## Workflow Completed")
            self.update_digest(f"- Final strategy: {top_strategy}")
            self.update_digest(f"- Report generated: {report_response.get('report_file')}")
            
            return {
                "status": "OK",
                "selected_strategy": top_strategy,
                "experiment_count": len(experiment_results),
                "report_file": report_response.get('report_file'),
                "run_directory": str(self.base_path)
            }
            
        except Exception as e:
            print(f"💥 Workflow failed: {e}")
            self.update_digest(f"## Workflow Failed")
            self.update_digest(f"- Error: {str(e)}")
            return {"status": "ERROR", "error": str(e)}
            
        finally:
            self.stop_file_watcher()
    
    def plan_experiments(self, market_data: Dict[str, Any], count: int) -> List[str]:
        """Plan and create experiment requests"""
        requests = []
        
        # Strategy templates with different parameterizations
        strategies = [
            {
                "strategy": "RSI oversold bounce strategy",
                "strategy_type": "rsi",
                "parameters": {"rsi_period": 14, "oversold_threshold": 30, "overbought_threshold": 70}
            },
            {
                "strategy": "Moving average crossover strategy", 
                "strategy_type": "moving_average",
                "parameters": {"fast_period": 10, "slow_period": 30}
            },
            {
                "strategy": "Bollinger band mean reversion strategy",
                "strategy_type": "bollinger", 
                "parameters": {"period": 20, "deviation": 2.0}
            },
            {
                "strategy": "MACD momentum strategy",
                "strategy_type": "macd",
                "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9}
            },
            {
                "strategy": "Volume price analysis strategy",
                "strategy_type": "volume",
                "parameters": {"volume_period": 20, "price_period": 10}
            }
        ]
        
        for i in range(min(count, len(strategies))):
            strategy_config = strategies[i % len(strategies)]
            
            params = {
                "strategy": strategy_config["strategy"],
                "strategy_type": strategy_config["strategy_type"],
                "market_data": market_data,
                "parameters": strategy_config["parameters"],
                "seed": 42 + i  # Reproducible seeds
            }
            
            request_file = self.create_tool_request("run_experiment", params)
            requests.append(request_file)
        
        return requests
    
    def evaluate_features(self, experiment_results: List[str]) -> str:
        """Create feature evaluation request"""
        params = {
            "experiment_results": [f"outbox/{result}.json" for result in experiment_results],
            "feature_types": ["performance", "risk", "market_regime"],
            "analysis_depth": "standard"
        }
        
        return self.create_tool_request("evaluate_features", params)
    
    def score_strategies(self, experiment_results: List[str]) -> str:
        """Create strategy scoring request"""
        params = {
            "strategy_results": [f"outbox/{result}.json" for result in experiment_results],
            "scoring_methodology": {
                "weights": {
                    "sharpe_ratio": 0.3,
                    "max_drawdown": 0.2,
                    "win_rate": 0.2,
                    "profit_factor": 0.15,
                    "calmar_ratio": 0.15
                },
                "risk_adjustment": True,
                "regime_analysis": True
            },
            "benchmark_comparison": True
        }
        
        return self.create_tool_request("score_strategy", params)
    
    def generate_report(self, selected_strategy: str, scoring_results: List[str]) -> str:
        """Create report generation request"""
        params = {
            "selected_strategy": selected_strategy,
            "strategy_rankings": [f"outbox/{result}.json" for result in scoring_results],
            "report_format": "html",
            "include_sections": [
                "executive_summary",
                "performance_analysis",
                "risk_assessment", 
                "regime_analysis",
                "recommendations"
            ],
            "output_path": "trading_strategy_report.html"
        }
        
        return self.create_tool_request("generate_report", params)


def main():
    """Main workflow runner"""
    parser = argparse.ArgumentParser(description="Claude Code Trading System Workflow Runner")
    parser.add_argument("--objective", 
                       default="Find profitable trading strategies for cryptocurrency market",
                       help="Trading system objective")
    parser.add_argument("--pair", default="BTC/USDT", help="Trading pair")
    parser.add_argument("--timeframe", default="1h", help="Timeframe")
    parser.add_argument("--start-date", default="2020-01-01", help="Start date")
    parser.add_argument("--end-date", default="2023-12-31", help="End date") 
    parser.add_argument("--experiments", type=int, default=5, help="Number of experiments")
    parser.add_argument("--run-dir", default="current", help="Run directory name")
    
    args = parser.parse_args()
    
    # Market data configuration
    market_data = {
        "pair": args.pair,
        "timeframe": args.timeframe,
        "start_date": args.start_date,
        "end_date": args.end_date
    }
    
    # Create and run workflow
    runner = ClaudeWorkflowRunner(run_dir=args.run_dir)
    
    try:
        results = runner.run_workflow(
            objective=args.objective,
            market_data=market_data,
            experiment_count=args.experiments
        )
        
        if results.get("status") == "OK":
            print(f"\n🎯 Workflow Results:")
            print(f"Selected Strategy: {results.get('selected_strategy')}")
            print(f"Experiments Completed: {results.get('experiment_count')}")
            print(f"Report: {results.get('report_file')}")
            print(f"Run Directory: {results.get('run_directory')}")
            return 0
        else:
            print(f"\n❌ Workflow Failed: {results.get('error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Workflow interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
File Watcher System
Monitors inbox/ directory and executes corresponding tools
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import threading
import queue
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ToolRequestHandler(FileSystemEventHandler):
    """Handles file system events for tool requests"""
    
    def __init__(self, inbox_dir: Path, outbox_dir: Path):
        self.inbox_dir = inbox_dir
        self.outbox_dir = outbox_dir
        self.processed_files = set()
        self.processing_queue = queue.Queue()
        
        # Map tools to their executable scripts
        self.tool_mapping = {
            'run_experiment': 'run_experiment.py',
            'evaluate_features': 'evaluate_features.py', 
            'score_strategy': 'score_strategy.py',
            'generate_report': 'generate_report.py'
        }
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.parent == self.inbox_dir and file_path.suffix == '.json':
            if file_path not in self.processed_files:
                self.processed_files.add(file_path)
                self.processing_queue.put(file_path)
    
    def process_request(self, request_file: Path):
        """Process a tool request"""
        try:
            print(f"📥 Processing request: {request_file.name}")
            
            # Load request
            with open(request_file, 'r') as f:
                request_data = json.load(f)
            
            tool_name = request_data.get('tool')
            if not tool_name:
                print(f"❌ No tool specified in {request_file.name}")
                return
            
            # Get tool executable
            tool_script = self.tool_mapping.get(tool_name)
            if not tool_script:
                print(f"❌ Unknown tool: {tool_name}")
                return
            
            # Execute tool
            tool_path = Path(__file__).parent / tool_script
            if not tool_path.exists():
                print(f"❌ Tool script not found: {tool_path}")
                return
            
            print(f"🔧 Executing {tool_name} with {request_file}")
            
            result = subprocess.run([
                sys.executable, str(tool_path), str(request_file)
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if result.returncode == 0:
                print(f"✅ {tool_name} completed successfully")
                print(f"Output: {result.stdout}")
            else:
                print(f"❌ {tool_name} failed with code {result.returncode}")
                print(f"Error: {result.stderr}")
            
            # Move processed request to archive
            archive_dir = self.inbox_dir / "processed"
            archive_dir.mkdir(exist_ok=True)
            request_file.rename(archive_dir / request_file.name)
            
        except Exception as e:
            print(f"💥 Error processing {request_file}: {e}")
    
    def run_event_loop(self):
        """Run the main event processing loop"""
        print("🚀 File watcher started")
        print(f"📁 Monitoring inbox: {self.inbox_dir}")
        print(f"📤 Output directory: {self.outbox_dir}")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                try:
                    # Get next file to process (with timeout)
                    request_file = self.processing_queue.get(timeout=1.0)
                    self.process_request(request_file)
                    self.processing_queue.task_done()
                except queue.Empty:
                    continue
                    
        except KeyboardInterrupt:
            print("\n👋 File watcher stopped")
    
    def start_processing_thread(self):
        """Start the processing thread"""
        processing_thread = threading.Thread(target=self.run_event_loop)
        processing_thread.daemon = True
        processing_thread.start()
        return processing_thread


def ensure_directories(base_dir: Path):
    """Ensure required directories exist"""
    inbox_dir = base_dir / "inbox"
    outbox_dir = base_dir / "outbox"
    
    inbox_dir.mkdir(parents=True, exist_ok=True)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    return inbox_dir, outbox_dir


def main():
    """Main file watcher execution"""
    parser = argparse.ArgumentParser(description="File watcher for tool execution")
    parser.add_argument("--run-dir", default="current", 
                       help="Run directory (default: current)")
    parser.add_argument("--base-path", default="runs",
                       help="Base path for runs (default: runs)")
    
    args = parser.parse_args()
    
    # Setup directories
    base_path = Path(args.base_path) / args.run_dir
    inbox_dir, outbox_dir = ensure_directories(base_path)
    
    # Create file watcher
    event_handler = ToolRequestHandler(inbox_dir, outbox_dir)
    
    # Setup observer
    observer = Observer()
    observer.schedule(event_handler, str(inbox_dir), recursive=False)
    
    # Start processing thread
    processing_thread = event_handler.start_processing_thread()
    
    # Start file system observer
    observer.start()
    
    try:
        # Keep main thread alive
        while processing_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
    print("File watcher shutdown complete")


if __name__ == "__main__":
    main()

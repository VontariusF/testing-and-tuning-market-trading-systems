"""
JSON report generator for validation results
"""

import json
import time
from pathlib import Path
from typing import Dict, Any


class JSONReporter:
    """Generate JSON reports for programmatic access"""

    def generate(self, results: Dict[str, Any], output_dir: str = './reports') -> str:
        """Generate JSON report

        Args:
            results: Complete validation results
            output_dir: Output directory

        Returns:
            Path to generated JSON file
        """
        # Ensure results are JSON serializable
        json_results = self._make_json_serializable(results)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = int(time.time())
        filename = f"validation_results_{timestamp}.json"
        output_file = output_path / filename

        # Write JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)

        return str(output_file)

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            # Convert to string for unknown types
            return str(obj)

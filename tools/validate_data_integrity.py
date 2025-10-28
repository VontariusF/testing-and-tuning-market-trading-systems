#!/usr/bin/env python3
"""
Data Integrity Validation Tool for Market Trading System

This script performs comprehensive validation on OHLCV data files to detect:
1. Chronological order violations (lookahead bias)
2. Data gaps and anomalies
3. OHLC relationship violations
4. Extreme price movements
5. Data quality issues

Part of Phase 1: Data Integrity Checks in the lookahead bias prevention plan.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import re

def parse_date(date_int):
    """Parse YYYYMMDD integer to datetime object"""
    if isinstance(date_int, str):
        date_int = int(date_int)
    year = date_int // 10000
    month = (date_int % 10000) // 100
    day = date_int % 100
    try:
        return datetime(year, month, day)
    except ValueError:
        return None

def load_ohlc_data(filepath):
    """Load OHLC data from text file"""
    data = []
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 5:
                    print(f"⚠️ Line {line_num}: Insufficient data fields ({len(parts)})")
                    continue

                try:
                    date = int(parts[0])
                    open_price = float(parts[1])
                    high = float(parts[2])
                    low = float(parts[3])
                    close = float(parts[4])
                    volume = float(parts[5]) if len(parts) > 5 else 0.0

                    data.append({
                        'line': line_num,
                        'date': date,
                        'datetime': parse_date(date),
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    })
                except ValueError as e:
                    print(f"⚠️ Line {line_num}: Invalid data format - {e}")
                    continue

    except FileNotFoundError:
        print(f"❌ Error: File not found - {filepath}")
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

    return data

def validate_chronological_order(data):
    """Validate that data is in strict chronological order"""
    print("\n🔍 VALIDATING CHRONOLOGICAL ORDER")
    print("=" * 50)

    violations = []
    total_checks = 0

    for i in range(1, len(data)):
        current = data[i]
        previous = data[i-1]
        total_checks += 1

        if current['date'] <= previous['date']:
            violations.append({
                'index': i,
                'line': current['line'],
                'current_date': current['date'],
                'previous_date': previous['date'],
                'description': f"Date {current['date']} <= {previous['date']}"
            })

    if violations:
        print(f"❌ CHRONOLOGICAL VIOLATIONS FOUND: {len(violations)}")
        print("   This indicates potential LOOKAHEAD BIAS!")
        print("   Data must be sorted in ascending chronological order.\n")

        # Show first 5 violations
        for v in violations[:5]:
            print(f"   Line {v['line']}: {v['description']}")

        if len(violations) > 5:
            print(f"   ... and {len(violations) - 5} more violations")
        print()
        return False
    else:
        print(f"✅ Chronological Order: {total_checks} checks passed")
        return True

def validate_data_integrity(data):
    """Validate data integrity and quality"""
    print("\n🔍 VALIDATING DATA INTEGRITY")
    print("=" * 50)

    issues = {'missing_dates': 0, 'negative_prices': 0, 'extreme_prices': 0,
              'zero_volumes': 0, 'invalid_structure': 0}
    warnings = []

    max_reasonable_price = 1e8  # 100M
    min_reasonable_price = 0.000001  # $1 per billion shares

    for item in data:
        # Check for missing or invalid dates
        if item['date'] == 0 or not item['datetime']:
            issues['missing_dates'] += 1
            warnings.append(f"Line {item['line']}: Invalid date {item['date']}")

        # Check for negative or zero prices
        for field in ['open', 'high', 'low', 'close']:
            price = item[field]
            if price <= 0:
                issues['negative_prices'] += 1
                warnings.append(f"Line {item['line']}: {field.upper()} price is {price}")
            elif price > max_reasonable_price:
                issues['extreme_prices'] += 1
                warnings.append(f"Line {item['line']}: Extreme {field.upper()} price ${price:,.2f}")
            elif price < min_reasonable_price:
                issues['extreme_prices'] += 1
                warnings.append(f"Line {item['line']}: Extremely low {field.upper()} price ${price:.10f}")

        # Check volume
        if item['volume'] < 0:
            issues['zero_volumes'] += 1
            warnings.append(f"Line {item['line']}: Negative volume {item['volume']}")

    total_issues = sum(issues.values())

    if total_issues == 0:
        print("✅ Data Integrity: All checks passed")
        return True
    else:
        print(f"⚠️ Data Integrity Issues Found: {total_issues}")
        for category, count in issues.items():
            if count > 0:
                print(f"   - {category.replace('_', ' ').title()}: {count}")
        print()

        # Show first 10 warnings
        if warnings:
            print("   Sample Issues:")
            for warning in warnings[:10]:
                print(f"     {warning}")
            if len(warnings) > 10:
                print(f"     ... and {len(warnings) - 10} more warnings")

        return total_issues == 0

def validate_ohlc_relationships(data):
    """Validate OHLC price relationships"""
    print("\n🔍 VALIDATING OHLC RELATIONSHIPS")
    print("=" * 50)

    violations = 0
    volatility_warnings = 0
    issues = []

    for item in data:
        # Basic OHLC logic checks
        if item['high'] < item['open'] or item['high'] < item['close'] or item['high'] < item['low']:
            violations += 1
            issues.append(f"Line {item['line']}: HIGH price (${item['high']:.6f}) too low")

        if item['low'] > item['open'] or item['low'] > item['close'] or item['low'] > item['high']:
            violations += 1
            issues.append(f"Line {item['line']}: LOW price (${item['low']:.6f}) too high")

        # Check for extreme intraday volatility
        try:
            open_to_close_change = abs(item['open'] - item['close']) / item['open']
            high_low_range = (item['high'] - item['low']) / item['low']

            if open_to_close_change > 0.5:  # >50% intraday change
                volatility_warnings += 1
                issues.append(f"Line {item['line']}: Extreme intraday change ({open_to_close_change:.1%})")

            if high_low_range > 1.0:  # >100% high-low range
                volatility_warnings += 1
                issues.append(f"Line {item['line']}: Extreme volatility range ({high_low_range:.1%})")
        except ZeroDivisionError:
            violations += 1
            issues.append(f"Line {item['line']}: Zero price division error")

    if violations == 0 and volatility_warnings == 0:
        print("✅ OHLC Relationships: All checks passed")
        return True
    else:
        print(f"⚠️ OHLC Issues Found: {violations + volatility_warnings}")
        if violations > 0:
            print(f"   - Logic Violations: {violations}")
        if volatility_warnings > 0:
            print(f"   - Volatility Warnings: {volatility_warnings}")
        print()

        # Show sample issues
        if issues:
            print("   Sample Issues:")
            for issue in issues[:10]:
                print(f"     {issue}")
            if len(issues) > 10:
                print(f"     ... and {len(issues) - 10} more issues")

        return False

def validate_date_gaps(data):
    """Validate for reasonable date gaps"""
    print("\n🔍 VALIDATING DATE CONTINUITY")
    print("=" * 50)

    gaps = []
    assumed_timeframe = None

    for i in range(1, len(data)):
        current = data[i]
        previous = data[i-1]

        # Try to infer timeframe from date differences
        if current['datetime'] and previous['datetime']:
            delta = current['datetime'] - previous['datetime']

            # Assume daily data for gap detection
            if delta.days > 5:  # Allow for weekends/5+ days
                gaps.append({
                    'index': i,
                    'gap_days': delta.days,
                    'from_date': previous['date'],
                    'to_date': current['date']
                })

    if not gaps:
        print("✅ Date Continuity: No significant gaps detected")
        return True
    else:
        print(f"⚠️ Date Gaps Found: {len(gaps)} gaps longer than 5 days")

        # Show largest gaps
        sorted_gaps = sorted(gaps, key=lambda x: x['gap_days'], reverse=True)
        print("   Largest Gaps:")
        for gap in sorted_gaps[:5]:
            print(f"     {gap['from_date']} -> {gap['to_date']}: {gap['gap_days']} days")

        return len(gaps) == 0

def generate_validation_report(data, filepath, validation_results):
    """Generate a comprehensive validation report"""
    print(f"\n📊 VALIDATION REPORT: {Path(filepath).name}")
    print("=" * 60)

    filename = Path(filepath).name
    total_bars = len(data)
    date_range = "N/A"

    if data and data[0]['datetime'] and data[-1]['datetime']:
        date_range = f"{data[0]['date']} to {data[-1]['date']}"

    print("📁 File Information:")
    print(f"   Filename: {filename}")
    print(f"   Total Bars: {total_bars:,}")
    print(f"   Date Range: {date_range}")
    print()

    # Overall status
    all_passed = all(validation_results.values())
    status = "✅ PASSED" if all_passed else "❌ FAILED"

    print(f"🎯 OVERALL STATUS: {status}")
    print()

    # Individual test results
    test_names = {
        'chronological': 'Chronological Order',
        'integrity': 'Data Integrity',
        'ohlc': 'OHLC Relationships',
        'gaps': 'Date Continuity'
    }

    for key, result in validation_results.items():
        status_icon = "✅" if result else "❌"
        print(f"   {status_icon} {test_names.get(key, key)}")

    # Summary statistics
    if data:
        prices = [item['close'] for item in data if item['close'] > 0]
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)

            print("\n💰 Price Statistics:")
            print(f"   Price Range: ${min_price:.6f} - ${max_price:.6f}")
            print(f"   Average Price: ${avg_price:.6f}")
            print(f"   Total Volume: {sum(item['volume'] for item in data if 'volume' in item):,.0f}")
    print("=" * 60)
    print()

    return all_passed

def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description="Validate OHLC data integrity and check for lookahead bias",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validate_data_integrity.py market_data.txt
  python3 validate_data_integrity.py data/sample_ohlc.txt --verbose
  python3 validate_data_integrity.py binance_BTC_USDT_1h.txt
        """
    )

    parser.add_argument('filepath', help='Path to OHLC data file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed validation output')
    parser.add_argument('--strict', action='store_true',
                       help='Treat warnings as errors')

    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"❌ Error: File not found - {args.filepath}")
        return 1

    print("🔬 DATA INTEGRITY VALIDATION TOOL")
    print("=" * 60)
    print(f"Target File: {args.filepath}")
    print("=" * 60)

    # Load data
    data = load_ohlc_data(args.filepath)
    if data is None:
        return 1

    if not data:
        print("❌ Error: No valid data found in file")
        return 1

    print(f"📊 Loaded: {len(data):,} bars for validation")

    # Run validation checks
    validation_results = {}

    # 1. Chronological order (CRITICAL for lookahead bias prevention)
    validation_results['chronological'] = validate_chronological_order(data)

    # 2. Data integrity
    validation_results['integrity'] = validate_data_integrity(data)

    # 3. OHLC relationships
    validation_results['ohlc'] = validate_ohlc_relationships(data)

    # 4. Date continuity
    validation_results['gaps'] = validate_date_gaps(data)

    # Generate summary report
    all_passed = generate_validation_report(data, args.filepath, validation_results)

    # Exit with appropriate code
    if all_passed:
        print("🎉 VALIDATION COMPLETE: File is safe for strategy testing")
        return 0
    else:
        print("⚠️ VALIDATION COMPLETE: Issues found - review before testing")
        print("   Use option --verbose for detailed output")
        return 1

if __name__ == '__main__':
    sys.exit(main())

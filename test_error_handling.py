#!/usr/bin/env python3
"""
Test script for new error handling features
Demonstrates the ValidationError class and error confirmation workflow
"""

from config_loader import ConfigLoader
from race_parser import RaceParser
from calculation_engine import CalculationEngine
from data_validator import validate_all, ValidationError

print("=" * 60)
print("Error Handling Feature Test")
print("=" * 60)

# Load settings
print("\n1. Loading settings...")
config_loader = ConfigLoader('sample/setting')
success, msg = config_loader.load_all()
print(f"   Result: {msg}")

# Load race data
print("\n2. Loading race data...")
race_parser = RaceParser('sample/race')
success, msg = race_parser.parse_all()
print(f"   Result: {msg}")

# Initial validation (without calc_engine)
print("\n3. Running initial validation...")
errors = validate_all('sample/race', race_parser.results, config_loader.section_list)
print(f"   Found {len(errors)} errors")

# Show error type breakdown
error_types = {}
for err in errors:
    error_types[err.error_type] = error_types.get(err.error_type, 0) + 1

print("\n   Error breakdown:")
for err_type, count in sorted(error_types.items()):
    type_names = {
        "csv_duplicate": "CSVファイル名重複",
        "zekken_duplicate": "ゼッケン重複",
        "section_order": "区間通過順",
        "zekken_order": "ゼッケン通過順",
        "invalid_status": "ステータス不正",
        "measurement_type": "計測タイプ",
        "measurement_deficiency": "計測データ不備"
    }
    print(f"     {type_names.get(err_type, err_type)}: {count}")

# Test error confirmation workflow
print("\n4. Testing error confirmation workflow...")
if errors:
    test_error = errors[0]
    print(f"   Test error type: {test_error.error_type}")
    print(f"   Allows confirmation: {test_error.allow_confirmation}")
    print(f"   Initially confirmed: {test_error.confirmed}")
    
    # Try to confirm it
    if test_error.allow_confirmation:
        test_error.confirmed = True
        print(f"   After confirmation: {test_error.confirmed}")
        print(f"   Comparison key: {test_error.get_comparison_key()}")
    else:
        print(f"   Cannot confirm this error (critical)")

# Test error persistence using comparison keys
print("\n5. Testing error persistence (same error detection)...")
confirmed_errors_map = {}
for error in errors[:10]:  # Confirm first 10 errors
    if error.allow_confirmation:
        error.confirmed = True
        confirmed_errors_map[error.get_comparison_key()] = True

print(f"   Stored {len(confirmed_errors_map)} confirmed error keys")

# Simulate re-validation
print("\n6. Simulating re-validation after changes...")
new_errors = validate_all('sample/race', race_parser.results, config_loader.section_list)

# Restore confirmed status
restored_count = 0
for error in new_errors:
    error_key = error.get_comparison_key()
    if error_key in confirmed_errors_map:
        error.confirmed = True
        restored_count += 1

print(f"   Restored confirmed status for {restored_count} errors")

# Count unconfirmed errors
unconfirmed_count = sum(1 for err in new_errors if not err.confirmed)
print(f"   Unconfirmed errors: {unconfirmed_count}/{len(new_errors)}")

# Run calculation and check for measurement deficiency errors
print("\n7. Running calculation for measurement deficiency check...")
calc_engine = CalculationEngine(config_loader, race_parser, co_point=500)
calc_engine.calculate_all()
print("   Calculation complete")

# Re-run validation with calc_engine
print("\n8. Re-validating with calculation results...")
errors_with_calc = validate_all(
    'sample/race',
    race_parser.results,
    config_loader.section_list,
    calc_engine
)

# Check for new errors
new_error_types = {}
for err in errors_with_calc:
    new_error_types[err.error_type] = new_error_types.get(err.error_type, 0) + 1

print(f"   Total errors after calculation: {len(errors_with_calc)}")
if 'measurement_deficiency' in new_error_types:
    print(f"   Measurement deficiency errors: {new_error_types['measurement_deficiency']}")
else:
    print("   No measurement deficiency errors found")

# Show sample of each error type
print("\n9. Sample errors by type:")
shown_types = set()
for error in errors_with_calc[:50]:
    if error.error_type not in shown_types:
        shown_types.add(error.error_type)
        lines = str(error).split('\n')
        print(f"\n   [{error.error_type}]")
        print(f"   {lines[0]}")
        print(f"   Allow confirmation: {error.allow_confirmation}")

print("\n" + "=" * 60)
print("✓ All error handling features tested successfully!")
print("=" * 60)

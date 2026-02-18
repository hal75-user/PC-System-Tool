# Error Handling Implementation Summary

## Overview

This document provides a technical summary of the error handling improvements implemented for the PC System Tool application.

## Changes Made

### 1. New ValidationError Class (`data_validator.py`)

Created a new `ValidationError` class to replace string-based error messages:

```python
class ValidationError:
    - error_type: str - Type identifier for the error
    - message: str - Human-readable error message  
    - details: Dict - Error-specific details for comparison
    - allow_confirmation: bool - Whether error can be marked as confirmed
    - confirmed: bool - Confirmation status
    - get_comparison_key() -> str - Generates unique key for error matching
```

**Benefits:**
- Structured error data
- Support for confirmation status
- Unique key generation for error matching across validations

### 2. New Validation Functions

#### 2.1 Measurement Type Check (`check_measurement_type`)
- **Purpose**: Warn when manual measurement entries (type=T) have bib numbers
- **Logic**: Scans CSV files for rows where `type=T` and `number` column is not empty
- **Error Details**: Records section, time, and bib number for comparison
- **Sample Data Results**: Found 9 errors in sample data

#### 2.2 Measurement Data Deficiency Check (`check_measurement_deficiency`)
- **Purpose**: Detect anomalies in measurement data
- **PC Competition**: Flags if ≥50% of vehicles have ≥1 second deviation
- **CO Competition**: Flags if ≥50% of vehicles have 0 points
- **PCG Competition**: Skipped (not required)
- **Runs After**: Calculation engine completion (requires calculated results)

### 3. Updated All Existing Validators

Converted all existing validation functions to return `ValidationError` objects:
- `check_duplicate_filenames` - CSV file name duplicates (allow_confirmation=False)
- `check_duplicate_zekken_in_section` - Bib duplicates in section (allow_confirmation=False)  
- `check_section_passage_order` - Section passage order mismatches (allow_confirmation=True)
- `check_zekken_passage_order` - Bib passage order mismatches (allow_confirmation=True)
- `check_invalid_status_with_time` - Status inconsistencies (allow_confirmation=True)

### 4. Error Dialog Window (`main_pyside6.py`)

Created `ErrorDialog` class with the following features:

**UI Components:**
- Table with 3 columns: Status, Error Type, Details
- Color-coded status indicators (red=unconfirmed, green=confirmed)
- Row selection for individual error actions

**Actions:**
- Confirm Selected Error
- Confirm All Errors (skips critical errors)
- Unconfirm Selected Error
- Close Dialog

**Error Type Display:**
- Translated error type names in Japanese
- Full error message in details column
- Visual indication of confirmation status

### 5. Main Window Integration

**Replaced:**
- Old: Multi-line text area showing all errors

**New:**
- Single status button at top of window
- Green: "✓ エラーなし（確認済み: X件）" - No unconfirmed errors
- Red: "⚠️ エラーあり（未確認: X/Y）" - Has unconfirmed errors
- Clicking button opens ErrorDialog

**Error State Management:**
- `validation_errors`: List[ValidationError] - Current errors
- `confirmed_errors_map`: Dict[str, bool] - Persists confirmation across re-validations
- Automatic status restoration when same error detected again

### 6. Validation Flow Updates

**Race Data Load (②):**
1. Parse CSV files
2. Run initial validation (without calc_engine)
3. Display error status button
4. Restore previously confirmed errors by comparison key

**Calculate (③):**
1. Check for unconfirmed errors, warn if present
2. Allow user to continue or cancel
3. Run calculation
4. Re-run validation with calc_engine (adds measurement deficiency check)
5. Update error status button

### 7. Supporting Infrastructure

**RaceParser (`race_parser.py`):**
- Added `RaceResult` class for validation
- Added `results` property that generates validation-compatible result objects
- Caches results for performance

**ConfigLoader (`config_loader.py`):**
- Added `SectionInfo` class for validation
- Added `section_list` property that generates validation-compatible section objects
- Caches section list for performance

## Error Comparison Logic

Each error type has specific comparison logic to determine if two errors are "the same":

| Error Type | Comparison Key Components |
|---|---|
| csv_duplicate | section name |
| zekken_duplicate | section + bib number |
| section_order | first section + base order + current section + current order |
| zekken_order | bib number + passed sections |
| invalid_status | section + bib number + status |
| measurement_type | section + time + bib number |
| measurement_deficiency | section |

## Critical Error Prevention

Errors marked with `allow_confirmation=False`:
- CSV filename duplicates
- Bib duplicates in sections

Attempting to confirm these shows a warning:
```
このエラーは確認済みにすることができません。
このエラーは重大な問題のため、必ず修正する必要があります。
```

## Testing

Created `test_error_handling.py` to validate:
1. ValidationError class functionality
2. All validation functions
3. Error confirmation workflow
4. Error state persistence
5. Calculation flow integration

**Test Results on Sample Data:**
- 599 total errors detected
- 9 measurement type errors
- 74 section order errors
- 516 bib order errors
- 0 measurement deficiency errors (data is clean)

## Files Modified

1. **data_validator.py** - New ValidationError class, new validators, updated existing validators
2. **main_pyside6.py** - ErrorDialog, main window error display changes
3. **race_parser.py** - Added results property
4. **config_loader.py** - Added section_list property
5. **test_error_handling.py** - New test script
6. **ERROR_HANDLING_GUIDE.md** - New user documentation

## Benefits

1. **Better User Experience**: Clear visual indication of error status, no cluttered display
2. **Workflow Support**: Confirmation status allows users to work through errors systematically
3. **Efficiency**: Confirmed errors persist across re-validations during same session
4. **Safety**: Critical errors cannot be confirmed, forcing correction
5. **Extensibility**: Easy to add new error types with ValidationError structure
6. **Maintainability**: Centralized error logic, type-safe error handling

## Future Enhancements

Possible improvements:
1. Persist confirmation status to file (survive app restart)
2. Add filtering options in ErrorDialog (show only unconfirmed, etc.)
3. Export errors to CSV for reporting
4. Add error statistics dashboard
5. Batch operations (confirm by type, etc.)
6. Error history tracking

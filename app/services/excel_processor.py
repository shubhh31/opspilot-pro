import pandas as pd
import io
import math

def scan_sap_export(file_bytes, filename: str):
    """
    Parses an uploaded Excel/CSV file and scans for:
    - Missing crucial values
    - Format mismatches (e.g., text in amount, invalid dates)
    - Duplicate entries
    - Business anomalies (e.g., negative amounts, abnormal thresholds)
    
    Returns:
        {
            "headers": list of columns,
            "rows": list of dicts (the actual file contents),
            "errors": list of dicts describing error cells/rows,
            "summary": dict of stats
        }
    """
    try:
        # Load based on extension
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        return {
            "success": False,
            "message": f"Could not read file. Ensure it is a valid Excel or CSV file. Error: {str(e)}"
        }

    # Convert all NaN to None or standard python types so it serializes to JSON
    df = df.where(pd.notnull(df), None)

    # Standardize column names for checking but keep original headers for rendering
    original_cols = list(df.columns)
    cols_lower = [str(c).lower().strip() for c in original_cols]
    
    errors = []
    rows = []
    
    # Identify key columns based on name mappings
    po_col_idx = -1
    amount_col_idx = -1
    date_col_idx = -1
    vendor_col_idx = -1
    dept_col_idx = -1
    
    for idx, col in enumerate(cols_lower):
        if any(keyword in col for keyword in ['po', 'purchase order', 'id', 'document number', 'doc num']):
            po_col_idx = idx
        elif any(keyword in col for keyword in ['amount', 'price', 'value', 'cost', 'total']):
            amount_col_idx = idx
        elif any(keyword in col for keyword in ['date', 'created', 'posting']):
            date_col_idx = idx
        elif any(keyword in col for keyword in ['vendor', 'supplier', 'partner']):
            vendor_col_idx = idx
        elif any(keyword in col for keyword in ['dept', 'department', 'team', 'cost center']):
            dept_col_idx = idx

    # List of unique PO numbers to track duplicates
    seen_pos = set()

    for row_idx, row in df.iterrows():
        row_dict = {}
        # Convert row values to list
        row_vals = list(row.values)
        
        # Populate row dictionary for frontend grid
        for col_name, val in zip(original_cols, row_vals):
            # Check for float NaN
            if isinstance(val, float) and math.isnan(val):
                row_dict[col_name] = None
            else:
                row_dict[col_name] = val
        
        rows.append(row_dict)

        # 1. Check PO ID / Document number
        if po_col_idx != -1:
            po_val = row_vals[po_col_idx]
            col_name = original_cols[po_col_idx]
            if po_val is None or str(po_val).strip() == "":
                errors.append({
                    "row": row_idx,
                    "col": col_name,
                    "type": "Error",
                    "category": "Missing Data",
                    "message": "Purchase Order / ID is missing."
                })
            else:
                po_str = str(po_val).strip()
                if po_str in seen_pos:
                    errors.append({
                        "row": row_idx,
                        "col": col_name,
                        "type": "Warning",
                        "category": "Duplicate Entry",
                        "message": f"Duplicate Purchase Order number: {po_str}"
                    })
                seen_pos.add(po_str)

        # 2. Check Amount / Price
        if amount_col_idx != -1:
            amt_val = row_vals[amount_col_idx]
            col_name = original_cols[amount_col_idx]
            if amt_val is None or str(amt_val).strip() == "":
                errors.append({
                    "row": row_idx,
                    "col": col_name,
                    "type": "Error",
                    "category": "Missing Data",
                    "message": "Amount field is empty."
                })
            else:
                try:
                    val_float = float(amt_val)
                    if val_float < 0:
                        errors.append({
                            "row": row_idx,
                            "col": col_name,
                            "type": "Error",
                            "category": "Invalid Value",
                            "message": f"Negative amount detected: {val_float}"
                        })
                    elif val_float > 500000: # Business rule threshold
                        errors.append({
                            "row": row_idx,
                            "col": col_name,
                            "type": "Warning",
                            "category": "Threshold Warning",
                            "message": f"High value transaction (> $500,000) requiring VP approval: {val_float}"
                        })
                except ValueError:
                    errors.append({
                        "row": row_idx,
                        "col": col_name,
                        "type": "Error",
                        "category": "Format Error",
                        "message": f"Invalid amount format: '{amt_val}' is not a number."
                    })

        # 3. Check Date
        if date_col_idx != -1:
            date_val = row_vals[date_col_idx]
            col_name = original_cols[date_col_idx]
            if date_val is None or str(date_val).strip() == "":
                errors.append({
                    "row": row_idx,
                    "col": col_name,
                    "type": "Error",
                    "category": "Missing Data",
                    "message": "Date field is empty."
                })
            else:
                # Try parsing the date
                try:
                    pd.to_datetime(date_val)
                except Exception:
                    errors.append({
                        "row": row_idx,
                        "col": col_name,
                        "type": "Error",
                        "category": "Format Error",
                        "message": f"Invalid date format: '{date_val}'."
                    })

        # 4. Check Vendor Inconsistencies (Example: Name is empty)
        if vendor_col_idx != -1:
            vendor_val = row_vals[vendor_col_idx]
            col_name = original_cols[vendor_col_idx]
            if vendor_val is None or str(vendor_val).strip() == "":
                errors.append({
                    "row": row_idx,
                    "col": col_name,
                    "type": "Warning",
                    "category": "Missing Data",
                    "message": "Vendor name is empty."
                })

    # Summary Statistics
    num_errors = len([e for e in errors if e["type"] == "Error"])
    num_warnings = len([e for e in errors if e["type"] == "Warning"])

    return {
        "success": True,
        "headers": original_cols,
        "rows": rows,
        "errors": errors,
        "summary": {
            "total_rows": len(df),
            "error_count": num_errors,
            "warning_count": num_warnings,
            "status": "Failed Validation" if num_errors > 0 else ("Passed with Warnings" if num_warnings > 0 else "Passed Validation")
        }
    }

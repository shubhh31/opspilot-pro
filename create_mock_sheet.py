import pandas as pd
import os

# Create mock data dictionary representing a typical SAP export report
# It contains deliberate errors to verify the validation engine
data = {
    "Purchase Order": [
        "PO-4500109001",
        "PO-4500109002",
        "PO-4500109003",
        "PO-4500109004",
        "",              # Missing PO ID (Error)
        "PO-4500109002", # Duplicate PO ID (Warning)
        "PO-4500109006",
        "PO-4500109007"
    ],
    "Description": [
        "Warehouse packaging boxes shipment",
        "Steel reinforcement bars for construction",
        "Consultancy fee for SAP migration support",
        "Safety goggles and protection wear",
        "HVAC system maintenance service",
        "Additional steel bars consignment",
        "Office stationery and printing supplies",
        "Legal advisory consulting fee"
    ],
    "Department": [
        "Warehouse",
        "Procurement",
        "Finance",
        "Warehouse",
        "Facilities",
        "Procurement",
        "Procurement",
        "Legal"
    ],
    "Amount": [
        "12500",
        "284500",
        "Not Available", # Text in amount (Error)
        "450",
        "8900",
        "150000",
        "-350",          # Negative amount (Error)
        "750000"         # Extremely high amount > 500k (Warning)
    ],
    "Created Date": [
        "2026-05-10",
        "2026-05-12",
        "2026-05-14",
        "2026-05-15",
        "2026-05-18",
        "2026-05-19",
        "InvalidDateVal", # Format date issue (Error)
        "2026-05-22"
    ],
    "Vendor Name": [
        "PackCo Logistics Inc.",
        "MetaSteel Industries",
        "Global Analytics Corp.",
        "SafeTech Equipment",
        "",              # Empty vendor (Warning)
        "MetaSteel Industries",
        "PaperPrint Co.",
        "LexCounsel Partners"
    ]
}

# Convert to DataFrame
df = pd.DataFrame(data)

# Export path
out_path = os.path.join(os.path.dirname(__file__), "mock_sap_data.xlsx")

# Save using openpyxl (standard Excel engine)
df.to_excel(out_path, index=False)
print(f"Mock SAP data sheet generated successfully at: {out_path}")

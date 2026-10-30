from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.excel_processor import scan_sap_export
from app.services.ai_service import analyze_excel_errors

router = APIRouter(prefix="/api/upload", tags=["Upload & Scan"])

@router.post("")
async def upload_sap_report(file: UploadFile = File(...)):
    """
    Upload an SAP CSV/Excel report export.
    Returns parsed records, cell-by-cell validation flags, 
    and an AI-generated audit warning.
    """
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls') or file.filename.endswith('.csv')):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Please upload a standard Excel (.xlsx, .xls) or CSV (.csv) file."
        )
    
    try:
        # Read file contents
        contents = await file.read()
        
        # Scan with Pandas processor
        scan_result = scan_sap_export(contents, file.filename)
        
        if not scan_result.get("success", True):
            raise HTTPException(status_code=400, detail=scan_result.get("message", "Error parsing file."))

        # Enrich with AI data quality analysis (even if fallback, it returns structured HTML/markdown notes)
        errors = scan_result.get("errors", [])
        ai_commentary = analyze_excel_errors(errors, file.filename)
        
        scan_result["ai_analysis"] = ai_commentary
        
        return scan_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {str(e)}")

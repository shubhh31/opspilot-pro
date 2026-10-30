import google.generativeai as genai
from app.config import settings
import json

# Flag to check if real AI is configured
is_ai_active = False
if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip() != "":
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        is_ai_active = True
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        is_ai_active = False

def get_model():
    # Use gemini-1.5-flash as the standard fast text model
    return genai.GenerativeModel('gemini-1.5-flash')

def generate_workflow_summary(tasks_list: list) -> str:
    """
    Generates an executive summary of current tasks, highlighting bottlenecks
    and giving recommendations. Falls back to simulated summaries if API key is missing.
    """
    if not is_ai_active:
        return _get_mock_workflow_summary(tasks_list)
        
    try:
        # Prepare context data
        summary_payload = []
        for t in tasks_list:
            summary_payload.append({
                "sap_id": t.sap_id,
                "title": t.title,
                "department": t.department,
                "status": t.status,
                "priority": t.priority,
                "delayed": t.delayed,
                "delay_reason": t.delay_reason,
                "amount": t.amount
            })
            
        prompt = f"""
        You are OpsPilot, an expert AI operational intelligence consultant for SAP systems.
        Analyze the following active workflows/tasks dataset and generate a concise executive summary for management.
        
        DATASET:
        {json.dumps(summary_payload, indent=2)}
        
        INSTRUCTIONS:
        1. Identify the primary bottlenecks (e.g., which department has the most delayed or high priority tasks).
        2. Summarize key high-value risks (tasks with high amount, delayed status, or critical priority).
        3. Provide 3 actionable operational recommendations to resolve delays.
        4. Keep the output professionally formatted with clear markdown headers. Use emojis for readability.
        """
        
        model = get_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ **AI Generation Error**: {str(e)}\n\n*Falling back to system generated summary:*\n" + _get_mock_workflow_summary(tasks_list)


def get_copilot_response(chat_history: list, user_message: str, tasks_list: list) -> str:
    """
    Processes chat with the OpsPilot Copilot. Answers questions about SAP tasks,
    delays, and operations. Falls back to keyword simulation if API key is missing.
    """
    if not is_ai_active:
        return _get_mock_copilot_response(user_message, tasks_list)

    try:
        # Prepare context data
        context = []
        for t in tasks_list:
            context.append({
                "id": t.id,
                "sap_id": t.sap_id,
                "title": t.title,
                "description": t.description,
                "department": t.department,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "assigned_to": t.assigned_to,
                "delayed": t.delayed,
                "delay_reason": t.delay_reason,
                "amount": t.amount
            })

        # Format history for prompt
        history_formatted = ""
        for msg in chat_history[-6:]:  # Keep last 6 messages
            role = "User" if msg.get("role") == "user" else "Copilot"
            history_formatted += f"{role}: {msg.get('text')}\n"

        prompt = f"""
        You are OpsPilot Copilot, an AI assistant built into an operational dashboard for SAP business workflows.
        You have direct access to the live tasks list.
        
        LIVE DATASET:
        {json.dumps(context, indent=2)}
        
        RECENT CHAT HISTORY:
        {history_formatted}
        
        USER QUESTION:
        {user_message}
        
        INSTRUCTIONS:
        1. Use the LIVE DATASET to answer the USER QUESTION.
        2. Be direct, clear, and action-oriented. Reference specific SAP IDs (like PO-XXXX) or department names.
        3. If the user asks about bottlenecks, count which departments have the most 'Delayed' or 'Pending' tasks.
        4. Keep your answer brief (under 150 words) and formatted in clean markdown.
        """
        
        model = get_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🤖 *[Simulation Fallback (Gemini API error)]*\n\n" + _get_mock_copilot_response(user_message, tasks_list)


def analyze_excel_errors(errors: list, filename: str) -> str:
    """
    Explains spreadsheet data quality errors and outlines standard SAP compliance fixes.
    """
    if not is_ai_active:
        return _get_mock_excel_analysis(errors)

    try:
        prompt = f"""
        You are an SAP Data Quality Auditor. An excel report named '{filename}' was uploaded, and our scanner detected these errors/warnings:
        
        ERRORS DETECTED:
        {json.dumps(errors[:10], indent=2)}
        
        INSTRUCTIONS:
        Write a brief data audit note:
        1. Classify the main issues (e.g., Duplicate POs, missing critical headers, amount formatting).
        2. Explain the downstream operational impacts of these errors in SAP (e.g., double payments, stuck invoice matching).
        3. Provide 3 specific directives for the team to fix this data before uploading again.
        4. Keep it concise, professional, and clear.
        """
        model = get_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return _get_mock_excel_analysis(errors)


# ==========================================
# MOCK / FALLBACK GENERATORS (for offline/no key)
# ==========================================

def _get_mock_workflow_summary(tasks_list: list) -> str:
    total = len(tasks_list)
    pending = len([t for t in tasks_list if t.status == "Pending"])
    delayed = len([t for t in tasks_list if t.status == "Delayed" or t.delayed])
    approved = len([t for t in tasks_list if t.status == "Approved"])
    
    # Calculate dept bottleneck
    depts = {}
    total_val = 0.0
    delayed_val = 0.0
    for t in tasks_list:
        total_val += t.amount
        if t.delayed or t.status == "Delayed":
            delayed_val += t.amount
            depts[t.department] = depts.get(t.department, 0) + 1

    bottleneck_dept = "None"
    if depts:
        bottleneck_dept = max(depts, key=depts.get)

    summary = f"""### 📊 Executive Operational Report (Simulation Mode)

Our OpsPilot AI engine analyzed **{total} active SAP workflows** valued at **₹{total_val:,.2f}**.

#### 🔍 Critical Highlights
* ⚠️ **Bottleneck Department**: **{bottleneck_dept}** represents the highest delay frequency, holding {depts.get(bottleneck_dept, 0)} stalled processes.
* 🚨 **At-Risk Capital**: **₹{delayed_val:,.2f}** is currently tied up in **{delayed} delayed approvals**.
* 📈 **Throughput**: **{approved}/{total} ({int(approved/total*100) if total > 0 else 0}%)** of current cycle runs are successfully approved.

#### 💡 Action Items & Recommendations
1. **Accelerate {bottleneck_dept} Approvals**: Set up instant reminders for pending tasks to clear current SLA backlogs.
2. **Review High-Value Requisitions**: Assign secondary managers to process items exceeding ₹10,00,000 to prevent contract start delays.
3. **Establish Vendor Auto-verification**: Standardize tax registration scans on incoming vendor profiles to prevent finance hold delays.
"""
    return summary


def _get_mock_copilot_response(query: str, tasks_list: list) -> str:
    q = query.lower()
    
    # Check if asking about bottlenecks
    if "bottleneck" in q or "slow" in q or "delay" in q:
        depts = {}
        for t in tasks_list:
            if t.delayed or t.status == "Delayed":
                depts[t.department] = depts.get(t.department, 0) + 1
        
        if not depts:
            return "Based on the live task lists, there are currently no delayed tasks or severe bottlenecks. Everything is running within SLA."
        
        slowest = max(depts, key=depts.get)
        count = depts[slowest]
        return f"🤖 **OpsPilot Analysis**: The primary operational bottleneck is currently in the **{slowest}** department, which has **{count} tasks currently delayed**. The most common reason is awaiting vendor compliance certificates or manager signature approvals. I recommend reaching out to the head of {slowest} to clear these blockers."

    # Check if asking about high priority or count
    if "priority" in q or "critical" in q:
        critical_tasks = [t for t in tasks_list if t.priority in ["High", "Critical"]]
        if not critical_tasks:
            return "There are no active High or Critical priority tasks in the system right now."
        
        response_text = f"There are **{len(critical_tasks)} Critical/High priority tasks** requiring immediate attention:\n\n"
        for t in critical_tasks[:3]:
            status_emoji = "🔴" if t.delayed else "🟡"
            response_text += f"* {status_emoji} **{t.sap_id or 'Task'}** ({t.title}) - {t.department} | Value: ₹{t.amount:,.2f}\n"
        return response_text

    # Default general response
    return f"""Hello! I am OpsPilot, your SAP Workflow Assistant. I am running in **Simulation Mode** (configure `GEMINI_API_KEY` to unlock live generative intelligence).

I can help you analyze the dashboard. Try asking:
* *"Which department is the bottleneck?"*
* *"Show me critical priority tasks"* 

How can I assist you with your workflows today?"""


def _get_mock_excel_analysis(errors: list) -> str:
    total_errors = len(errors)
    missing = len([e for e in errors if e["category"] == "Missing Data"])
    dupes = len([e for e in errors if e["category"] == "Duplicate Entry"])
    formats = len([e for e in errors if e["category"] == "Format Error"])

    return f"""### 🛡️ Data Quality Scan Audit (Simulation Mode)

Our validation parsed the uploaded document and flagged **{total_errors} data issues** ({missing} missing fields, {dupes} duplicate keys, {formats} format mismatches).

#### ⚠️ Downstream SAP Implications
* **Duplicate Document IDs**: If uploaded directly to SAP (via BAPI_PO_CREATE), duplicates will cause transactions to fail or double-payment errors.
* **Missing Vendor Identifiers**: Leads to incomplete journal entries, resulting in invoice posting failures and delayed supplier payments.
* **Bad Formatting**: Breaks automated batch workflows, causing standard overnight ERP posting jobs to crash.

#### 🛠️ Directives for Remediation
1. **De-duplicate Excel Sheets**: Remove rows with matching PO Numbers before re-submitting.
2. **Mandatory Cell Completion**: Ensure the columns for **Amount** and **Vendor Name** contain valid data for every row.
3. **Format Integrity**: Verify that transaction amounts are pure numbers without currency symbols (e.g. use `1500` instead of `₹1,500`).
"""

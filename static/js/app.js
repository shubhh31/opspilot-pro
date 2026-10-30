// OpsPilot Pro - Client Application Logic

document.addEventListener("DOMContentLoaded", () => {
    // Current application state
    const state = {
        activeTab: "dashboard",
        tasks: [],
        analytics: null,
        chatHistory: [
            { role: "assistant", text: "Hello! I am OpsPilot. Ask me any questions about SAP tasks, department bottlenecks, or pending approvals." }
        ],
        charts: {
            dept: null,
            priority: null
        }
    };

    // Initialize UI
    initNavigation();
    initCopilot();
    initExcelScanner();
    initTaskTracker();
    initGeneralButtons();
    
    // Initial data load
    refreshAppData();
    checkAiStatus();

    // ==========================================
    // Core Navigation & Tabs
    // ==========================================
    function initNavigation() {
        const navItems = document.querySelectorAll(".nav-item");
        navItems.forEach(item => {
            item.addEventListener("click", () => {
                const tabId = item.getAttribute("data-tab");
                switchTab(tabId);
            });
        });
    }

    function switchTab(tabId) {
        state.activeTab = tabId;
        
        // Update nav buttons
        document.querySelectorAll(".nav-item").forEach(btn => {
            if (btn.getAttribute("data-tab") === tabId) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        // Update tab panels
        document.querySelectorAll(".tab-pane").forEach(pane => {
            pane.classList.remove("active");
        });
        
        const activePane = document.getElementById(`tab-${tabId}`);
        if (activePane) activePane.classList.add("active");

        // Update title
        const titles = {
            dashboard: "Command Center",
            scanner: "Excel Data Scan",
            tracker: "Workflow Ledger"
        };
        document.getElementById("pageTitle").textContent = titles[tabId] || "Dashboard";

        // Refresh tab-specific views if needed
        if (tabId === "dashboard") {
            renderCharts();
        }
        
        lucide.createIcons();
    }

    // ==========================================
    // Fetch and Sync API Data
    // ==========================================
    async function refreshAppData() {
        try {
            await Promise.all([
                fetchTasks(),
                fetchAnalytics(),
                fetchAiSummary()
            ]);
            
            // Re-render UI
            renderDashboardMetrics();
            renderBottlenecks();
            renderCharts();
            renderTrackerTable();
            lucide.createIcons();
        } catch (err) {
            console.error("Error loading application data:", err);
        }
    }

    async function fetchTasks() {
        const res = await fetch("/api/tasks");
        if (res.ok) {
            state.tasks = await res.json();
        }
    }

    async function fetchAnalytics() {
        const res = await fetch("/api/tasks/analytics");
        if (res.ok) {
            state.analytics = await res.json();
        }
    }

    async function fetchAiSummary(force = false) {
        const summaryContainer = document.getElementById("aiSummaryContent");
        
        // Show loading spinner only if empty or forced
        if (force || summaryContainer.innerHTML.includes("loading-state") || summaryContainer.innerHTML === "") {
            summaryContainer.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>AI is parsing live database workflows...</p>
                </div>
            `;
        }

        try {
            const res = await fetch("/api/copilot/summary");
            if (res.ok) {
                const data = await res.json();
                summaryContainer.innerHTML = formatMarkdown(data.summary);
            } else {
                summaryContainer.innerHTML = "<p class='text-danger'>Error generating executive summary. Try again later.</p>";
            }
        } catch (e) {
            summaryContainer.innerHTML = "<p class='text-danger'>Connection error to the AI service.</p>";
        }
    }

    async function checkAiStatus() {
        try {
            const res = await fetch("/api/copilot/summary");
            const statusDesc = document.getElementById("aiStatusDesc");
            const indicator = document.getElementById("aiStatusIndicator");
            
            if (res.ok) {
                const data = await res.json();
                if (data.summary.includes("Simulation Mode")) {
                    statusDesc.textContent = "Simulation Mode (Offline)";
                    indicator.className = "status-indicator online";
                    // Change glow color in CSS if needed, but yellow/orange represents simulation
                    indicator.style.backgroundColor = "#f59e0b";
                    indicator.style.boxShadow = "0 0 10px #f59e0b";
                } else {
                    statusDesc.textContent = "Gemini 1.5 Active";
                    indicator.className = "status-indicator online";
                    indicator.style.backgroundColor = "";
                    indicator.style.boxShadow = "";
                }
            } else {
                statusDesc.textContent = "Disconnected";
                indicator.className = "status-indicator offline";
            }
        } catch (e) {
            document.getElementById("aiStatusDesc").textContent = "Disconnected";
            document.getElementById("aiStatusIndicator").className = "status-indicator offline";
        }
    }

    // ==========================================
    // Render Dashboard Tab UI
    // ==========================================
    function renderDashboardMetrics() {
        if (!state.analytics) return;
        
        const a = state.analytics;
        document.getElementById("valTotalTasks").textContent = a.total_tasks;
        document.getElementById("valDelayedTasks").textContent = a.delayed_count;
        document.getElementById("valApprovedTasks").textContent = a.approved_count;
        document.getElementById("valDelayedValue").textContent = formatCurrency(a.delayed_value);

        // Highlight card if there are delayed tasks
        const delayCard = document.querySelector(".metric-card.alert-pulse");
        if (a.delayed_count > 0) {
            delayCard.classList.add("active-danger");
        } else {
            delayCard.classList.remove("active-danger");
        }
    }

    function renderBottlenecks() {
        const container = document.getElementById("bottleneckList");
        if (!state.analytics || !state.analytics.bottlenecks || state.analytics.bottlenecks.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 20px;">
                    <i data-lucide="check" class="empty-state-icon" style="color: var(--color-success);"></i>
                    <p style="margin: 0;">SLA parameters aligned. No current bottlenecks.</p>
                </div>
            `;
            return;
        }

        let html = "";
        state.analytics.bottlenecks.forEach(b => {
            const riskLevel = b.risk_factor >= 7 ? "risk-high" : "risk-medium";
            const fillWidth = Math.min(b.risk_factor * 10, 100);

            html += `
                <div class="bottleneck-item">
                    <div class="bottleneck-top">
                        <span class="bottleneck-dept">${b.department}</span>
                        <span class="risk-badge ${riskLevel}">Risk index: ${b.risk_factor}/10</span>
                    </div>
                    <div class="bottleneck-stats">
                        <span>⚠️ ${b.delayed_count} Delayed</span>
                        <span>🕒 ${b.pending_count} Pending</span>
                    </div>
                    <div class="bottleneck-bar-bg">
                        <div class="bottleneck-bar-fill" style="width: ${fillWidth}%;"></div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    function renderCharts() {
        if (!state.analytics) return;

        // 1. Department Bar Chart (Value & Count)
        const ctxDept = document.getElementById("chartDept").getContext("2d");
        const deptLabels = Object.keys(state.analytics.department_stats);
        const deptTotals = [];
        const deptDelayed = [];
        
        deptLabels.forEach(d => {
            const stats = state.analytics.department_stats[d];
            deptTotals.push(stats.total);
            deptDelayed.push(stats.delayed);
        });

        if (state.charts.dept) state.charts.dept.destroy();
        state.charts.dept = new Chart(ctxDept, {
            type: "bar",
            data: {
                labels: deptLabels,
                datasets: [
                    {
                        label: "Total Workflows",
                        data: deptTotals,
                        backgroundColor: "rgba(59, 130, 246, 0.4)",
                        borderColor: "rgba(59, 130, 246, 1)",
                        borderWidth: 1.5,
                        borderRadius: 4
                    },
                    {
                        label: "Delayed Approvals",
                        data: deptDelayed,
                        backgroundColor: "rgba(239, 68, 68, 0.5)",
                        borderColor: "rgba(239, 68, 68, 1)",
                        borderWidth: 1.5,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: "#9ca3af", font: { family: "Plus Jakarta Sans" } } }
                },
                scales: {
                    x: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(255,255,255,0.05)" } },
                    y: { ticks: { color: "#9ca3af", stepSize: 1 }, grid: { color: "rgba(255,255,255,0.05)" } }
                }
            }
        });

        // 2. Priority Doughnut Chart
        const ctxPriority = document.getElementById("chartPriority").getContext("2d");
        const priorityKeys = ["Critical", "High", "Medium", "Low"];
        const priorityData = priorityKeys.map(k => state.analytics.priority_stats[k] || 0);

        if (state.charts.priority) state.charts.priority.destroy();
        state.charts.priority = new Chart(ctxPriority, {
            type: "doughnut",
            data: {
                labels: priorityKeys,
                datasets: [{
                    data: priorityData,
                    backgroundColor: [
                        "rgba(239, 68, 68, 0.7)",  // Critical
                        "rgba(245, 158, 11, 0.7)", // High
                        "rgba(59, 130, 246, 0.7)", // Medium
                        "rgba(107, 114, 128, 0.7)" // Low
                    ],
                    borderColor: "rgba(11, 15, 25, 1)",
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: "right", 
                        labels: { color: "#9ca3af", font: { family: "Plus Jakarta Sans" } } 
                    }
                }
            }
        });
    }

    // ==========================================
    // Render Task Tracker UI
    // ==========================================
    function initTaskTracker() {
        const filterDept = document.getElementById("filterDept");
        const filterPriority = document.getElementById("filterPriority");
        const btnAddTask = document.getElementById("btnAddTask");
        const btnCancelTask = document.getElementById("btnCancelTask");
        const btnCloseTaskModal = document.getElementById("btnCloseTaskModal");
        const addTaskForm = document.getElementById("addTaskForm");
        
        filterDept.addEventListener("change", renderTrackerTable);
        filterPriority.addEventListener("change", renderTrackerTable);
        
        // Modals Toggle
        btnAddTask.addEventListener("click", () => {
            // Set default date to today + 7 days
            const dateInput = document.getElementById("taskDueDate");
            const d = new Date();
            d.setDate(d.getDate() + 7);
            dateInput.value = d.toISOString().split("T")[0];
            
            document.getElementById("addTaskModal").classList.remove("hidden");
        });
        
        const closeForm = () => {
            document.getElementById("addTaskModal").classList.add("hidden");
            addTaskForm.reset();
        };
        btnCancelTask.addEventListener("click", closeForm);
        btnCloseTaskModal.addEventListener("click", closeForm);
        
        // Add Task Submit
        addTaskForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const payload = {
                sap_id: document.getElementById("taskSapId").value.trim() || null,
                title: document.getElementById("taskTitle").value.trim(),
                description: document.getElementById("taskDesc").value.trim() || null,
                department: document.getElementById("taskDept").value,
                priority: document.getElementById("taskPriority").value,
                amount: parseFloat(document.getElementById("taskAmount").value) || 0.0,
                due_date: document.getElementById("taskDueDate").value,
                assigned_to: document.getElementById("taskAssignee").value.trim()
            };

            const res = await fetch("/api/tasks/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                closeForm();
                refreshAppData();
            } else {
                alert("Failed to create task workflow.");
            }
        });

        // Delay Modal Actions
        const btnCloseDelayModal = document.getElementById("btnCloseDelayModal");
        const btnCancelDelay = document.getElementById("btnCancelDelay");
        const delayForm = document.getElementById("delayForm");

        const closeDelayForm = () => {
            document.getElementById("delayModal").classList.add("hidden");
            delayForm.reset();
        };
        btnCloseDelayModal.addEventListener("click", closeDelayForm);
        btnCancelDelay.addEventListener("click", closeDelayForm);

        delayForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const taskId = document.getElementById("delayTaskId").value;
            const reason = document.getElementById("delayReason").value.trim();

            const res = await fetch(`/api/tasks/${taskId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    delayed: true,
                    delay_reason: reason
                })
            });

            if (res.ok) {
                closeDelayForm();
                refreshAppData();
            } else {
                alert("Error setting delay state.");
            }
        });

        // Audit Close Drawer
        document.getElementById("btnCloseAudit").addEventListener("click", () => {
            document.getElementById("auditDrawer").classList.remove("open");
        });
    }

    function renderTrackerTable() {
        const tbody = document.querySelector("#trackerTable tbody");
        const fDept = document.getElementById("filterDept").value;
        const fPriority = document.getElementById("filterPriority").value;
        
        tbody.innerHTML = "";
        
        // Filter tasks
        const filtered = state.tasks.filter(t => {
            if (fDept !== "All" && t.department !== fDept) return false;
            if (fPriority !== "All" && t.priority !== fPriority) return false;
            return true;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                        No tasks matched the filters.
                    </td>
                </tr>
            `;
            return;
        }

        filtered.forEach(t => {
            const tr = document.createElement("tr");
            
            // Priority Class
            const priorityClass = `priority-${t.priority.toLowerCase()}`;
            
            // Status Class
            const statusClass = `status-${t.status.replace(" ", "").toLowerCase()}`;
            
            // Format dates
            const dueStr = new Date(t.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
            
            tr.innerHTML = `
                <td><strong>${t.sap_id || "N/A"}</strong></td>
                <td>
                    <div style="font-weight: 500;">${t.title}</div>
                    <div class="text-muted" style="font-size: 11px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${t.description || "No description provided"}</div>
                </td>
                <td>${t.department}</td>
                <td>${t.assigned_to}</td>
                <td><span class="priority-lbl ${priorityClass}">${t.priority}</span></td>
                <td><strong>${formatCurrency(t.amount)}</strong></td>
                <td>${dueStr}</td>
                <td><span class="status-pill ${statusClass}">${t.status}</span></td>
                <td>
                    <div class="btn-action-row">
                        ${t.status === "Pending" ? `
                            <button class="btn-action approve" data-id="${t.id}" title="Approve Workflow">
                                <i data-lucide="check-square"></i>
                            </button>
                            <button class="btn-action delay" data-id="${t.id}" title="Flag Delay Reason">
                                <i data-lucide="clock-alert"></i>
                            </button>
                        ` : ''}
                        <button class="btn-action audit" data-id="${t.id}" title="View Audit Trail Ledger">
                            <i data-lucide="history"></i>
                        </button>
                    </div>
                </td>
            `;

            // Bind Actions manually to avoid string eval scope issues
            tr.querySelector(".approve")?.addEventListener("click", () => approveTask(t.id));
            tr.querySelector(".delay")?.addEventListener("click", () => openDelayModal(t.id));
            tr.querySelector(".audit").addEventListener("click", () => openAuditDrawer(t.id));

            tbody.appendChild(tr);
        });
    }

    async function approveTask(id) {
        const res = await fetch(`/api/tasks/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "Approved" })
        });
        if (res.ok) {
            refreshAppData();
        }
    }

    function openDelayModal(id) {
        document.getElementById("delayTaskId").value = id;
        document.getElementById("delayModal").classList.remove("hidden");
    }

    async function openAuditDrawer(id) {
        const drawer = document.getElementById("auditDrawer");
        
        // Reset contents
        document.getElementById("auditTaskTitle").textContent = "Loading...";
        document.getElementById("auditTaskSapId").textContent = "";
        document.getElementById("auditTaskVal").textContent = "";
        document.getElementById("auditTaskOwner").textContent = "";
        document.getElementById("auditTaskDue").textContent = "";
        document.getElementById("auditDelayAlert").classList.add("hidden");
        document.getElementById("auditTimeline").innerHTML = "<div class='spinner' style='margin: 20px auto;'></div>";

        drawer.classList.add("open");

        try {
            // Find task details locally
            const task = state.tasks.find(t => t.id === id);
            if (!task) return;

            document.getElementById("auditTaskTitle").textContent = task.title;
            document.getElementById("auditTaskSapId").textContent = task.sap_id || "PO Draft";
            document.getElementById("auditTaskVal").textContent = formatCurrency(task.amount);
            document.getElementById("auditTaskOwner").textContent = task.assigned_to;
            document.getElementById("auditTaskDue").textContent = new Date(task.due_date).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
            
            if (task.delayed || task.status === "Delayed") {
                document.getElementById("auditDelayAlert").classList.remove("hidden");
                document.getElementById("auditDelayReason").textContent = task.delay_reason || "Escalation registered by AI workflow audit.";
            }

            // Fetch logs
            const res = await fetch(`/api/tasks/${id}/audit`);
            if (res.ok) {
                const logs = await res.json();
                const timeline = document.getElementById("auditTimeline");
                timeline.innerHTML = "";

                if (logs.length === 0) {
                    timeline.innerHTML = "<p class='text-muted'>No audit logs registered yet.</p>";
                    return;
                }

                logs.forEach(l => {
                    const evt = document.createElement("div");
                    evt.className = "timeline-event";
                    
                    let dotClass = "updated";
                    if (l.action === "Created") dotClass = "created";
                    else if (l.action === "Approved") dotClass = "approved";
                    else if (l.action.includes("Delay") || l.action.includes("Warning")) dotClass = "delayed";

                    const timeStr = new Date(l.timestamp).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) + 
                                   " - " + new Date(l.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" });

                    evt.innerHTML = `
                        <div class="timeline-dot ${dotClass}"></div>
                        <div class="timeline-header">
                            <span class="timeline-action">${l.action}</span>
                            <span class="timeline-time">${timeStr}</span>
                        </div>
                        <div class="timeline-actor">by ${l.performed_by}</div>
                        <div class="timeline-details">${l.details || "No details provided"}</div>
                    `;
                    timeline.appendChild(evt);
                });
            }
        } catch (e) {
            document.getElementById("auditTimeline").innerHTML = "<p class='text-danger'>Failed to load audit trail history.</p>";
        }
    }

    // ==========================================
    // Excel Data Quality Scanner Tab UI
    // ==========================================
    function initExcelScanner() {
        const dropzone = document.getElementById("dropzone");
        const fileInput = document.getElementById("fileInput");
        const btnBrowse = document.getElementById("btnBrowse");
        
        btnBrowse.addEventListener("click", () => fileInput.click());
        
        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                uploadExcelFile(e.target.files[0]);
            }
        });

        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });

        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("dragover");
        });

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                uploadExcelFile(e.dataTransfer.files[0]);
            }
        });
    }

    async function uploadExcelFile(file) {
        const dropzone = document.getElementById("dropzone");
        const results = document.getElementById("scannerResults");
        const aiReport = document.getElementById("scanAiReport");

        // UI Loading State
        dropzone.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Reading file & running AI quality compliance scan...</p>
            </div>
        `;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                
                // Hide dropzone, show grid
                dropzone.classList.add("hidden");
                results.classList.remove("hidden");

                // Populate meta
                document.getElementById("scanFilename").textContent = file.name;
                document.getElementById("scanTotalRows").textContent = data.summary.total_rows;
                document.getElementById("scanErrors").textContent = data.summary.error_count;
                document.getElementById("scanWarnings").textContent = data.summary.warning_count;

                // Render grid
                renderExcelGrid(data.headers, data.rows, data.errors);

                // Render AI analysis report on right
                aiReport.innerHTML = formatMarkdown(data.ai_analysis);
            } else {
                throw new Error("API responded with an error.");
            }
        } catch (e) {
            // Restore dropzone
            dropzone.classList.remove("hidden");
            dropzone.innerHTML = `
                <i data-lucide="upload-cloud" class="upload-icon"></i>
                <p class="upload-text">Drag and drop your SAP export Excel (.xlsx) or CSV file here</p>
                <span class="upload-subtext">Supports PO, SO, and Transaction tables</span>
                <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" class="hidden-input">
                <button class="btn btn-primary" id="btnBrowse">Browse Files</button>
            `;
            initExcelScanner(); // Re-bind events
            alert("File upload failed. Ensure it is a valid spreadsheet file.");
        }
        lucide.createIcons();
    }

    function renderExcelGrid(headers, rows, errors) {
        const table = document.getElementById("excelGrid");
        const thead = table.querySelector("thead");
        const tbody = table.querySelector("tbody");

        thead.innerHTML = "";
        tbody.innerHTML = "";

        // Render header row (with leading Row index column)
        const headerTr = document.createElement("tr");
        headerTr.innerHTML = "<th>#</th>" + headers.map(h => `<th>${h}</th>`).join("");
        thead.appendChild(headerTr);

        // Map error coordinates for quick lookup: row_col -> error object
        const errMap = {};
        errors.forEach(e => {
            const key = `${e.row}_${e.col}`;
            errMap[key] = e;
        });

        // Render data rows
        rows.forEach((row, rowIdx) => {
            const tr = document.createElement("tr");
            
            // Index column cell
            let rowHtml = `<td style="color: var(--text-muted); font-weight: bold; background-color: #111827; position: sticky; left: 0;">${rowIdx + 1}</td>`;
            
            // Value cells
            headers.forEach(h => {
                const val = row[h] === null ? "" : row[h];
                const key = `${rowIdx}_${h}`;
                const errObj = errMap[key];
                
                let cellClass = "";
                let tooltipAttr = "";

                if (errObj) {
                    cellClass = errObj.type === "Error" ? "cell-error" : "cell-warning";
                    tooltipAttr = `data-tooltip="${errObj.category}: ${errObj.message}"`;
                }

                rowHtml += `<td class="${cellClass}" ${tooltipAttr}>${val}</td>`;
            });

            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        });
    }

    // ==========================================
    // Floating AI Copilot Chat Drawer UI
    // ==========================================
    function initCopilot() {
        const drawer = document.getElementById("copilotDrawer");
        const btnOpen = document.getElementById("btnOpenCopilot");
        const btnClose = document.getElementById("btnCloseCopilot");
        const chatForm = document.getElementById("chatForm");
        const chatInput = document.getElementById("chatInput");
        
        btnOpen.addEventListener("click", () => {
            drawer.classList.add("open");
            renderChatHistory();
        });

        btnClose.addEventListener("click", () => {
            drawer.classList.remove("open");
        });

        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            // Clear input
            chatInput.value = "";

            // Push User Message
            state.chatHistory.push({ role: "user", text: text });
            renderChatHistory();

            // Append floating loading message
            const messagesContainer = document.getElementById("chatMessages");
            const loadingBubble = document.createElement("div");
            loadingBubble.className = "chat-msg bot loading-bubble";
            loadingBubble.innerHTML = "<div class='spinner' style='width: 14px; height: 14px; border-width: 2px;'></div>";
            messagesContainer.appendChild(loadingBubble);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            try {
                // Prepare API history payload in correct backend format
                const apiHistory = state.chatHistory.slice(0, -1).map(h => ({
                    role: h.role,
                    text: h.text
                }));

                const res = await fetch("/api/copilot/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        message: text,
                        history: apiHistory
                    })
                });

                // Remove loading bubble
                loadingBubble.remove();

                if (res.ok) {
                    const data = await res.json();
                    state.chatHistory.push({ role: "assistant", text: data.reply });
                    renderChatHistory();
                } else {
                    state.chatHistory.push({ role: "assistant", text: "⚠️ Server encountered an error trying to process your request." });
                    renderChatHistory();
                }
            } catch (err) {
                loadingBubble.remove();
                state.chatHistory.push({ role: "assistant", text: "⚠️ Network disconnected. AI is currently offline." });
                renderChatHistory();
            }
        });
    }

    function renderChatHistory() {
        const container = document.getElementById("chatMessages");
        container.innerHTML = "";

        state.chatHistory.forEach(msg => {
            const el = document.createElement("div");
            el.className = `chat-msg ${msg.role === "user" ? "user" : "bot"}`;
            
            // Format bots response (allows markdown summary responses in chat drawer too)
            if (msg.role === "assistant") {
                el.innerHTML = formatMarkdown(msg.text);
            } else {
                el.textContent = msg.text;
            }
            container.appendChild(el);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    // ==========================================
    // System General Action Buttons (Reset, Refresh)
    // ==========================================
    function initGeneralButtons() {
        // Reset DB Mock Data
        document.getElementById("btnResetDB").addEventListener("click", async () => {
            if (confirm("Are you sure you want to delete all current workflows and restore defaults?")) {
                const res = await fetch("/api/tasks/seed", { method: "POST" });
                if (res.ok) {
                    refreshAppData();
                    alert("Database restored successfully!");
                }
            }
        });

        // Refresh Summary Card
        document.getElementById("btnRefreshSummary").addEventListener("click", () => {
            fetchAiSummary(true);
        });
    }

    // ==========================================
    // UI Helpers (Markdown parser & currency formats)
    // ==========================================
    function formatCurrency(val) {
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0
        }).format(val);
    }


    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = text
            // Escaping HTML characters
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            // Headers
            .replace(/^### (.*$)/gim, "<h3>$1</h3>")
            .replace(/^#### (.*$)/gim, "<h4>$1</h4>")
            .replace(/^## (.*$)/gim, "<h3>$1</h3>")
            .replace(/^# (.*$)/gim, "<h2>$1</h2>")
            // Bold
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            // Lists
            .replace(/^\s*\*\s+(.*$)/gim, "<li>$1</li>")
            .replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>");

        // Group lists together
        formatted = formatted.replace(/(<li>.*<\/li>)/gim, "<ul>$1</ul>");
        // Fix nested double-ul
        formatted = formatted.replace(/<\/ul>\s*<ul>/gim, "");
        
        // Paragraph newlines
        return formatted.split("\n\n").map(p => {
            if (p.trim().startsWith("<h") || p.trim().startsWith("<ul") || p.trim().startsWith("<li>")) {
                return p;
            }
            return `<p>${p.replace(/\n/g, "<br>")}</p>`;
        }).join("");
    }
});

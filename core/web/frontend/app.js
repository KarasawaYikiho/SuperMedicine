/**
 * SuperMedicine Web Interface — Client Logic
 *
 * Manages WebSocket connection, tab navigation, API calls,
 * data rendering, and real-time updates.
 */

(function () {
    "use strict";

    // ---- DOM References --------------------------------------------------

    const messagesEl = document.getElementById("messages");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const statusIndicator = document.getElementById("status-indicator");
    const statusText = document.getElementById("status-text");
    const projectStatusEl = document.getElementById("project-status");

    // ---- State -----------------------------------------------------------

    let ws = null;
    let reconnectTimer = null;
    const RECONNECT_DELAY = 3000;
    let currentWorkspaceId = null;

    // ---- Helpers ---------------------------------------------------------

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function showToast(message, type) {
        type = type || "info";
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = "toast " + type;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, 3000);
    }

    function addMessage(role, content, extraClass) {
        const div = document.createElement("div");
        let cls = "message " + role;
        if (extraClass) cls += " " + extraClass;
        div.className = cls;

        const roleLabel = document.createElement("div");
        roleLabel.className = "role";
        roleLabel.textContent = role === "user" ? "You" : role === "assistant" ? "SuperMedicine" : role;
        div.appendChild(roleLabel);

        const body = document.createElement("div");
        body.textContent = content;
        div.appendChild(body);

        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function setConnected(connected) {
        statusIndicator.className = connected ? "connected" : "disconnected";
        statusText.textContent = connected ? "Connected" : "Disconnected";
    }

    // ---- API Helper ------------------------------------------------------

    async function apiCall(method, url, body) {
        const opts = {
            method: method,
            headers: { "Content-Type": "application/json" },
        };
        if (body) opts.body = JSON.stringify(body);

        const resp = await fetch(url, opts);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
    }

    // ---- Tab Navigation --------------------------------------------------

    function initTabs() {
        var tabBtns = document.querySelectorAll(".tab-btn");
        tabBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var tabId = this.getAttribute("data-tab");

                // Update button states
                tabBtns.forEach(function (b) {
                    b.classList.remove("active");
                });
                this.classList.add("active");

                // Update content visibility
                document.querySelectorAll(".tab-content").forEach(function (c) {
                    c.classList.remove("active");
                });
                document.getElementById("tab-" + tabId).classList.add("active");

                // Load data for the tab
                loadTabData(tabId);
            });
        });
    }

    function loadTabData(tabId) {
        switch (tabId) {
            case "dashboard":
                fetchStatus();
                break;
            case "workspaces":
                loadWorkspaces();
                break;
            case "papers":
                loadWorkspaceSelectors();
                break;
            case "experiences":
                loadWorkspaceSelectors();
                break;
            case "tools":
                loadWorkspaceSelectors();
                break;
            case "experiments":
                loadExperiments();
                break;
            case "llm":
                loadLLMProviders();
                break;
            case "permissions":
                loadPermissions();
                break;
            case "logs":
                loadLogs();
                break;
        }
    }

    // ---- Status fetch ----------------------------------------------------

    async function fetchStatus() {
        try {
            const data = await apiCall("GET", "/api/v1/status");

            projectStatusEl.innerHTML =
                '<div class="status-card">' +
                '<div class="label">Version</div>' +
                '<div class="value">' + escapeHtml(data.version || "unknown") + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">Config</div>' +
                '<div class="value">' + (data.config_initialized ? "Initialized" : "Not initialized") + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">Plugins</div>' +
                '<div class="value">' + (data.plugin_count ?? 0) + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">LLM Provider</div>' +
                '<div class="value">' + escapeHtml(data.llm_provider || "N/A") + "</div>" +
                "</div>";
        } catch (err) {
            projectStatusEl.innerHTML =
                '<div style="color:var(--color-error)">Failed to load status: ' +
                escapeHtml(err.message) + "</div>";
        }
    }

    // ---- Workspace Management --------------------------------------------

    async function loadWorkspaces() {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces");
            renderWorkspaces(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to load workspaces: " + err.message, "error");
        }
    }

    function renderWorkspaces(workspaces) {
        var tbody = document.getElementById("workspace-tbody");
        if (!workspaces.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No workspaces found</td></tr>';
            return;
        }
        tbody.innerHTML = workspaces.map(function (ws) {
            return "<tr>" +
                "<td>" + escapeHtml(ws.id || ws.name || "-") + "</td>" +
                "<td>" + escapeHtml(ws.name || ws.id || "-") + "</td>" +
                "<td><span class=\"status-badge success\">Active</span></td>" +
                "<td><button class=\"btn btn-danger btn-sm\" onclick=\"deleteWorkspace('" + escapeHtml(ws.id || ws.name) + "')\">Delete</button></td>" +
                "</tr>";
        }).join("");
    }

    function setupWorkspaceForm() {
        var form = document.getElementById("workspace-form");
        document.getElementById("btn-add-workspace").addEventListener("click", function () {
            form.classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-workspace").addEventListener("click", function () {
            form.classList.add("hidden");
        });
        document.getElementById("btn-save-workspace").addEventListener("click", async function () {
            var id = document.getElementById("ws-id").value.trim();
            var name = document.getElementById("ws-name").value.trim();
            if (!id) {
                showToast("Workspace ID is required", "warning");
                return;
            }
            try {
                await apiCall("POST", "/api/v1/workspaces", { id: id, name: name || undefined });
                showToast("Workspace created successfully", "success");
                form.classList.add("hidden");
                document.getElementById("ws-id").value = "";
                document.getElementById("ws-name").value = "";
                loadWorkspaces();
            } catch (err) {
                showToast("Failed to create workspace: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-workspaces").addEventListener("click", loadWorkspaces);
    }

    // Global function for inline onclick
    window.deleteWorkspace = async function (id) {
        if (!confirm("Delete workspace '" + id + "'?")) return;
        try {
            await apiCall("DELETE", "/api/v1/workspaces/" + encodeURIComponent(id));
            showToast("Workspace deleted", "success");
            loadWorkspaces();
        } catch (err) {
            showToast("Failed to delete workspace: " + err.message, "error");
        }
    };

    // ---- Workspace Selectors ---------------------------------------------

    async function loadWorkspaceSelectors() {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces");
            var workspaces = Array.isArray(data) ? data : [];
            var selectors = ["paper-ws-select", "exp-ws-select", "tool-ws-select"];
            selectors.forEach(function (selId) {
                var sel = document.getElementById(selId);
                var current = sel.value;
                sel.innerHTML = '<option value="">Select Workspace</option>';
                workspaces.forEach(function (ws) {
                    var opt = document.createElement("option");
                    opt.value = ws.id || ws.name;
                    opt.textContent = ws.name || ws.id;
                    sel.appendChild(opt);
                });
                if (current) sel.value = current;
            });
        } catch (err) {
            // Silently fail for selectors
        }
    }

    // ---- Paper Management ------------------------------------------------

    function setupPaperForm() {
        var form = document.getElementById("paper-form");
        document.getElementById("btn-add-paper").addEventListener("click", function () {
            if (!document.getElementById("paper-ws-select").value) {
                showToast("Select a workspace first", "warning");
                return;
            }
            form.classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-paper").addEventListener("click", function () {
            form.classList.add("hidden");
        });
        document.getElementById("btn-save-paper").addEventListener("click", async function () {
            var wsId = document.getElementById("paper-ws-select").value;
            var source = document.getElementById("paper-source").value.trim();
            var title = document.getElementById("paper-title").value.trim();
            var enrich = document.getElementById("paper-enrich").checked;
            if (!source) {
                showToast("Source path is required", "warning");
                return;
            }
            try {
                var body = { source_path: source, enrich: enrich };
                if (title) body.metadata = { title: title };
                await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers", body);
                showToast("Paper imported successfully", "success");
                form.classList.add("hidden");
                document.getElementById("paper-source").value = "";
                document.getElementById("paper-title").value = "";
                document.getElementById("paper-enrich").checked = false;
                loadPapers(wsId);
            } catch (err) {
                showToast("Failed to import paper: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-papers").addEventListener("click", function () {
            var wsId = document.getElementById("paper-ws-select").value;
            if (wsId) loadPapers(wsId);
        });
        document.getElementById("paper-ws-select").addEventListener("change", function () {
            if (this.value) loadPapers(this.value);
        });
    }

    async function loadPapers(wsId) {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers");
            renderPapers(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to load papers: " + err.message, "error");
        }
    }

    function renderPapers(papers) {
        var tbody = document.getElementById("paper-tbody");
        if (!papers.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No papers found</td></tr>';
            return;
        }
        tbody.innerHTML = papers.map(function (p) {
            return "<tr>" +
                "<td>" + escapeHtml(p.id || "-") + "</td>" +
                "<td>" + escapeHtml(p.title || p.metadata?.title || "-") + "</td>" +
                "<td>" + escapeHtml(p.authors || p.metadata?.authors || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.enriched ? "success" : "info") + "\">" + (p.enriched ? "Enriched" : "Imported") + "</span></td>" +
                "<td><button class=\"btn btn-secondary btn-sm\" onclick=\"enrichPaper('" + escapeHtml(currentWorkspaceId || "") + "','" + escapeHtml(p.id || "") + "')\">Enrich</button></td>" +
                "</tr>";
        }).join("");
    }

    window.enrichPaper = async function (wsId, paperId) {
        if (!wsId || !paperId) return;
        try {
            await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers/" + encodeURIComponent(paperId) + "/enrich", { confirm_enrich: true });
            showToast("Paper enrichment started", "info");
            loadPapers(wsId);
        } catch (err) {
            showToast("Failed to enrich paper: " + err.message, "error");
        }
    };

    // ---- Experience Management -------------------------------------------

    function setupExperienceForm() {
        var form = document.getElementById("experience-form");
        document.getElementById("btn-add-experience").addEventListener("click", function () {
            if (!document.getElementById("exp-ws-select").value) {
                showToast("Select a workspace first", "warning");
                return;
            }
            form.classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-experience").addEventListener("click", function () {
            form.classList.add("hidden");
        });
        document.getElementById("btn-save-experience").addEventListener("click", async function () {
            var wsId = document.getElementById("exp-ws-select").value;
            var scope = document.getElementById("exp-scope").value;
            var title = document.getElementById("exp-title").value.trim();
            var summary = document.getElementById("exp-summary").value.trim();
            var tags = document.getElementById("exp-tags").value.trim();
            if (!title || !summary) {
                showToast("Title and summary are required", "warning");
                return;
            }
            try {
                var body = { scope: scope, title: title, summary: summary };
                if (tags) body.tags = tags.split(",").map(function (t) { return t.trim(); });
                await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/experiences", body);
                showToast("Experience saved successfully", "success");
                form.classList.add("hidden");
                document.getElementById("exp-title").value = "";
                document.getElementById("exp-summary").value = "";
                document.getElementById("exp-tags").value = "";
                loadExperiences(wsId);
            } catch (err) {
                showToast("Failed to save experience: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-experiences").addEventListener("click", function () {
            var wsId = document.getElementById("exp-ws-select").value;
            if (wsId) loadExperiences(wsId);
        });
        document.getElementById("exp-ws-select").addEventListener("change", function () {
            if (this.value) loadExperiences(this.value);
        });
    }

    async function loadExperiences(wsId) {
        if (!wsId) wsId = document.getElementById("exp-ws-select").value;
        if (!wsId) return;
        try {
            const data = await apiCall("GET", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/experiences");
            renderExperiences(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to load experiences: " + err.message, "error");
        }
    }

    function renderExperiences(experiences) {
        var tbody = document.getElementById("experience-tbody");
        if (!experiences.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No experiences found</td></tr>';
            return;
        }
        tbody.innerHTML = experiences.map(function (e) {
            var tags = Array.isArray(e.tags) ? e.tags.join(", ") : (e.tags || "-");
            return "<tr>" +
                "<td>" + escapeHtml(e.id || "-") + "</td>" +
                "<td>" + escapeHtml(e.title || "-") + "</td>" +
                "<td>" + escapeHtml(e.scope || "-") + "</td>" +
                "<td>" + escapeHtml(tags) + "</td>" +
                "<td><button class=\"btn btn-danger btn-sm\" onclick=\"deleteExperience('" + escapeHtml(currentWorkspaceId || "") + "','" + escapeHtml(e.id || "") + "','" + escapeHtml(e.scope || "") + "')\">Delete</button></td>" +
                "</tr>";
        }).join("");
    }

    window.deleteExperience = async function (wsId, expId, scope) {
        if (!confirm("Delete this experience?")) return;
        try {
            await apiCall("DELETE", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/experiences/" + encodeURIComponent(expId), { scope: scope });
            showToast("Experience deleted", "success");
            loadExperiences(wsId);
        } catch (err) {
            showToast("Failed to delete experience: " + err.message, "error");
        }
    };

    // ---- Tool Management -------------------------------------------------

    function setupToolForm() {
        document.getElementById("btn-refresh-tools").addEventListener("click", function () {
            var wsId = document.getElementById("tool-ws-select").value;
            if (wsId) loadTools(wsId);
        });
        document.getElementById("tool-ws-select").addEventListener("change", function () {
            if (this.value) {
                currentWorkspaceId = this.value;
                loadTools(this.value);
            }
        });
        document.getElementById("btn-scan-tools").addEventListener("click", scanTools);
        document.getElementById("btn-add-tool").addEventListener("click", function () {
            var wsId = document.getElementById("tool-ws-select").value;
            if (!wsId) {
                showToast("Select a workspace first", "warning");
                return;
            }
            document.getElementById("tool-scan-results").classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-scan").addEventListener("click", function () {
            document.getElementById("tool-scan-results").classList.add("hidden");
        });
        document.getElementById("btn-add-scanned-tools").addEventListener("click", addScannedTools);
    }

    async function loadTools(wsId) {
        if (!wsId) wsId = document.getElementById("tool-ws-select").value;
        if (!wsId) return;
        try {
            var lang = document.getElementById("tool-lang-select").value;
            var url = "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/tools";
            if (lang) url += "?language=" + encodeURIComponent(lang);
            const data = await apiCall("GET", url);
            renderTools(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to load tools: " + err.message, "error");
        }
    }

    function renderTools(tools) {
        var tbody = document.getElementById("tool-tbody");
        if (!tools.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No tools found</td></tr>';
            return;
        }
        tbody.innerHTML = tools.map(function (t) {
            return "<tr>" +
                "<td>" + escapeHtml(t.name || "-") + "</td>" +
                "<td>" + escapeHtml(t.language || "-") + "</td>" +
                "<td>" + escapeHtml(t.version || "-") + "</td>" +
                "<td><span class=\"status-badge success\">Installed</span></td>" +
                "<td>-</td>" +
                "</tr>";
        }).join("");
    }

    async function scanTools() {
        try {
            var lang = document.getElementById("tool-lang-select").value;
            var url = "/api/v1/tools/scan";
            if (lang) url += "?language=" + encodeURIComponent(lang);
            const data = await apiCall("GET", url);
            renderScanResults(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to scan tools: " + err.message, "error");
        }
    }

    function renderScanResults(tools) {
        var container = document.getElementById("tool-scan-list");
        document.getElementById("tool-scan-results").classList.remove("hidden");
        if (!tools.length) {
            container.innerHTML = '<p class="text-muted">No tools found</p>';
            return;
        }
        container.innerHTML = tools.map(function (t, i) {
            return '<div class="scan-item">' +
                '<input type="checkbox" id="scan-' + i + '" value="' + escapeHtml(t.name || "") + '">' +
                '<label for="scan-' + i + '">' + escapeHtml(t.name || "Unknown") + ' (' + escapeHtml(t.language || "?") + ')</label>' +
                "</div>";
        }).join("");
    }

    async function addScannedTools() {
        var wsId = document.getElementById("tool-ws-select").value;
        if (!wsId) return;
        var checkboxes = document.querySelectorAll("#tool-scan-list input[type=checkbox]:checked");
        var selections = Array.from(checkboxes).map(function (cb) { return cb.value; });
        if (!selections.length) {
            showToast("Select tools to add", "warning");
            return;
        }
        try {
            await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/tools", { selections: selections });
            showToast("Tools added successfully", "success");
            document.getElementById("tool-scan-results").classList.add("hidden");
            loadTools(wsId);
        } catch (err) {
            showToast("Failed to add tools: " + err.message, "error");
        }
    }

    // ---- Experiment Management -------------------------------------------

    function setupExperimentForm() {
        var form = document.getElementById("experiment-form");
        document.getElementById("btn-start-experiment").addEventListener("click", function () {
            form.classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-experiment").addEventListener("click", function () {
            form.classList.add("hidden");
        });
        document.getElementById("btn-save-experiment").addEventListener("click", async function () {
            var protocol = document.getElementById("exp-protocol").value.trim();
            var sessionId = document.getElementById("exp-session-id").value.trim();
            if (!protocol) {
                showToast("Protocol is required", "warning");
                return;
            }
            try {
                var body = { protocol: protocol };
                if (sessionId) body.session_id = sessionId;
                await apiCall("POST", "/api/v1/experiments", body);
                showToast("Experiment started", "success");
                form.classList.add("hidden");
                document.getElementById("exp-protocol").value = "";
                document.getElementById("exp-session-id").value = "";
                loadExperiments();
            } catch (err) {
                showToast("Failed to start experiment: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-experiments").addEventListener("click", loadExperiments);
    }

    async function loadExperiments() {
        try {
            const data = await apiCall("GET", "/api/v1/experiments");
            renderExperiments(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("Failed to load experiments: " + err.message, "error");
        }
    }

    function renderExperiments(experiments) {
        var tbody = document.getElementById("experiment-tbody");
        if (!experiments.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No experiments found</td></tr>';
            return;
        }
        tbody.innerHTML = experiments.map(function (e) {
            return "<tr>" +
                "<td>" + escapeHtml(e.session_id || e.session_file || "-") + "</td>" +
                "<td>" + escapeHtml((e.protocol || "").substring(0, 50)) + "</td>" +
                "<td><span class=\"status-badge " + (e.status === "completed" ? "success" : e.status === "error" ? "error" : "info") + "\">" + escapeHtml(e.status || "active") + "</span></td>" +
                "<td>" + escapeHtml(e.current_step || "-") + "</td>" +
                "<td><button class=\"btn btn-secondary btn-sm\" onclick=\"viewExperiment('" + escapeHtml(e.session_file || e.session_id || "") + "')\">View</button></td>" +
                "</tr>";
        }).join("");
    }

    window.viewExperiment = async function (sessionFile) {
        // This could be expanded to show experiment details
        showToast("Viewing experiment: " + sessionFile, "info");
    };

    // ---- LLM Configuration ----------------------------------------------

    async function loadLLMProviders() {
        try {
            const data = await apiCall("GET", "/api/v1/llm/providers");
            var providers = Array.isArray(data) ? data : [];
            renderLLMProviders(providers);

            // Try to get current provider info
            try {
                const status = await apiCall("GET", "/api/v1/status");
                document.getElementById("llm-current-info").innerHTML =
                    '<div><span class="text-muted">Provider:</span> ' + escapeHtml(status.llm_provider || "N/A") + "</div>";
            } catch (e) {
                document.getElementById("llm-current-info").innerHTML = '<span class="text-muted">Unable to load current provider</span>';
            }
        } catch (err) {
            showToast("Failed to load LLM providers: " + err.message, "error");
        }
    }

    function renderLLMProviders(providers) {
        var tbody = document.getElementById("llm-tbody");
        if (!providers.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No providers configured</td></tr>';
            return;
        }
        tbody.innerHTML = providers.map(function (p) {
            return "<tr>" +
                "<td>" + escapeHtml(p.name || p.provider || "-") + "</td>" +
                "<td>" + escapeHtml(p.model || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.active ? "success" : "info") + "\">" + (p.active ? "Active" : "Available") + "</span></td>" +
                "<td><button class=\"btn btn-primary btn-sm\" onclick=\"switchLLM('" + escapeHtml(p.name || p.provider || "") + "')\">Switch</button></td>" +
                "</tr>";
        }).join("");
    }

    window.switchLLM = async function (provider) {
        try {
            await apiCall("POST", "/api/v1/llm/switch", { provider: provider });
            showToast("Switched to " + provider, "success");
            loadLLMProviders();
        } catch (err) {
            showToast("Failed to switch provider: " + err.message, "error");
        }
    };

    document.getElementById("btn-refresh-llm").addEventListener("click", loadLLMProviders);

    // ---- Permissions -----------------------------------------------------

    async function loadPermissions() {
        try {
            const data = await apiCall("GET", "/api/v1/permissions");
            renderPermissions(data);
        } catch (err) {
            showToast("Failed to load permissions: " + err.message, "error");
        }
    }

    function renderPermissions(data) {
        var modeInfo = document.getElementById("permission-mode-info");
        modeInfo.innerHTML =
            '<div><span class="text-muted">Mode:</span> <strong>' + escapeHtml(data.mode || "unknown") + "</strong></div>" +
            '<div><span class="text-muted">Status:</span> ' + escapeHtml(data.status || "N/A") + "</div>";

        var tbody = document.getElementById("permission-tbody");
        var policies = data.policies || [];
        if (!policies.length) {
            tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No policies configured</td></tr>';
            return;
        }
        tbody.innerHTML = policies.map(function (p) {
            return "<tr>" +
                "<td>" + escapeHtml(p.rule || p.action || "-") + "</td>" +
                "<td>" + escapeHtml(p.scope || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.allowed ? "success" : "warning") + "\">" + (p.allowed ? "Allowed" : "Denied") + "</span></td>" +
                "</tr>";
        }).join("");
    }

    function setupPermissionForm() {
        document.getElementById("btn-set-permission").addEventListener("click", async function () {
            var mode = document.getElementById("permission-mode-select").value;
            var confirmFull = document.getElementById("permission-confirm-full").checked;
            try {
                await apiCall("POST", "/api/v1/permissions/mode", { mode: mode, confirm_full: confirmFull });
                showToast("Permission mode updated", "success");
                loadPermissions();
            } catch (err) {
                showToast("Failed to set permission mode: " + err.message, "error");
            }
        });
        document.getElementById("btn-authorize-path").addEventListener("click", async function () {
            var path = document.getElementById("permission-path").value.trim();
            if (!path) {
                showToast("Path is required", "warning");
                return;
            }
            try {
                await apiCall("POST", "/api/v1/permissions/authorize", { path: path });
                showToast("Path authorized", "success");
                document.getElementById("permission-path").value = "";
                loadPermissions();
            } catch (err) {
                showToast("Failed to authorize path: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-permissions").addEventListener("click", loadPermissions);
    }

    // ---- Log Viewer ------------------------------------------------------

    async function loadLogs() {
        try {
            const data = await apiCall("GET", "/api/v1/logs");
            var logs = Array.isArray(data) ? data : [];
            var sel = document.getElementById("log-select");
            var current = sel.value;
            sel.innerHTML = '<option value="">Select Log</option>';
            logs.forEach(function (l) {
                var opt = document.createElement("option");
                opt.value = l.name || l.id || l;
                opt.textContent = l.name || l.id || l;
                sel.appendChild(opt);
            });
            if (current) sel.value = current;
        } catch (err) {
            showToast("Failed to load logs: " + err.message, "error");
        }
    }

    function setupLogForm() {
        document.getElementById("log-select").addEventListener("change", async function () {
            var name = this.value;
            if (!name) return;
            try {
                const data = await apiCall("GET", "/api/v1/logs/" + encodeURIComponent(name));
                document.getElementById("log-content").textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
            } catch (err) {
                document.getElementById("log-content").textContent = "Error loading log: " + err.message;
            }
        });
        document.getElementById("btn-refresh-logs").addEventListener("click", loadLogs);
        document.getElementById("btn-write-log").addEventListener("click", function () {
            document.getElementById("log-write-form").classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-log").addEventListener("click", function () {
            document.getElementById("log-write-form").classList.add("hidden");
        });
        document.getElementById("btn-save-log").addEventListener("click", async function () {
            var message = document.getElementById("log-message").value.trim();
            var sessionId = document.getElementById("log-session-id").value.trim();
            if (!message) {
                showToast("Message is required", "warning");
                return;
            }
            try {
                var body = { message: message };
                if (sessionId) body.session_id = sessionId;
                await apiCall("POST", "/api/v1/logs", body);
                showToast("Log entry written", "success");
                document.getElementById("log-write-form").classList.add("hidden");
                document.getElementById("log-message").value = "";
                document.getElementById("log-session-id").value = "";
            } catch (err) {
                showToast("Failed to write log: " + err.message, "error");
            }
        });
    }

    // ---- WebSocket -------------------------------------------------------

    function connect() {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        var proto = location.protocol === "https:" ? "wss:" : "ws:";
        var url = proto + "//" + location.host + "/ws/chat";
        ws = new WebSocket(url);

        ws.onopen = function () {
            setConnected(true);
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        ws.onclose = function () {
            setConnected(false);
            scheduleReconnect();
        };

        ws.onerror = function () {
            setConnected(false);
        };

        ws.onmessage = function (event) {
            var data;
            try {
                data = JSON.parse(event.data);
            } catch (_) {
                addMessage("assistant", event.data);
                return;
            }

            switch (data.type) {
                case "progress":
                    addMessage("progress", data.data.message || JSON.stringify(data.data), "progress");
                    break;

                case "result": {
                    var result = data.data;
                    var text = "";
                    if (result.output && typeof result.output === "object") {
                        text = result.output.message || result.output.text || JSON.stringify(result.output, null, 2);
                    } else if (result.output) {
                        text = String(result.output);
                    } else if (result.error) {
                        text = "Error: " + String(result.error);
                        addMessage("assistant", text, "error");
                        return;
                    } else {
                        text = JSON.stringify(result, null, 2);
                    }
                    addMessage("assistant", text);
                    break;
                }

                case "error":
                    addMessage("system", data.content || "Unknown error", "error");
                    break;

                default:
                    addMessage("assistant", JSON.stringify(data, null, 2));
            }
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connect();
        }, RECONNECT_DELAY);
    }

    // ---- Send message ----------------------------------------------------

    function sendMessage(text) {
        if (!text.trim()) return;

        addMessage("user", text);

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message: text }));
        } else {
            fetch("/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var out = data.output
                        ? (typeof data.output === "object" ? (data.output.message || JSON.stringify(data.output, null, 2)) : String(data.output))
                        : JSON.stringify(data, null, 2);
                    addMessage("assistant", out);
                })
                .catch(function (err) {
                    addMessage("system", "Request failed: " + err.message, "error");
                });
        }
    }

    // ---- Event listeners -------------------------------------------------

    chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var text = chatInput.value;
        chatInput.value = "";
        sendMessage(text);
    });

    chatInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // ---- Smooth scrolling for anchor links --------------------------------

    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener("click", function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute("href"));
            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }
        });
    });

    // ---- Toast dismiss on click ------------------------------------------

    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("toast")) {
            e.target.style.animation = "toastOut 0.3s ease forwards";
            setTimeout(function () {
                e.target.remove();
            }, 300);
        }
    });

    // ---- Keyboard shortcuts ----------------------------------------------

    document.addEventListener("keydown", function (e) {
        // Ctrl/Cmd + K to focus search (if exists)
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            var searchInput = document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to close modals
        if (e.key === "Escape") {
            var modals = document.querySelectorAll(".modal.active");
            modals.forEach(function (modal) {
                modal.classList.remove("active");
            });
        }
    });

    // ---- Init ------------------------------------------------------------

    initTabs();
    setupWorkspaceForm();
    setupPaperForm();
    setupExperienceForm();
    setupToolForm();
    setupExperimentForm();
    setupPermissionForm();
    setupLogForm();
    fetchStatus();
    connect();
})();

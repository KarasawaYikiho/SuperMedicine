/**
     * SuperMedicine 网页界面 — 客户端逻辑
     *
     * 管理 WebSocket 连接、页面导航、API 调用、数据渲染和实时更新。
 */

(function () {
    "use strict";

    // ---- DOM 引用 ---------------------------------------------------------

    const messagesEl = document.getElementById("messages");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const statusIndicator = document.getElementById("status-indicator");
    const statusText = document.getElementById("status-text");
    const projectStatusEl = document.getElementById("project-status");
    const hamburgerBtn = document.getElementById("hamburger-btn");
    const drawerMenu = document.getElementById("drawer-menu");
    const drawerOverlay = document.getElementById("drawer-overlay");
    const drawerCloseBtn = document.getElementById("drawer-close-btn");
    const chatWsSelect = document.getElementById("chat-ws-select");
    const webAuthTokenInput = document.getElementById("web-auth-token");
    const webAuthSave = document.getElementById("web-auth-save");

    // ---- 状态 -------------------------------------------------------------

    let ws = null;
    let reconnectTimer = null;
    const RECONNECT_DELAY = 3000;
    let currentWorkspaceId = null;
    let chatProcessing = false;
    let webAuthToken = sessionStorage.getItem("supermedicine.webAuthToken") || "";

    // ---- 辅助函数 ---------------------------------------------------------

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeAttribute(text) {
        return String(text == null ? "" : text)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
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

    function openAppDialog(options) {
        const dialog = document.createElement("dialog");
        dialog.className = "app-dialog";
        dialog.setAttribute("aria-labelledby", "app-dialog-title");

        const panel = document.createElement("div");
        panel.className = "app-dialog-panel";
        const title = document.createElement("h3");
        title.id = "app-dialog-title";
        title.textContent = options.title || "SuperMedicine";
        const body = document.createElement(options.preformatted ? "pre" : "p");
        body.className = "app-dialog-body";
        body.textContent = options.message || "";
        const actions = document.createElement("div");
        actions.className = "app-dialog-actions";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "btn btn-secondary";
        cancel.textContent = options.cancelLabel || "取消";
        const accept = document.createElement("button");
        accept.type = "button";
        accept.className = options.danger ? "btn btn-danger" : "btn btn-primary";
        accept.textContent = options.acceptLabel || "确定";
        actions.append(cancel, accept);
        panel.append(title, body, actions);
        dialog.appendChild(panel);
        document.body.appendChild(dialog);

        return new Promise(function (resolve) {
            function finish(value) {
                dialog.close();
                dialog.remove();
                resolve(value);
            }
            cancel.addEventListener("click", function () { finish(false); });
            accept.addEventListener("click", function () { finish(true); });
            dialog.addEventListener("cancel", function (event) {
                event.preventDefault();
                finish(false);
            });
            dialog.addEventListener("click", function (event) {
                if (event.target === dialog) finish(false);
            });
            dialog.showModal();
            (options.focusCancel ? cancel : accept).focus();
        });
    }

    function requestConfirmation(message, title) {
        return openAppDialog({
            title: title || "确认操作",
            message: message,
            danger: true,
            focusCancel: true
        });
    }

    function showJsonDetails(title, data) {
        return openAppDialog({
            title: title,
            message: JSON.stringify(data, null, 2),
            preformatted: true,
            cancelLabel: "关闭",
            acceptLabel: "关闭"
        });
    }

    function addMessage(role, content, extraClass) {
        const div = document.createElement("div");
        let cls = "message " + role;
        if (extraClass) cls += " " + extraClass;
        div.className = cls;

        const roleLabel = document.createElement("div");
        roleLabel.className = "role";
        roleLabel.textContent = role === "user" ? "你" : role === "assistant" ? "SuperMedicine" : role;
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
        statusText.textContent = connected ? "已连接" : "已断开";
    }

    function setChatProcessing(active) {
        chatProcessing = Boolean(active);
        if (chatInput) chatInput.disabled = chatProcessing;
        if (sendBtn) sendBtn.disabled = chatProcessing;
        if (chatWsSelect) chatWsSelect.disabled = chatProcessing;
    }

    function selectedChatWorkspace() {
        return chatWsSelect ? (chatWsSelect.value || null) : null;
    }

    function localizeStatus(value) {
        var statusMap = {
            completed: "已完成",
            complete: "已完成",
            success: "成功",
            error: "错误",
            failed: "失败",
            pending: "待处理",
            running: "运行中",
            active: "活跃",
            available: "可用",
            configured: "已配置",
            unknown: "未知",
            sandbox: "沙盒",
            conservative: "保守",
            full: "完全",
            general: "通用",
            workspace: "工作区",
            global: "全局"
        };
        var key = String(value || "").toLowerCase();
        return statusMap[key] || value || "未知";
    }

    function syncWorkspaceSelectors(workspaceId) {
        var normalized = workspaceId || "";
        ["chat-ws-select", "paper-ws-select", "exp-ws-select", "tool-ws-select", "dialog-ws-select"].forEach(function (selId) {
            var sel = document.getElementById(selId);
            if (sel) sel.value = normalized;
        });
        currentWorkspaceId = normalized || null;
    }

    function refreshWorkspaceBoundViews(workspaceId) {
        var normalized = workspaceId || "";
        if (!normalized) return;
        var activeTab = document.querySelector(".tab-content.active");
        if (activeTab && activeTab.id === "tab-tools") loadTools(normalized);
        if (activeTab && activeTab.id === "tab-papers") loadPapers(normalized);
        if (activeTab && activeTab.id === "tab-experiences") loadExperiences(normalized);
        if (activeTab && activeTab.id === "tab-dialog") loadDialogHistory(normalized);
    }

    function handleWorkspaceSelection(workspaceId) {
        syncWorkspaceSelectors(workspaceId);
        refreshWorkspaceBoundViews(workspaceId);
    }

    // ---- 抽屉菜单 ---------------------------------------------------------

    function openDrawer() {
        drawerMenu.classList.add("open");
        drawerOverlay.classList.add("active");
        hamburgerBtn.setAttribute("aria-expanded", "true");
        drawerMenu.setAttribute("aria-hidden", "false");
    }

    function closeDrawer() {
        drawerMenu.classList.remove("open");
        drawerOverlay.classList.remove("active");
        hamburgerBtn.setAttribute("aria-expanded", "false");
        drawerMenu.setAttribute("aria-hidden", "true");
    }

    function toggleDrawer() {
        if (drawerMenu.classList.contains("open")) {
            closeDrawer();
        } else {
            openDrawer();
        }
    }

    hamburgerBtn.addEventListener("click", toggleDrawer);
    drawerCloseBtn.addEventListener("click", closeDrawer);
    drawerOverlay.addEventListener("click", closeDrawer);

    // ---- API 辅助 ---------------------------------------------------------

    function authorizedFetch(url, opts) {
        opts = opts || {};
        opts.headers = Object.assign({}, opts.headers || {});
        if (webAuthToken) opts.headers.Authorization = "Bearer " + webAuthToken;
        return fetch(url, opts);
    }

    async function apiCall(method, url, body) {
        const opts = {
            method: method,
            headers: { "Content-Type": "application/json" },
        };
        if (body) opts.body = JSON.stringify(body);

        const resp = await authorizedFetch(url, opts);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
    }

    // ---- 页面导航 ---------------------------------------------------------

    function initTabs() {
        var tabBtns = document.querySelectorAll(".tab-btn");
        tabBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var tabId = this.getAttribute("data-tab");

                // 更新按钮状态
                tabBtns.forEach(function (b) {
                    b.classList.remove("active");
                });
                this.classList.add("active");

                // 更新内容可见性
                document.querySelectorAll(".tab-content").forEach(function (c) {
                    c.classList.remove("active");
                });
                document.getElementById("tab-" + tabId).classList.add("active");

                // 选择后关闭抽屉菜单
                closeDrawer();

                // 加载当前页面数据
                loadTabData(tabId);
            });
        });
    }

    function loadTabData(tabId) {
        switch (tabId) {
            case "dashboard":
                fetchStatus();
                break;
            case "chat":
                loadChatWorkspaceSelector();
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
            case "dialog":
                loadWorkspaceSelectors().then(function () {
                    var wsId = document.getElementById("dialog-ws-select").value;
                    if (wsId) loadDialogHistory(wsId);
                });
                break;
            case "llm":
                loadLLMProviders();
                break;
            case "permissions":
                loadPermissions();
                loadMultiAgent();
                break;
            case "logs":
                loadLogs();
                break;
            case "self-evolution":
                loadSelfEvolution();
                break;
            case "diagnose":
                loadDiagnostics();
                break;
        }
    }

    // ---- 状态获取 ---------------------------------------------------------

    async function fetchStatus() {
        try {
            const data = await apiCall("GET", "/api/v1/status");

            projectStatusEl.innerHTML =
                '<div class="status-card">' +
                '<div class="label">版本</div>' +
                '<div class="value">' + escapeHtml(data.version || "未知") + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">配置</div>' +
                '<div class="value">' + (data.config_initialized ? "已初始化" : "未初始化") + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">插件</div>' +
                '<div class="value">' + (data.plugin_count ?? 0) + "</div>" +
                "</div>" +
                '<div class="status-card">' +
                '<div class="label">LLM 提供商</div>' +
                '<div class="value">' + escapeHtml(data.llm_provider || "无") + "</div>" +
                "</div>";
        } catch (err) {
            projectStatusEl.innerHTML =
                '<div style="color:var(--color-error)">加载状态失败: ' +
                escapeHtml(err.message) + "</div>";
        }
    }

    // ---- 工作区管理 -------------------------------------------------------

    async function loadWorkspaces() {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces");
            renderWorkspaces(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("加载工作区失败: " + err.message, "error");
        }
    }

    function renderWorkspaces(workspaces) {
        var tbody = document.getElementById("workspace-tbody");
        if (!workspaces.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">未找到工作区</td></tr>';
            return;
        }
        tbody.innerHTML = workspaces.map(function (ws) {
            return "<tr>" +
                "<td>" + escapeHtml(ws.id || ws.name || "-") + "</td>" +
                "<td>" + escapeHtml(ws.name || ws.id || "-") + "</td>" +
                "<td><span class=\"status-badge success\">活跃</span></td>" +
                "<td><button class=\"btn btn-danger btn-sm\" data-action=\"delete-workspace\" data-id=\"" + escapeAttribute(ws.id || ws.name) + "\">删除</button></td>" +
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
                showToast("工作区ID为必填项", "warning");
                return;
            }
            try {
                await apiCall("POST", "/api/v1/workspaces", { id: id, name: name || undefined });
                showToast("工作区创建成功", "success");
                form.classList.add("hidden");
                document.getElementById("ws-id").value = "";
                document.getElementById("ws-name").value = "";
                loadWorkspaces();
                loadWorkspaceSelectors().then(function () { handleWorkspaceSelection(id); });
            } catch (err) {
                showToast("创建工作区失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-workspaces").addEventListener("click", loadWorkspaces);
    }

    async function deleteWorkspace(id) {
        if (!await requestConfirmation("确定要删除工作区 '" + id + "' 吗？", "删除工作区")) return;
        try {
            await apiCall("DELETE", "/api/v1/workspaces/" + encodeURIComponent(id), { confirm: id });
            showToast("工作区已删除", "success");
            loadWorkspaces();
            if (currentWorkspaceId === id || selectedChatWorkspace() === id) {
                handleWorkspaceSelection("");
            }
            loadWorkspaceSelectors();
        } catch (err) {
            showToast("删除工作区失败: " + err.message, "error");
        }
    }

    // ---- 工作区选择器 -----------------------------------------------------

    async function loadWorkspaceSelectors() {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces");
            var workspaces = Array.isArray(data) ? data : [];
            var selectors = ["paper-ws-select", "exp-ws-select", "tool-ws-select", "chat-ws-select", "dialog-ws-select"];
            selectors.forEach(function (selId) {
                var sel = document.getElementById(selId);
                if (!sel) return;
                var current = sel.value || currentWorkspaceId || "";
                var defaultOption = selId === "chat-ws-select"
                    ? '<option value="">无工作区（全局）</option>'
                    : '<option value="">选择工作区</option>';
                sel.innerHTML = defaultOption;
                workspaces.forEach(function (ws) {
                    var opt = document.createElement("option");
                    opt.value = ws.id || ws.name;
                    opt.textContent = ws.name || ws.id;
                    sel.appendChild(opt);
                });
                if (current) sel.value = current;
            });
        } catch (err) {
            // 选择器加载失败时保持静默
        }
    }

    // ---- 对话工作区选择器 -------------------------------------------------

    async function loadChatWorkspaceSelector() {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces");
            var workspaces = Array.isArray(data) ? data : [];
            var current = selectedChatWorkspace() || currentWorkspaceId || "";
            chatWsSelect.innerHTML = '<option value="">无工作区（全局）</option>';
            workspaces.forEach(function (ws) {
                var opt = document.createElement("option");
                opt.value = ws.id || ws.name;
                opt.textContent = ws.name || ws.id;
                chatWsSelect.appendChild(opt);
            });
            if (current) chatWsSelect.value = current;
            currentWorkspaceId = chatWsSelect.value || null;
        } catch (err) {
            // 加载失败时保持静默
        }
    }

    // ---- 论文管理 ---------------------------------------------------------

    function setupPaperForm() {
        var form = document.getElementById("paper-form");
        document.getElementById("btn-add-paper").addEventListener("click", function () {
            if (!document.getElementById("paper-ws-select").value) {
                showToast("请先选择工作区", "warning");
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
                showToast("源路径为必填项", "warning");
                return;
            }
            try {
                var body = { source_path: source, enrich: enrich };
                if (title) body.metadata = { title: title };
                await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers", body);
                showToast("论文导入成功", "success");
                form.classList.add("hidden");
                document.getElementById("paper-source").value = "";
                document.getElementById("paper-title").value = "";
                document.getElementById("paper-enrich").checked = false;
                loadPapers(wsId);
            } catch (err) {
                showToast("导入论文失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-papers").addEventListener("click", function () {
            var wsId = document.getElementById("paper-ws-select").value;
            if (wsId) loadPapers(wsId);
        });
        document.getElementById("paper-ws-select").addEventListener("change", function () {
            handleWorkspaceSelection(this.value);
            if (this.value) loadPapers(this.value);
        });
    }

    async function loadPapers(wsId) {
        try {
            const data = await apiCall("GET", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers");
            renderPapers(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("加载论文失败: " + err.message, "error");
        }
    }

    function renderPapers(papers) {
        var tbody = document.getElementById("paper-tbody");
        if (!papers.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">未找到论文</td></tr>';
            return;
        }
        tbody.innerHTML = papers.map(function (p) {
            return "<tr>" +
                "<td>" + escapeHtml(p.id || "-") + "</td>" +
                "<td>" + escapeHtml(p.title || p.metadata?.title || "-") + "</td>" +
                "<td>" + escapeHtml(p.authors || p.metadata?.authors || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.enriched ? "success" : "info") + "\">" + (p.enriched ? "已充实" : "已导入") + "</span></td>" +
                "<td><button class=\"btn btn-secondary btn-sm\" data-action=\"enrich-paper\" data-workspace=\"" + escapeAttribute(currentWorkspaceId || "") + "\" data-id=\"" + escapeAttribute(p.id || "") + "\">充实</button></td>" +
                "</tr>";
        }).join("");
    }

    async function enrichPaper(wsId, paperId) {
        if (!wsId || !paperId) return;
        try {
            await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/papers/" + encodeURIComponent(paperId) + "/enrich", { confirm_enrich: true });
            showToast("论文充实已启动", "info");
            loadPapers(wsId);
        } catch (err) {
            showToast("充实论文失败: " + err.message, "error");
        }
    }

    // ---- 经验管理 ---------------------------------------------------------

    function setupExperienceForm() {
        var form = document.getElementById("experience-form");
        document.getElementById("btn-add-experience").addEventListener("click", function () {
            if (!document.getElementById("exp-ws-select").value) {
                showToast("请先选择工作区", "warning");
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
                showToast("标题和摘要为必填项", "warning");
                return;
            }
            try {
                var body = { scope: scope, title: title, summary: summary };
                if (tags) body.tags = tags.split(",").map(function (t) { return t.trim(); });
                await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/experiences", body);
                showToast("经验保存成功", "success");
                form.classList.add("hidden");
                document.getElementById("exp-title").value = "";
                document.getElementById("exp-summary").value = "";
                document.getElementById("exp-tags").value = "";
                loadExperiences(wsId);
            } catch (err) {
                showToast("保存经验失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-experiences").addEventListener("click", function () {
            var wsId = document.getElementById("exp-ws-select").value;
            if (wsId) loadExperiences(wsId);
        });
        document.getElementById("exp-ws-select").addEventListener("change", function () {
            handleWorkspaceSelection(this.value);
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
            showToast("加载经验失败: " + err.message, "error");
        }
    }

    function renderExperiences(experiences) {
        var tbody = document.getElementById("experience-tbody");
        if (!experiences.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">未找到经验</td></tr>';
            return;
        }
        tbody.innerHTML = experiences.map(function (e) {
            var tags = Array.isArray(e.tags) ? e.tags.join(", ") : (e.tags || "-");
            return "<tr>" +
                "<td>" + escapeHtml(e.id || "-") + "</td>" +
                "<td>" + escapeHtml(e.title || "-") + "</td>" +
                "<td>" + escapeHtml(localizeStatus(e.scope || "-")) + "</td>" +
                "<td>" + escapeHtml(tags) + "</td>" +
                "<td><button class=\"btn btn-danger btn-sm\" data-action=\"delete-experience\" data-workspace=\"" + escapeAttribute(currentWorkspaceId || "") + "\" data-id=\"" + escapeAttribute(e.id || "") + "\" data-scope=\"" + escapeAttribute(e.scope || "") + "\">删除</button></td>" +
                "</tr>";
        }).join("");
    }

    async function deleteExperience(wsId, expId, scope) {
        if (!await requestConfirmation("确定要删除此经验吗？", "删除经验")) return;
        try {
            await apiCall("DELETE", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/experiences/" + encodeURIComponent(expId), { scope: scope });
            showToast("经验已删除", "success");
            loadExperiences(wsId);
        } catch (err) {
            showToast("删除经验失败: " + err.message, "error");
        }
    }

    // ---- 工具管理 ---------------------------------------------------------

    function setupToolForm() {
        document.getElementById("btn-refresh-tools").addEventListener("click", function () {
            var wsId = document.getElementById("tool-ws-select").value;
            if (wsId) loadTools(wsId);
        });
        document.getElementById("tool-ws-select").addEventListener("change", function () {
            handleWorkspaceSelection(this.value);
            if (this.value) {
                loadTools(this.value);
            }
        });
        document.getElementById("btn-scan-tools").addEventListener("click", scanTools);
        document.getElementById("btn-add-tool").addEventListener("click", function () {
            var wsId = document.getElementById("tool-ws-select").value;
            if (!wsId) {
                showToast("请先选择工作区", "warning");
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
            renderTools(flattenToolGroups(data));
        } catch (err) {
            showToast("加载工具失败: " + err.message, "error");
        }
    }

    function flattenToolGroups(data) {
        if (Array.isArray(data)) return data;
        if (!data || typeof data !== "object") return [];
        return Object.keys(data).reduce(function (items, language) {
            var group = data[language];
            if (!Array.isArray(group)) return items;
            group.forEach(function (tool) {
                if (!tool || typeof tool !== "object") return;
                if (!tool.language) tool.language = language;
                items.push(tool);
            });
            return items;
        }, []);
    }

    function renderTools(tools) {
        var tbody = document.getElementById("tool-tbody");
        if (!tools.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">未找到工具</td></tr>';
            return;
        }
        tbody.innerHTML = tools.map(function (t) {
            return "<tr>" +
                "<td>" + escapeHtml(t.name || "-") + "</td>" +
                "<td>" + escapeHtml(t.language || "-") + "</td>" +
                "<td>" + escapeHtml(t.version || "-") + "</td>" +
                "<td><span class=\"status-badge success\">已安装</span></td>" +
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
            renderScanResults(flattenToolGroups(data));
        } catch (err) {
            showToast("扫描工具失败: " + err.message, "error");
        }
    }

    function renderScanResults(tools) {
        var container = document.getElementById("tool-scan-list");
        document.getElementById("tool-scan-results").classList.remove("hidden");
        if (!tools.length) {
            container.innerHTML = '<p class="text-muted">未找到工具</p>';
            return;
        }
        container.innerHTML = tools.map(function (t, i) {
            var selection = t.index ? String(t.index) : ((t.language || "") + "/" + (t.id || ""));
            var label = (t.name || "未知") + " [" + (t.language + "/" + t.id) + "]";
            return '<div class="scan-item">' +
                '<input type="checkbox" id="scan-' + i + '" value="' + escapeHtml(selection) + '">' +
                '<label for="scan-' + i + '">' + escapeHtml(label) + ' #' + escapeHtml(t.index || "-") + '</label>' +
                "</div>";
        }).join("");
    }

    async function addScannedTools() {
        var wsId = document.getElementById("tool-ws-select").value;
        if (!wsId) return;
        var checkboxes = document.querySelectorAll("#tool-scan-list input[type=checkbox]:checked");
        var selections = Array.from(checkboxes).map(function (cb) { return cb.value; });
        if (!selections.length) {
            showToast("请选择要添加的工具", "warning");
            return;
        }
        try {
            await apiCall("POST", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/tools", { selections: selections });
            showToast("工具添加成功", "success");
            document.getElementById("tool-scan-results").classList.add("hidden");
            loadTools(wsId);
        } catch (err) {
            showToast("添加工具失败: " + err.message, "error");
        }
    }

    // ---- 实验管理 ---------------------------------------------------------

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
                showToast("实验方案为必填项", "warning");
                return;
            }
            try {
                var body = { protocol: protocol };
                if (sessionId) body.session_id = sessionId;
                var started = await apiCall("POST", "/api/v1/experiments", body);
                showExperimentDetails(started);
                showToast("实验已启动", "success");
                form.classList.add("hidden");
                document.getElementById("exp-protocol").value = "";
                document.getElementById("exp-session-id").value = "";
                loadExperiments();
            } catch (err) {
                showToast("启动实验失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-experiments").addEventListener("click", loadExperiments);
    }

    async function loadExperiments() {
        try {
            const data = await apiCall("GET", "/api/v1/experiments");
            renderExperiments(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("加载实验失败: " + err.message, "error");
        }
    }

    function renderExperiments(experiments) {
        var tbody = document.getElementById("experiment-tbody");
        if (!experiments.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">未找到实验</td></tr>';
            return;
        }
        tbody.innerHTML = experiments.map(function (e) {
            return "<tr>" +
                "<td>" + escapeHtml(e.session_id || e.session_file || "-") + "</td>" +
                "<td>" + escapeHtml((e.protocol || "").substring(0, 50)) + "</td>" +
                "<td><span class=\"status-badge " + (e.status === "completed" ? "success" : e.status === "error" ? "error" : "info") + "\">" + escapeHtml(localizeStatus(e.status || "running")) + "</span></td>" +
                "<td>" + escapeHtml(e.current_step || "-") + "</td>" +
                "<td><button class=\"btn btn-secondary btn-sm\" data-action=\"view-experiment\" data-id=\"" + escapeAttribute(e.session_file || e.session_id || "") + "\">查看</button></td>" +
                "</tr>";
        }).join("");
    }

    function showExperimentDetails(data) {
        showJsonDetails("实验详情", data);
    }

    async function viewExperiment(sessionFile) {
        if (!sessionFile) return;
        try {
            var data = await apiCall(
                "GET",
                "/api/v1/experiments?session_file=" + encodeURIComponent(sessionFile)
            );
            showExperimentDetails(data);
        } catch (err) {
            showToast("加载实验详情失败: " + err.message, "error");
        }
    }

    // ---- 对话历史 ---------------------------------------------------------

    function setupDialogHistoryForm() {
        var refreshBtn = document.getElementById("btn-refresh-dialog");
        if (refreshBtn) refreshBtn.addEventListener("click", function () {
            var wsId = document.getElementById("dialog-ws-select").value;
            if (wsId) loadDialogHistory(wsId);
        });
        var wsSelect = document.getElementById("dialog-ws-select");
        if (wsSelect) wsSelect.addEventListener("change", function () {
            handleWorkspaceSelection(this.value);
            if (this.value) loadDialogHistory(this.value);
        });
    }

    async function loadDialogHistory(wsId) {
        var tbody = document.getElementById("dialog-tbody");
        if (!wsId) {
            if (tbody) tbody.innerHTML = '<tr><td colspan="3" class="empty-state">选择工作区以查看对话历史</td></tr>';
            return;
        }
        try {
            var data = await apiCall("GET", "/api/v1/workspaces/" + encodeURIComponent(wsId) + "/dialog-history");
            renderDialogHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("加载对话历史失败: " + err.message, "error");
        }
    }

    function renderDialogHistory(events) {
        var tbody = document.getElementById("dialog-tbody");
        if (!tbody) return;
        if (!events.length) {
            tbody.innerHTML = '<tr><td colspan="3" class="empty-state">暂无对话历史</td></tr>';
            return;
        }
        tbody.innerHTML = events.map(function (event) {
            return "<tr>" +
                "<td>" + escapeHtml(event.event || "-") + "</td>" +
                "<td>" + escapeHtml(event.summary || "-") + "</td>" +
                "<td>" + escapeHtml(event.created_at || "-") + "</td>" +
                "</tr>";
        }).join("");
    }

    // ---- LLM 配置 ---------------------------------------------------------

    async function loadLLMProviders() {
        try {
            const data = await apiCall("GET", "/api/v1/llm/providers");
            var providers = Array.isArray(data) ? data : (data.providers || []);
            renderLLMProviders(providers);

            // 同步当前提供商信息
            try {
                const status = await apiCall("GET", "/api/v1/status");
                document.getElementById("llm-current-info").innerHTML =
                    '<div><span class="text-muted">提供商：</span> ' + escapeHtml(status.llm_provider || data.current_provider || "无") + "</div>" +
                    '<div><span class="text-muted">上一提供商：</span> ' + escapeHtml(data.last_provider || "无") + "</div>";
            } catch (e) {
                document.getElementById("llm-current-info").innerHTML = '<span class="text-muted">无法加载当前提供商</span>';
            }
        } catch (err) {
            showToast("加载 LLM 提供商失败: " + err.message, "error");
        }
    }

    function renderLLMProviders(providers) {
        var tbody = document.getElementById("llm-tbody");
        if (!providers.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">未配置提供商</td></tr>';
            return;
        }
        tbody.innerHTML = providers.map(function (p) {
            var providerName = p.name || p.provider || "";
            return "<tr>" +
                "<td>" + escapeHtml(providerName || "-") + "</td>" +
                "<td>" + escapeHtml(p.model || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.active || p.current ? "success" : "info") + "\">" + (p.active || p.current ? "当前" : "可用") + "</span></td>" +
                "<td>" +
                "<button class=\"btn btn-secondary btn-sm\" data-action=\"show-llm\" data-provider=\"" + escapeAttribute(providerName) + "\">详情</button> " +
                "<button class=\"btn btn-primary btn-sm\" data-action=\"switch-llm\" data-provider=\"" + escapeAttribute(providerName) + "\">切换</button>" +
                "</td>" +
                "</tr>";
        }).join("");
    }

    async function showLLM(provider) {
        if (!provider) return;
        try {
            var data = await apiCall("GET", "/api/v1/llm/providers/" + encodeURIComponent(provider));
            showJsonDetails("LLM 提供商详情", data);
        } catch (err) {
            showToast("加载提供商详情失败: " + err.message, "error");
        }
    }

    async function switchLLM(provider) {
        try {
            await apiCall("POST", "/api/v1/llm/switch", { provider: provider });
            showToast("已切换至 " + provider, "success");
            loadLLMProviders();
        } catch (err) {
            showToast("切换提供商失败: " + err.message, "error");
        }
    }

    function setupLLMForm() {
        document.getElementById("btn-refresh-llm").addEventListener("click", loadLLMProviders);
        var form = document.getElementById("llm-form");
        document.getElementById("btn-add-llm").addEventListener("click", function () {
            form.classList.toggle("hidden");
        });
        document.getElementById("btn-cancel-llm").addEventListener("click", function () {
            form.classList.add("hidden");
        });
        document.getElementById("btn-save-llm").addEventListener("click", async function () {
            var provider = document.getElementById("llm-provider-name").value.trim();
            if (!provider) {
                showToast("提供商名称为必填项", "warning");
                return;
            }
            var timeoutRaw = document.getElementById("llm-timeout").value.trim();
            var body = {
                provider: provider,
                api_format: document.getElementById("llm-api-format").value.trim() || undefined,
                base_url: document.getElementById("llm-base-url").value.trim() || undefined,
                model: document.getElementById("llm-model").value.trim() || undefined,
                api_key_env: document.getElementById("llm-api-key-env").value.trim() || undefined,
                api_key: document.getElementById("llm-api-key").value.trim() || undefined,
                set_current: document.getElementById("llm-set-current").checked
            };
            if (timeoutRaw) body.timeout = Number(timeoutRaw);
            try {
                await apiCall("POST", "/api/v1/llm/providers", body);
                showToast("LLM 提供商已保存", "success");
                form.classList.add("hidden");
                ["llm-provider-name", "llm-api-format", "llm-base-url", "llm-model", "llm-api-key-env", "llm-api-key", "llm-timeout"].forEach(function (id) {
                    document.getElementById(id).value = "";
                });
                document.getElementById("llm-set-current").checked = false;
                loadLLMProviders();
            } catch (err) {
                showToast("保存 LLM 提供商失败: " + err.message, "error");
            }
        });
    }

    // ---- 权限 -------------------------------------------------------------

    async function loadPermissions() {
        try {
            const data = await apiCall("GET", "/api/v1/permissions");
            renderPermissions(data);
        } catch (err) {
            showToast("加载权限失败: " + err.message, "error");
        }
    }

    async function loadMultiAgent() {
        try {
            const data = await apiCall("GET", "/api/v1/multi-agent");
            document.getElementById("multi-agent-enabled").value = String(Boolean(data.enabled));
            document.getElementById("multi-agent-info").textContent = data.enabled
                ? "已启用：任务自动经过完整四角色流程。"
                : "已关闭：任务使用轻量单流程。";
        } catch (err) {
            showToast("加载 Multi-Agent 设置失败: " + err.message, "error");
        }
    }

    function renderPermissions(data) {
        var modeInfo = document.getElementById("permission-mode-info");
        modeInfo.innerHTML =
            '<div><span class="text-muted">模式:</span> <strong>' + escapeHtml(data.mode || "未知") + "</strong></div>" +
            '<div><span class="text-muted">状态:</span> ' + escapeHtml(data.status || "无") + "</div>";

        var tbody = document.getElementById("permission-tbody");
        var policies = data.policies || [];
        if (!policies.length) {
            tbody.innerHTML = '<tr><td colspan="3" class="empty-state">未配置策略</td></tr>';
            return;
        }
        tbody.innerHTML = policies.map(function (p) {
            return "<tr>" +
                "<td>" + escapeHtml(p.rule || p.action || "-") + "</td>" +
                "<td>" + escapeHtml(p.scope || "-") + "</td>" +
                "<td><span class=\"status-badge " + (p.allowed ? "success" : "warning") + "\">" + (p.allowed ? "允许" : "拒绝") + "</span></td>" +
                "</tr>";
        }).join("");
    }

    function setupPermissionForm() {
        document.getElementById("btn-set-multi-agent").addEventListener("click", async function () {
            var enabled = document.getElementById("multi-agent-enabled").value === "true";
            try {
                await apiCall("POST", "/api/v1/multi-agent", { enabled: enabled });
                showToast(enabled ? "完整四角色流程已启用" : "已切换为轻量单流程", "success");
                loadMultiAgent();
            } catch (err) {
                showToast("设置 Multi-Agent 失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-set-permission").addEventListener("click", async function () {
            var mode = document.getElementById("permission-mode-select").value;
            var confirmFull = document.getElementById("permission-confirm-full").checked;
            try {
                await apiCall("POST", "/api/v1/permissions/mode", { mode: mode, confirm_full: confirmFull });
                showToast("权限模式已更新", "success");
                loadPermissions();
            } catch (err) {
                showToast("设置权限模式失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-authorize-path").addEventListener("click", async function () {
            var path = document.getElementById("permission-path").value.trim();
            if (!path) {
                showToast("路径为必填项", "warning");
                return;
            }
            try {
                await apiCall("POST", "/api/v1/permissions/authorize", { path: path });
                showToast("路径已授权", "success");
                document.getElementById("permission-path").value = "";
                loadPermissions();
            } catch (err) {
                showToast("授权路径失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-revoke-path").addEventListener("click", async function () {
            var path = document.getElementById("permission-path").value.trim();
            if (!path) {
                showToast("路径为必填项", "warning");
                return;
            }
            try {
                await apiCall("POST", "/api/v1/permissions/revoke", { path: path });
                showToast("路径授权已撤销", "success");
                document.getElementById("permission-path").value = "";
                loadPermissions();
            } catch (err) {
                showToast("撤销路径授权失败: " + err.message, "error");
            }
        });
        document.getElementById("btn-refresh-permissions").addEventListener("click", loadPermissions);
    }

    // ---- 日志查看器 -------------------------------------------------------

    async function loadLogs() {
        try {
            const data = await apiCall("GET", "/api/v1/logs");
            var logs = Array.isArray(data) ? data : [];
            var sel = document.getElementById("log-select");
            var current = sel.value;
            sel.innerHTML = '<option value="">选择日志</option>';
            logs.forEach(function (l) {
                var opt = document.createElement("option");
                opt.value = l.name || l.id || l;
                opt.textContent = l.name || l.id || l;
                sel.appendChild(opt);
            });
            if (current) sel.value = current;
        } catch (err) {
            showToast("加载日志失败: " + err.message, "error");
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
                document.getElementById("log-content").textContent = "加载日志出错: " + err.message;
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
                showToast("消息为必填项", "warning");
                return;
            }
            try {
                var body = { message: message };
                if (sessionId) body.session_id = sessionId;
                await apiCall("POST", "/api/v1/logs", body);
                showToast("日志条目已写入", "success");
                document.getElementById("log-write-form").classList.add("hidden");
                document.getElementById("log-message").value = "";
                document.getElementById("log-session-id").value = "";
            } catch (err) {
                showToast("写入日志失败: " + err.message, "error");
            }
        });
    }

    // ---- 自进化 -----------------------------------------------------------

    async function loadSelfEvolution() {
        try {
            const data = await apiCall("GET", "/api/v1/self-evolution");
            renderSelfEvolution(Array.isArray(data) ? data : []);
        } catch (err) {
            showToast("加载自进化数据失败: " + err.message, "error");
        }
    }

    function renderSelfEvolution(data) {
        var tbody = document.getElementById("self-evolution-tbody");
        if (!tbody) return;

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">未找到自进化制品</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(function (item) {
            return "<tr>" +
                "<td>" + escapeHtml(item.id || "-") + "</td>" +
                "<td>" + escapeHtml(item.type || "-") + "</td>" +
                "<td>" + escapeHtml(item.instruction || "-") + "</td>" +
                "<td><span class=\"status-badge " + (item.status === "success" ? "success" : item.status === "error" ? "error" : "info") + "\">" + escapeHtml(localizeStatus(item.status || "pending")) + "</span></td>" +
                "<td>" +
                "<button class=\"btn btn-sm btn-secondary\" data-action=\"view-artifact\" data-id=\"" + escapeAttribute(item.id) + "\">查看</button> " +
                "<button class=\"btn btn-sm btn-danger\" data-action=\"delete-artifact\" data-id=\"" + escapeAttribute(item.id) + "\">删除</button>" +
                "</td>" +
                "</tr>";
        }).join("");
    }

    async function generateArtifact() {
        var instruction = document.getElementById("se-instruction").value;
        var artifactType = document.getElementById("se-artifact-type").value;
        var output = document.getElementById("se-output").value;

        if (!instruction || !output) {
            showToast("请填写所有必填字段", "error");
            return;
        }

        try {
            var data = await apiCall("POST", "/api/v1/self-evolution/generate", {
                instruction: instruction,
                type: artifactType,
                output: output
            });
            if (data.success) {
                showToast("制品生成成功", "success");
                loadSelfEvolution();
                document.getElementById("self-evolution-form").classList.add("hidden");
            } else {
                showToast(data.error || "生成制品失败", "error");
            }
        } catch (err) {
            showToast("生成制品失败: " + err.message, "error");
        }
    }

    async function viewArtifact(id) {
        try {
            var data = await apiCall("GET", "/api/v1/self-evolution/" + encodeURIComponent(id));
            showJsonDetails("自进化制品", data);
        } catch (err) {
            showToast("查看制品失败: " + err.message, "error");
        }
    }

    async function deleteArtifact(id) {
        if (!await requestConfirmation("确定要删除此制品吗？", "删除制品")) return;
        try {
            var data = await apiCall("DELETE", "/api/v1/self-evolution/" + encodeURIComponent(id));
            if (data.success) {
                showToast("制品删除成功", "success");
                loadSelfEvolution();
            } else {
                showToast(data.error || "删除制品失败", "error");
            }
        } catch (err) {
            showToast("删除制品失败: " + err.message, "error");
        }
    }

    function setupSelfEvolutionForm() {
        var refreshBtn = document.getElementById("btn-refresh-self-evolution");
        if (refreshBtn) refreshBtn.addEventListener("click", loadSelfEvolution);

        var generateBtn = document.getElementById("btn-generate-artifacts");
        if (generateBtn) generateBtn.addEventListener("click", function () {
            document.getElementById("self-evolution-form").classList.toggle("hidden");
        });

        var saveBtn = document.getElementById("btn-save-artifact");
        if (saveBtn) saveBtn.addEventListener("click", generateArtifact);

        var cancelBtn = document.getElementById("btn-cancel-artifact");
        if (cancelBtn) cancelBtn.addEventListener("click", function () {
            document.getElementById("self-evolution-form").classList.add("hidden");
        });
    }

    // ---- 诊断 -------------------------------------------------------------

    function loadDiagnostics() {
        authorizedFetch('/api/v1/diagnose')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                renderDiagnostics(data);
            })
            .catch(function (error) {
                console.error('加载诊断出错:', error);
                showToast('加载诊断失败', 'error');
            });
    }

    function renderDiagnostics(data) {
        var configInfo = document.getElementById('diagnose-config-info');
        var llmInfo = document.getElementById('diagnose-llm-info');
        var installInfo = document.getElementById('diagnose-install-info');

        if (configInfo) {
            configInfo.innerHTML = data.config ? (
                '<p><strong>状态:</strong> ' + (data.config.exists ? '✓ 已初始化' : '✗ 未找到') + '</p>' +
                '<p><strong>路径:</strong> ' + escapeHtml(data.config.path || '-') + '</p>'
            ) : '<p>无配置数据</p>';
        }

        if (llmInfo) {
            llmInfo.innerHTML = data.llm ? (
                '<p><strong>状态:</strong> ' + (data.llm.ok ? '✓ 已配置' : '✗ 未配置') + '</p>' +
                '<p><strong>提供商:</strong> ' + escapeHtml(data.llm.provider || '-') + '</p>'
            ) : '<p>无LLM数据</p>';
        }

        if (installInfo) {
            installInfo.innerHTML = data.install ? (
                '<p><strong>状态:</strong> ' + (data.install.ok ? '✓ 有效' : '✗ 无效') + '</p>' +
                '<p><strong>版本:</strong> ' + escapeHtml(data.install.version || '-') + '</p>'
            ) : '<p>无安装数据</p>';
        }
    }

    function runConfigDiagnostics() {
        authorizedFetch('/api/v1/diagnose/config')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                document.getElementById('diagnose-content').textContent = JSON.stringify(data, null, 2);
                showToast('配置诊断完成', 'success');
            })
            .catch(function (error) {
                console.error('运行配置诊断出错:', error);
                showToast('运行配置诊断失败', 'error');
            });
    }

    function runLLMDiagnostics() {
        authorizedFetch('/api/v1/diagnose/llm')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                document.getElementById('diagnose-content').textContent = JSON.stringify(data, null, 2);
                showToast('LLM 诊断完成', 'success');
            })
            .catch(function (error) {
                console.error('运行 LLM 诊断出错:', error);
                showToast('运行 LLM 诊断失败', 'error');
            });
    }

    function runInstallDiagnostics() {
        authorizedFetch('/api/v1/diagnose/install')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                document.getElementById('diagnose-content').textContent = JSON.stringify(data, null, 2);
                showToast('安装诊断完成', 'success');
            })
            .catch(function (error) {
                console.error('运行安装诊断出错:', error);
                showToast('运行安装诊断失败', 'error');
            });
    }

    function runAllDiagnostics() {
        authorizedFetch('/api/v1/diagnose')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                document.getElementById('diagnose-content').textContent = JSON.stringify(data, null, 2);
                renderDiagnostics(data);
                showToast('全部诊断完成', 'success');
            })
            .catch(function (error) {
                console.error('运行全部诊断出错:', error);
                showToast('运行全部诊断失败', 'error');
            });
    }

    function setupDiagnoseForm() {
        var refreshBtn = document.getElementById('btn-refresh-diagnose');
        var runAllBtn = document.getElementById('btn-run-all-diagnostics');
        var configBtn = document.getElementById('btn-diagnose-config');
        var llmBtn = document.getElementById('btn-diagnose-llm');
        var installBtn = document.getElementById('btn-diagnose-install');
        if (refreshBtn) refreshBtn.addEventListener('click', loadDiagnostics);
        if (runAllBtn) runAllBtn.addEventListener('click', runAllDiagnostics);
        if (configBtn) configBtn.addEventListener('click', runConfigDiagnostics);
        if (llmBtn) llmBtn.addEventListener('click', runLLMDiagnostics);
        if (installBtn) installBtn.addEventListener('click', runInstallDiagnostics);
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
            if (webAuthToken) {
                ws.send(JSON.stringify({ type: "auth", token: webAuthToken }));
            } else {
                setConnected(true);
            }
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        ws.onclose = function () {
            setConnected(false);
            setChatProcessing(false);
            scheduleReconnect();
        };

        ws.onerror = function () {
            setConnected(false);
            setChatProcessing(false);
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
                case "auth_ok":
                    setConnected(true);
                    break;

                case "progress":
                    addMessage("progress", data.data.message || JSON.stringify(data.data), "progress");
                    break;

                case "result": {
                    setChatProcessing(false);
                    var result = data.data;
                    var text = "";
                    if (result.output && typeof result.output === "object") {
                        text = result.output.message || result.output.text || JSON.stringify(result.output, null, 2);
                    } else if (result.output) {
                        text = String(result.output);
                    } else if (result.error) {
                        text = "错误: " + String(result.error);
                        addMessage("assistant", text, "error");
                        return;
                    } else {
                        text = JSON.stringify(result, null, 2);
                    }
                    addMessage("assistant", text);
                    break;
                }

                case "error":
                    setChatProcessing(false);
                    addMessage("system", data.content || "未知错误", "error");
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

    // ---- 发送消息 ---------------------------------------------------------

    function sendMessage(text) {
        if (!text.trim()) return;
        if (chatProcessing) return;

        addMessage("user", text);
        setChatProcessing(true);

        var selectedWorkspace = selectedChatWorkspace();
        var payload = { message: text };
        if (selectedWorkspace) {
            payload.workspace_id = selectedWorkspace;
        }

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
        } else {
            authorizedFetch("/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    setChatProcessing(false);
                    var out = data.output
                        ? (typeof data.output === "object" ? (data.output.message || JSON.stringify(data.output, null, 2)) : String(data.output))
                        : JSON.stringify(data, null, 2);
                    addMessage("assistant", out);
                })
                .catch(function (err) {
                    setChatProcessing(false);
                    addMessage("system", "请求失败: " + err.message, "error");
                });
        }
    }

    // ---- 事件监听 ---------------------------------------------------------

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

    if (chatWsSelect) {
        chatWsSelect.addEventListener("change", function () {
            handleWorkspaceSelection(this.value);
        });
    }

    if (webAuthTokenInput) webAuthTokenInput.value = webAuthToken;
    if (webAuthSave) {
        webAuthSave.addEventListener("click", function () {
            webAuthToken = webAuthTokenInput.value.trim();
            if (webAuthToken) {
                sessionStorage.setItem("supermedicine.webAuthToken", webAuthToken);
            } else {
                sessionStorage.removeItem("supermedicine.webAuthToken");
            }
            if (ws) ws.close();
            fetchStatus();
            connect();
        });
    }

    // ---- 锚点平滑滚动 -----------------------------------------------------

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

    // ---- 点击关闭提示 -----------------------------------------------------

    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("toast")) {
            e.target.style.animation = "toastOut 0.3s ease forwards";
            setTimeout(function () {
                e.target.remove();
            }, 300);
        }

        var actionTarget = e.target.closest("[data-action]");
        if (!actionTarget) return;
        var action = actionTarget.dataset.action;
        if (action === "delete-workspace") deleteWorkspace(actionTarget.dataset.id);
        if (action === "enrich-paper") enrichPaper(actionTarget.dataset.workspace, actionTarget.dataset.id);
        if (action === "delete-experience") deleteExperience(actionTarget.dataset.workspace, actionTarget.dataset.id, actionTarget.dataset.scope);
        if (action === "view-experiment") viewExperiment(actionTarget.dataset.id);
        if (action === "show-llm") showLLM(actionTarget.dataset.provider);
        if (action === "switch-llm") switchLLM(actionTarget.dataset.provider);
        if (action === "view-artifact") viewArtifact(actionTarget.dataset.id);
        if (action === "delete-artifact") deleteArtifact(actionTarget.dataset.id);
    });

    // ---- 键盘快捷键 -------------------------------------------------------

    document.addEventListener("keydown", async function (e) {
        // Ctrl/Cmd + K 聚焦搜索框（如果存在）
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            var searchInput = document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape 关闭弹窗和抽屉
        if (e.key === "Escape") {
            var modals = document.querySelectorAll(".modal.active");
            modals.forEach(function (modal) {
                modal.classList.remove("active");
            });
            closeDrawer();
        }

        // Ctrl+Q 仅关闭当前窗口；服务生命周期由启动它的进程管理。
        if (e.ctrlKey && e.key === "q") {
            e.preventDefault();
            if (await requestConfirmation("确定要退出 SuperMedicine 吗？", "退出应用")) {
                window.close();
            }
        }

        // F11 切换全屏
        if (e.key === "F11") {
            e.preventDefault();
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                document.documentElement.requestFullscreen();
            }
        }

        // Ctrl+1-9 切换页面
        if (e.ctrlKey && e.key >= "1" && e.key <= "9") {
            e.preventDefault();
            var tabIndex = parseInt(e.key, 10) - 1;
            var tabBtns = document.querySelectorAll(".tab-btn");
            if (tabIndex < tabBtns.length) {
                tabBtns[tabIndex].click();
            }
        }
    });

    // ---- 初始化 -----------------------------------------------------------

    initTabs();
    setupWorkspaceForm();
    setupPaperForm();
    setupExperienceForm();
    setupToolForm();
    setupExperimentForm();
    setupDialogHistoryForm();
    setupLLMForm();
    setupPermissionForm();
    setupLogForm();
    setupSelfEvolutionForm();
    setupDiagnoseForm();
    loadWorkspaceSelectors();
    fetchStatus();
    connect();
})();

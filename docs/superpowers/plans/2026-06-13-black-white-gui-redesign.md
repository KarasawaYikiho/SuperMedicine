# SuperMedicine Black & White GUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the SuperMedicine web interface with a modern, minimalist black and white (monochrome) design system while preserving all existing functionality.

**Architecture:** Pure CSS redesign with enhanced HTML structure and JavaScript animation support. No backend changes required. The design uses a monochrome palette (black #000, white #fff, grays) with clean typography, card-based layouts, subtle shadows, and smooth transitions.

**Tech Stack:** HTML5, CSS3 (custom properties, grid, flexbox, animations), vanilla JavaScript (no dependencies)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `core/web/frontend/style.css` | Complete redesign - monochrome color system, modern typography, card layouts, animations |
| `core/web/frontend/index.html` | Structural enhancements - semantic markup, accessibility attributes, icon placeholders |
| `core/web/frontend/app.js` | Animation helpers, smooth transitions, enhanced toast system |
| `core/web/server.py` | No changes - backend serves frontend as-is |

---

## Task 1: Redesign CSS Color System & Base Styles

**Files:**
- Modify: `core/web/frontend/style.css:1-35`

- [ ] **Step 1: Replace CSS custom properties with monochrome palette**

```css
:root {
    /* Monochrome Color System */
    --color-bg: #000000;
    --color-surface: #0a0a0a;
    --color-surface-elevated: #111111;
    --color-surface-hover: #1a1a1a;
    --color-border: #222222;
    --color-border-light: #333333;
    
    /* Text Colors */
    --color-text: #ffffff;
    --color-text-secondary: #a0a0a0;
    --color-text-muted: #666666;
    --color-text-inverse: #000000;
    
    /* Accent (keeping minimal for status indicators) */
    --color-success: #00ff00;
    --color-warning: #ffaa00;
    --color-error: #ff3333;
    --color-info: #00aaff;
    
    /* Design Tokens */
    --radius-sm: 4px;
    --radius: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(255, 255, 255, 0.05);
    --shadow: 0 2px 8px rgba(255, 255, 255, 0.08);
    --shadow-lg: 0 8px 24px rgba(255, 255, 255, 0.12);
    
    /* Typography */
    --font-mono: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    --font-sans: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
    
    /* Transitions */
    --transition-fast: 150ms ease;
    --transition: 200ms ease;
    --transition-slow: 300ms ease;
}
```

- [ ] **Step 2: Update base body styles**

```css
body {
    font-family: var(--font-sans);
    background: var(--color-bg);
    color: var(--color-text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
```

- [ ] **Step 3: Verify CSS variables compile correctly**

Open `core/web/frontend/index.html` in browser, verify no visual regressions (temporary).

---

## Task 2: Redesign Header Component

**Files:**
- Modify: `core/web/frontend/style.css:36-76`

- [ ] **Step 1: Update header styles**

```css
header {
    background: var(--color-surface);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--color-border);
    backdrop-filter: blur(10px);
    position: sticky;
    top: 0;
    z-index: 100;
}

header h1 {
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--color-text);
}

header h1::before {
    content: "◆";
    margin-right: 0.5rem;
    color: var(--color-text);
}
```

- [ ] **Step 2: Update status indicator styles**

```css
#status-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.85rem;
    color: var(--color-text-secondary);
}

#status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    transition: all var(--transition);
}

#status-indicator.connected {
    background: var(--color-text);
    box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

#status-indicator.disconnected {
    background: var(--color-error);
    box-shadow: 0 0 8px rgba(255, 51, 51, 0.5);
}
```

- [ ] **Step 3: Verify header renders correctly**

Check header alignment, status indicator visibility.

---

## Task 3: Redesign Tab Navigation

**Files:**
- Modify: `core/web/frontend/style.css:77-111`

- [ ] **Step 1: Update tab navigation container**

```css
#tab-nav {
    background: var(--color-surface);
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    padding: 0 2rem;
    border-bottom: 1px solid var(--color-border);
    overflow-x: auto;
    scrollbar-width: none;
}

#tab-nav::-webkit-scrollbar {
    display: none;
}
```

- [ ] **Step 2: Update tab button styles**

```css
.tab-btn {
    background: transparent;
    color: var(--color-text-muted);
    border: none;
    padding: 1rem 1.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    transition: all var(--transition);
    white-space: nowrap;
    position: relative;
}

.tab-btn:hover {
    color: var(--color-text);
    background: var(--color-surface-hover);
}

.tab-btn.active {
    color: var(--color-text);
    border-bottom-color: var(--color-text);
}

.tab-btn.active::after {
    content: "";
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--color-text);
}
```

- [ ] **Step 3: Test tab switching animation**

Click through tabs, verify smooth transitions.

---

## Task 4: Redesign Main Content Area & Cards

**Files:**
- Modify: `core/web/frontend/style.css:112-195`

- [ ] **Step 1: Update main layout**

```css
main {
    flex: 1;
    padding: 2rem;
    max-width: 1400px;
    width: 100%;
    margin: 0 auto;
}

section {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    border: 1px solid var(--color-border);
    transition: all var(--transition);
}

section:hover {
    border-color: var(--color-border-light);
}

section h2 {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--color-text);
    letter-spacing: -0.01em;
}
```

- [ ] **Step 2: Update status grid and cards**

```css
.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.status-card {
    background: var(--color-surface-elevated);
    padding: 1.25rem;
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
    transition: all var(--transition);
}

.status-card:hover {
    border-color: var(--color-border-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow);
}

.status-card .label {
    color: var(--color-text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
}

.status-card .value {
    font-size: 1.75rem;
    font-weight: 700;
    margin-top: 0.5rem;
    color: var(--color-text);
    font-feature-settings: "tnum";
}
```

- [ ] **Step 3: Update dashboard cards grid**

```css
.dashboard-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    margin-top: 1.5rem;
}

.info-card {
    background: var(--color-surface-elevated);
    padding: 1.25rem;
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
    margin-bottom: 1rem;
    transition: all var(--transition);
}

.info-card:hover {
    border-color: var(--color-border-light);
}

.info-card h3 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    margin-bottom: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
```

- [ ] **Step 4: Verify card layout responsiveness**

Resize browser window, check grid reflows correctly.

---

## Task 5: Redesign Buttons

**Files:**
- Modify: `core/web/frontend/style.css:197-249`

- [ ] **Step 1: Update base button styles**

```css
.btn {
    padding: 0.625rem 1.25rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    cursor: pointer;
    font-weight: 500;
    font-size: 0.875rem;
    transition: all var(--transition);
    background: var(--color-surface);
    color: var(--color-text);
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn:hover {
    background: var(--color-surface-hover);
    border-color: var(--color-border-light);
}

.btn:active {
    transform: scale(0.98);
}
```

- [ ] **Step 2: Update button variants**

```css
.btn-primary {
    background: var(--color-text);
    color: var(--color-bg);
    border-color: var(--color-text);
}

.btn-primary:hover {
    background: var(--color-text-secondary);
    border-color: var(--color-text-secondary);
}

.btn-secondary {
    background: transparent;
    color: var(--color-text);
    border-color: var(--color-border);
}

.btn-secondary:hover {
    background: var(--color-surface-hover);
    border-color: var(--color-border-light);
}

.btn-danger {
    background: transparent;
    color: var(--color-error);
    border-color: var(--color-error);
}

.btn-danger:hover {
    background: rgba(255, 51, 51, 0.1);
}

.btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: 0.8125rem;
}
```

- [ ] **Step 3: Test button interactions**

Hover, click, verify visual feedback.

---

## Task 6: Redesign Forms & Inputs

**Files:**
- Modify: `core/web/frontend/style.css:251-322`

- [ ] **Step 1: Update form container**

```css
.form-container {
    background: var(--color-surface-elevated);
    padding: 1.5rem;
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
    margin-bottom: 1rem;
}

.form-container h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: 1rem;
}
```

- [ ] **Step 2: Update form groups and inputs**

```css
.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
    width: 100%;
    padding: 0.75rem 1rem;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 0.9375rem;
    transition: all var(--transition);
}

.form-group input[type="text"]:focus,
.form-group textarea:focus,
.form-group select:focus {
    outline: none;
    border-color: var(--color-text);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
}

.form-group input[type="text"]::placeholder,
.form-group textarea::placeholder {
    color: var(--color-text-muted);
}

.form-group input[type="checkbox"] {
    margin-right: 0.75rem;
    accent-color: var(--color-text);
}

.form-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.25rem;
}
```

- [ ] **Step 3: Update select input**

```css
.select-input {
    padding: 0.75rem 1rem;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all var(--transition);
}

.select-input:focus {
    outline: none;
    border-color: var(--color-text);
}
```

- [ ] **Step 4: Test form focus states**

Click into inputs, verify focus ring appears.

---

## Task 7: Redesign Data Tables

**Files:**
- Modify: `core/web/frontend/style.css:324-398`

- [ ] **Step 1: Update table container and base styles**

```css
.data-table-container {
    overflow-x: auto;
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9375rem;
}

.data-table th {
    background: var(--color-surface-elevated);
    color: var(--color-text-secondary);
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid var(--color-border);
}

.data-table td {
    padding: 1rem;
    border-bottom: 1px solid var(--color-border);
    vertical-align: middle;
    color: var(--color-text);
}

.data-table tbody tr {
    transition: background var(--transition-fast);
}

.data-table tbody tr:hover {
    background: var(--color-surface-hover);
}

.data-table tbody tr:last-child td {
    border-bottom: none;
}

.data-table .empty-state {
    text-align: center;
    color: var(--color-text-muted);
    font-style: italic;
    padding: 2.5rem 1rem;
}
```

- [ ] **Step 2: Update status badges**

```css
.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status-badge.success {
    background: rgba(0, 255, 0, 0.1);
    color: var(--color-success);
    border: 1px solid rgba(0, 255, 0, 0.2);
}

.status-badge.warning {
    background: rgba(255, 170, 0, 0.1);
    color: var(--color-warning);
    border: 1px solid rgba(255, 170, 0, 0.2);
}

.status-badge.error {
    background: rgba(255, 51, 51, 0.1);
    color: var(--color-error);
    border: 1px solid rgba(255, 51, 51, 0.2);
}

.status-badge.info {
    background: rgba(0, 170, 255, 0.1);
    color: var(--color-info);
    border: 1px solid rgba(0, 170, 255, 0.2);
}
```

- [ ] **Step 3: Test table scrolling**

Add enough content to trigger horizontal scroll, verify behavior.

---

## Task 8: Redesign Chat Interface

**Files:**
- Modify: `core/web/frontend/style.css:513-629`

- [ ] **Step 1: Update chat panel layout**

```css
#tab-chat {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
}

#tab-chat.active {
    display: flex;
}

#messages {
    flex: 1;
    overflow-y: auto;
    min-height: 400px;
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: var(--radius);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
}
```

- [ ] **Step 2: Update message bubbles**

```css
.message {
    margin-bottom: 1rem;
    padding: 1rem 1.25rem;
    border-radius: var(--radius-lg);
    max-width: 80%;
    word-wrap: break-word;
    white-space: pre-wrap;
    animation: message-in 0.3s ease;
}

.message.user {
    background: var(--color-text);
    color: var(--color-bg);
    margin-left: auto;
    border-bottom-right-radius: var(--radius-sm);
}

.message.assistant {
    background: var(--color-surface-elevated);
    border: 1px solid var(--color-border);
    margin-right: auto;
    border-bottom-left-radius: var(--radius-sm);
}

.message.progress {
    background: transparent;
    border: 1px dashed var(--color-border-light);
    color: var(--color-text-muted);
    font-size: 0.875rem;
    font-style: italic;
    margin-right: auto;
    max-width: 100%;
}

.message.error {
    background: rgba(255, 51, 51, 0.1);
    border: 1px solid var(--color-error);
    color: var(--color-error);
    margin-right: auto;
    max-width: 100%;
}

.message .role {
    font-size: 0.6875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.375rem;
    opacity: 0.7;
}

@keyframes message-in {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

- [ ] **Step 3: Update chat input form**

```css
#chat-form {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
}

#chat-input {
    flex: 1;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: 1rem;
    resize: vertical;
    min-height: 3rem;
    transition: all var(--transition);
}

#chat-input:focus {
    outline: none;
    border-color: var(--color-text);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
}

#send-btn {
    padding: 1rem 2rem;
    background: var(--color-text);
    color: var(--color-bg);
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    font-weight: 600;
    font-size: 1rem;
    transition: all var(--transition);
    align-self: flex-end;
}

#send-btn:hover {
    background: var(--color-text-secondary);
}

#send-btn:disabled {
    background: var(--color-border);
    color: var(--color-text-muted);
    cursor: not-allowed;
}
```

- [ ] **Step 4: Test chat message flow**

Send messages, verify bubble alignment and animations.

---

## Task 9: Redesign Toast Notifications

**Files:**
- Modify: `core/web/frontend/style.css:461-511`

- [ ] **Step 1: Update toast container and base styles**

```css
#toast-container {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-width: 400px;
}

.toast {
    padding: 1rem 1.25rem;
    border-radius: var(--radius);
    font-size: 0.9375rem;
    animation: toast-in 0.3s ease, toast-out 0.3s ease 2.7s forwards;
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--color-border);
    backdrop-filter: blur(10px);
}

.toast.success {
    background: rgba(0, 255, 0, 0.15);
    border-color: var(--color-success);
    color: var(--color-success);
}

.toast.error {
    background: rgba(255, 51, 51, 0.15);
    border-color: var(--color-error);
    color: var(--color-error);
}

.toast.info {
    background: rgba(0, 170, 255, 0.15);
    border-color: var(--color-info);
    color: var(--color-info);
}

.toast.warning {
    background: rgba(255, 170, 0, 0.15);
    border-color: var(--color-warning);
    color: var(--color-warning);
}

@keyframes toast-in {
    from {
        opacity: 0;
        transform: translateX(100%);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes toast-out {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(100%);
    }
}
```

- [ ] **Step 2: Test toast notifications**

Trigger success/error toasts, verify animations.

---

## Task 10: Redesign Log Viewer

**Files:**
- Modify: `core/web/frontend/style.css:400-431`

- [ ] **Step 1: Update log viewer styles**

```css
.log-viewer {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 1.5rem;
    max-height: 60vh;
    overflow-y: auto;
}

.log-viewer pre {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    white-space: pre-wrap;
    word-wrap: break-word;
    color: var(--color-text-secondary);
    line-height: 1.7;
}

.log-viewer::-webkit-scrollbar {
    width: 8px;
}

.log-viewer::-webkit-scrollbar-track {
    background: var(--color-bg);
}

.log-viewer::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
}

.log-viewer::-webkit-scrollbar-thumb:hover {
    background: var(--color-border-light);
}
```

- [ ] **Step 2: Test log viewer scrolling**

Load long log content, verify smooth scrolling.

---

## Task 11: Redesign Scan Results & Toolbar

**Files:**
- Modify: `core/web/frontend/style.css:197-206, 433-459`

- [ ] **Step 1: Update toolbar styles**

```css
.toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    align-items: center;
}
```

- [ ] **Step 2: Update scan results grid**

```css
.scan-results {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.scan-item {
    background: var(--color-surface-elevated);
    padding: 1rem;
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: all var(--transition);
}

.scan-item:hover {
    border-color: var(--color-border-light);
}

.scan-item input[type="checkbox"] {
    flex-shrink: 0;
    accent-color: var(--color-text);
}

.scan-item label {
    font-size: 0.9375rem;
    cursor: pointer;
    color: var(--color-text);
}
```

- [ ] **Step 3: Test scan results display**

Open tools tab, trigger scan, verify grid layout.

---

## Task 12: Update Scrollbar Styles

**Files:**
- Modify: `core/web/frontend/style.css:653-670`

- [ ] **Step 1: Update global scrollbar styles**

```css
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--color-bg);
}

::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--color-border-light);
}

/* Firefox */
* {
    scrollbar-width: thin;
    scrollbar-color: var(--color-border) var(--color-bg);
}
```

- [ ] **Step 2: Test scrollbar appearance**

Scroll various containers, verify consistent styling.

---

## Task 13: Update Responsive Design

**Files:**
- Modify: `core/web/frontend/style.css:672-714`

- [ ] **Step 1: Update mobile breakpoints**

```css
@media (max-width: 768px) {
    header {
        flex-direction: column;
        gap: 0.75rem;
        text-align: center;
        padding: 1rem;
    }

    #tab-nav {
        justify-content: flex-start;
        padding: 0 1rem;
    }

    .tab-btn {
        padding: 0.75rem 1rem;
        font-size: 0.8125rem;
    }

    main {
        padding: 1rem;
    }

    section {
        padding: 1rem;
    }

    .toolbar {
        flex-direction: column;
        align-items: stretch;
    }

    .select-input {
        width: 100%;
    }

    .data-table {
        font-size: 0.8125rem;
    }

    .data-table th,
    .data-table td {
        padding: 0.75rem;
    }

    .form-actions {
        flex-direction: column;
    }

    .btn {
        width: 100%;
        justify-content: center;
    }

    #chat-form {
        flex-direction: column;
    }

    #send-btn {
        width: 100%;
    }

    .message {
        max-width: 90%;
    }
}

@media (max-width: 480px) {
    .status-grid {
        grid-template-columns: 1fr;
    }

    .dashboard-cards {
        grid-template-columns: 1fr;
    }

    .scan-results {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 2: Test mobile responsiveness**

Use browser dev tools to test 375px, 768px, 1024px widths.

---

## Task 14: Add Utility Classes & Final Polish

**Files:**
- Modify: `core/web/frontend/style.css:631-651`

- [ ] **Step 1: Update utility classes**

```css
.hidden {
    display: none !important;
}

.text-muted {
    color: var(--color-text-muted);
}

.text-secondary {
    color: var(--color-text-secondary);
}

.text-success {
    color: var(--color-success);
}

.text-error {
    color: var(--color-error);
}

.text-warning {
    color: var(--color-warning);
}

/* Selection color */
::selection {
    background: var(--color-text);
    color: var(--color-bg);
}

/* Focus visible for keyboard navigation */
:focus-visible {
    outline: 2px solid var(--color-text);
    outline-offset: 2px;
}

/* Smooth transitions for all interactive elements */
a, button, input, select, textarea {
    transition: all var(--transition);
}
```

- [ ] **Step 2: Verify final visual consistency**

Review all components together, ensure cohesive design.

---

## Task 15: Update HTML Structure (Optional Enhancements)

**Files:**
- Modify: `core/web/frontend/index.html`

- [ ] **Step 1: Add Inter font import**

Add to `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- [ ] **Step 2: Add meta theme color**

Add to `<head>`:
```html
<meta name="theme-color" content="#000000">
<meta name="color-scheme" content="dark">
```

- [ ] **Step 3: Verify font loading**

Check network tab for font requests, verify rendering.

---

## Task 16: Update JavaScript for Enhanced Interactions

**Files:**
- Modify: `core/web/frontend/app.js`

- [ ] **Step 1: Add smooth scroll utility**

Add after `escapeHtml` function:
```javascript
function smoothScrollToBottom(element) {
    element.scrollTo({
        top: element.scrollHeight,
        behavior: 'smooth'
    });
}
```

- [ ] **Step 2: Update message scroll behavior**

Replace `messagesEl.scrollTop = messagesEl.scrollHeight;` with:
```javascript
smoothScrollToBottom(messagesEl);
```

- [ ] **Step 3: Add toast dismiss on click**

Update `showToast` function:
```javascript
function showToast(message, type) {
    type = type || "info";
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.textContent = message;
    toast.style.cursor = "pointer";
    toast.addEventListener("click", function() {
        toast.remove();
    });
    container.appendChild(toast);
    setTimeout(function () {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}
```

- [ ] **Step 4: Test enhanced interactions**

Send chat messages, trigger toasts, verify smooth behavior.

---

## Task 17: Final Testing & Verification

**Files:**
- None (testing only)

- [ ] **Step 1: Visual regression test**

Open `http://localhost:8000` in browser, verify:
- All 10 tabs render correctly
- Black and white color scheme applied consistently
- Text is readable with high contrast
- Cards have subtle shadows
- Buttons have clear hover/active states
- Forms are properly styled
- Tables are clean and readable
- Chat interface works smoothly
- Toast notifications animate correctly

- [ ] **Step 2: Responsive test**

Test at these breakpoints:
- 375px (mobile)
- 768px (tablet)
- 1024px (small desktop)
- 1400px+ (large desktop)

- [ ] **Step 3: Accessibility check**

- Verify focus indicators are visible
- Check color contrast ratios (should be 4.5:1 minimum)
- Test keyboard navigation through tabs and forms

- [ ] **Step 4: Functionality verification**

Test all features still work:
- Tab switching
- WebSocket chat connection
- Workspace CRUD operations
- Paper import/enrichment
- Experience management
- Tool scanning
- Experiment creation
- LLM provider switching
- Permission mode changes
- Log viewing/writing

- [ ] **Step 5: Browser compatibility**

Test in:
- Chrome/Edge (Chromium)
- Firefox
- Safari (if available)

---

## Dependencies

- Task 1-4: Foundation (colors, header, tabs, cards)
- Task 5-7: Components (buttons, forms, tables)
- Task 8-11: Complex components (chat, toasts, logs, scan)
- Task 12-14: Polish (scrollbars, responsive, utilities)
- Task 15-16: Enhancements (HTML, JavaScript)
- Task 17: Final verification (depends on all above)

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-06-13-black-white-gui-redesign.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

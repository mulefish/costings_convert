/* --- Progress modal with running timer --- */
function showProgressModal(message) {
    let overlay = document.getElementById("progress-modal-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "progress-modal-overlay";
        overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;";
        const box = document.createElement("div");
        box.id = "progress-modal-box";
        box.style.cssText = "background:#fff;border-radius:8px;padding:32px 48px;text-align:center;min-width:280px;box-shadow:0 4px 24px rgba(0,0,0,0.3);";
        box.innerHTML = `
            <div id="progress-modal-msg" style="font-size:15px;margin-bottom:16px;font-weight:600;"></div>
            <div id="progress-modal-timer" style="font-size:28px;font-family:monospace;color:#333;"></div>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);
    }
    overlay.style.display = "flex";
    document.getElementById("progress-modal-msg").textContent = message || "Processing...";
    const timerEl = document.getElementById("progress-modal-timer");
    const start = performance.now();
    const intervalId = setInterval(() => {
        const elapsed = (performance.now() - start) / 1000;
        const secs = Math.floor(elapsed);
        const tenths = Math.floor((elapsed - secs) * 10);
        timerEl.textContent = `${secs}.${tenths}s`;
    }, 100);
    overlay._intervalId = intervalId;
    return overlay;
}

function hideProgressModal() {
    const overlay = document.getElementById("progress-modal-overlay");
    if (overlay) {
        clearInterval(overlay._intervalId);
        overlay.style.display = "none";
    }
}

async function renderControlPanelView() {
    const content = document.getElementById("content");
    const wrap = document.createElement("div");
    wrap.id = "jarvis-view";

    const h = document.createElement("h3");
    h.style.marginTop = "0";
    h.textContent = "Jarvis";
    wrap.appendChild(h);

    const p = document.createElement("p");
    p.style.fontSize = "13px";
    p.style.color = "#444";
    p.style.maxWidth = "720px";
    p.style.lineHeight = "1.45";
    p.textContent =
        "Values edited here are saved to the SQLite database (costings/data/costings.db): global control-panel numbers (fuel surcharge, OTR GRI, ocean GRI, interest, commission, and related inputs), consolidation, consolidation days storage, drayage by port, document/CIF by country, USA forwarding, and themes (Export tints each row using Themes → Country vs Export Base). " +
        "They drive the OTR, OCEAN, USD, PTS, CIF, and Export views.";
    wrap.appendChild(p);

    const status = document.createElement("p");
    status.style.fontSize = "13px";
    status.style.minHeight = "1.2em";
    wrap.appendChild(status);

    const consolStatus = document.createElement("p");
    consolStatus.style.fontSize = "13px";
    consolStatus.style.minHeight = "1.2em";

    const cdsStatus = document.createElement("p");
    cdsStatus.style.fontSize = "13px";
    cdsStatus.style.minHeight = "1.2em";

    const drayageStatus = document.createElement("p");
    drayageStatus.style.fontSize = "13px";
    drayageStatus.style.minHeight = "1.2em";

    const docCifStatus = document.createElement("p");
    docCifStatus.style.fontSize = "13px";
    docCifStatus.style.minHeight = "1.2em";

    const usaFwdStatus = document.createElement("p");
    usaFwdStatus.style.fontSize = "13px";
    usaFwdStatus.style.minHeight = "1.2em";

    const themesStatus = document.createElement("p");
    themesStatus.style.fontSize = "13px";
    themesStatus.style.minHeight = "1.2em";

    let data = {};
    let consol = {};
    let cds = {};
    let drayageData = {};
    let documentCifData = [];
    let usaFwdData = {};
    try {
        const cpRes = await fetch("/api/control-panel");
        if (!cpRes.ok) {
            throw new Error(cpRes.statusText);
        }
        data = await cpRes.json();
    } catch (err) {
        console.error(err);
        status.textContent = "Could not load control panel.";
        status.style.color = "#b00020";
        content.appendChild(wrap);
        return;
    }

    try {
        const cRes = await fetch("/api/consolidation");
        if (!cRes.ok) {
            consolStatus.textContent = "Could not load consolidation.";
            consolStatus.style.color = "#b00020";
        } else {
            consol = await cRes.json();
        }
    } catch (err) {
        console.error(err);
        consolStatus.textContent = "Could not load consolidation.";
        consolStatus.style.color = "#b00020";
    }

    try {
        const cdsRes = await fetch("/api/consolidation-days-storage");
        if (!cdsRes.ok) {
            cdsStatus.textContent = "Could not load consolidation days storage.";
            cdsStatus.style.color = "#b00020";
        } else {
            cds = await cdsRes.json();
        }
    } catch (err) {
        console.error(err);
        cdsStatus.textContent = "Could not load consolidation days storage.";
        cdsStatus.style.color = "#b00020";
    }

    try {
        const drayRes = await fetch("/api/drayage");
        if (!drayRes.ok) {
            drayageStatus.textContent = "Could not load drayage.";
            drayageStatus.style.color = "#b00020";
        } else {
            drayageData = await drayRes.json();
        }
    } catch (err) {
        console.error(err);
        drayageStatus.textContent = "Could not load drayage.";
        drayageStatus.style.color = "#b00020";
    }

    try {
        const dcRes = await fetch("/api/document-cif");
        if (!dcRes.ok) {
            docCifStatus.textContent = "Could not load document / CIF.";
            docCifStatus.style.color = "#b00020";
        } else {
            documentCifData = await dcRes.json();
        }
    } catch (err) {
        console.error(err);
        docCifStatus.textContent = "Could not load document / CIF.";
        docCifStatus.style.color = "#b00020";
    }

    try {
        const ufcRes = await fetch("/api/usa-forwarding-cost");
        if (!ufcRes.ok) {
            usaFwdStatus.textContent = "Could not load USA forwarding cost.";
            usaFwdStatus.style.color = "#b00020";
        } else {
            usaFwdData = await ufcRes.json();
        }
    } catch (err) {
        console.error(err);
        usaFwdStatus.textContent = "Could not load USA forwarding cost.";
        usaFwdStatus.style.color = "#b00020";
    }

    let themesRows = [];
    try {
        const themesRes = await fetch("/api/themes");
        if (!themesRes.ok) {
            themesStatus.textContent = "Could not load themes.";
            themesStatus.style.color = "#b00020";
        } else {
            themesRows = await themesRes.json();
            if (!Array.isArray(themesRows)) {
                themesRows = [];
            }
        }
    } catch (err) {
        console.error(err);
        themesStatus.textContent = "Could not load themes.";
        themesStatus.style.color = "#b00020";
    }

    function getDaysMultiplierFromForm() {
        for (const inp of wrap.querySelectorAll("input[data-cds-key]")) {
            const k = inp.getAttribute("data-cds-key");
            if (k === "Days Storage") {
                const v = parseFloat(inp.value, 10);
                if (!Number.isNaN(v)) {
                    return v;
                }
                break;
            }
        }
        const fallback = Number(cds["Days Storage"]);
        return Number.isFinite(fallback) ? fallback : 14;
    }

    const table = document.createElement("table");
    table.style.borderCollapse = "collapse";
    table.style.marginTop = "8px";
    table.style.minWidth = "420px";
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    ["Parameter", "Value"].forEach((label) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");

    Object.keys(data).forEach((key) => {
        const tr = document.createElement("tr");
        const tdL = document.createElement("td");
        tdL.textContent = key;
        tdL.style.border = "1px solid #d9d9d9";
        tdL.style.padding = "6px 10px";
        const tdR = document.createElement("td");
        tdR.style.border = "1px solid #d9d9d9";
        tdR.style.padding = "6px 10px";
        const inp = document.createElement("input");
        inp.type = "number";
        inp.step = "any";
        inp.value = data[key];
        inp.dataset.key = key;
        inp.style.width = "100%";
        inp.style.boxSizing = "border-box";
        inp.style.padding = "6px 8px";
        tdR.appendChild(inp);
        tr.appendChild(tdL);
        tr.appendChild(tdR);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);

    const btnRow = document.createElement("div");
    btnRow.style.marginTop = "12px";
    btnRow.style.display = "flex";
    btnRow.style.gap = "8px";
    btnRow.style.alignItems = "center";
    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.textContent = "Save";
    saveBtn.style.padding = "8px 16px";
    saveBtn.style.cursor = "pointer";
    saveBtn.addEventListener("click", async () => {
        status.textContent = "";
        status.style.color = "";
        const body = {};
        for (const inp of wrap.querySelectorAll("input[data-key]")) {
            const k = inp.dataset.key;
            const v = parseFloat(inp.value, 10);
            if (Number.isNaN(v)) {
                status.textContent = `Invalid number for “${k}”.`;
                status.style.color = "#b00020";
                return;
            }
            body[k] = v;
        }
        try {
            const res = await fetch("/api/control-panel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            status.textContent = "Saved.";
            status.style.color = "#1b5e20";
        } catch (err) {
            console.error(err);
            status.textContent = err.message || "Save failed.";
            status.style.color = "#b00020";
        }
    });
    btnRow.appendChild(saveBtn);
    wrap.appendChild(btnRow);

    const CONSOL_METRICS = [
        ["bale", "InAndOut"],
        ["storage", "Storage"],
        ["month", "TotalStorage"],
    ];
    const h2 = document.createElement("h3");
    h2.style.marginTop = "28px";
    h2.style.marginBottom = "8px";
    h2.textContent = "Consolidation";
    wrap.appendChild(h2);

    const p2 = document.createElement("p");
    p2.style.fontSize = "13px";
    p2.style.color = "#444";
    p2.style.maxWidth = "720px";
    p2.style.lineHeight = "1.45";
    p2.textContent =
        "Per-region InAndOut and Storage are saved to costings/data/consolidation.json (keys bale, storage). " +
        "TotalStorage is Storage × Days Storage; it updates live when Days Storage changes, and saving Days Storage " +
        "also recomputes and saves consolidation on the server.";
    wrap.appendChild(p2);

    wrap.appendChild(consolStatus);

    const consolTable = document.createElement("table");
    consolTable.style.borderCollapse = "collapse";
    consolTable.style.marginTop = "8px";
    consolTable.style.minWidth = "520px";
    const cThead = document.createElement("thead");
    const chr = document.createElement("tr");
    const chRegion = document.createElement("th");
    chRegion.textContent = "Region";
    chRegion.style.border = "1px solid #d9d9d9";
    chRegion.style.padding = "6px 10px";
    chRegion.style.background = "#2f5fa7";
    chRegion.style.color = "#fff";
    chr.appendChild(chRegion);
    CONSOL_METRICS.forEach(([, label]) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        chr.appendChild(th);
    });
    cThead.appendChild(chr);
    consolTable.appendChild(cThead);
    const cTbody = document.createElement("tbody");

    const regionKeys = Object.keys(consol).sort();
    regionKeys.forEach((region) => {
        const tr = document.createElement("tr");
        const tdR = document.createElement("td");
        tdR.textContent = region;
        tdR.style.border = "1px solid #d9d9d9";
        tdR.style.padding = "6px 10px";
        tr.appendChild(tdR);
        const inner = consol[region] && typeof consol[region] === "object" ? consol[region] : {};
        let storageInput = null;
        let monthInput = null;
        CONSOL_METRICS.forEach(([field]) => {
            const td = document.createElement("td");
            td.style.border = "1px solid #d9d9d9";
            td.style.padding = "6px 10px";
            const inp = document.createElement("input");
            inp.type = "number";
            inp.step = "any";
            const raw = inner[field];
            inp.value = raw !== undefined && raw !== null ? raw : "";
            inp.dataset.consolRegion = region;
            inp.dataset.consolField = field;
            inp.style.width = "100%";
            inp.style.boxSizing = "border-box";
            inp.style.padding = "6px 8px";
            if (field === "month") {
                inp.readOnly = true;
                inp.title = "TotalStorage: Storage × Days Storage (computed on save)";
                inp.style.background = "#f4f4f4";
                monthInput = inp;
            }
            if (field === "storage") {
                storageInput = inp;
            }
            td.appendChild(inp);
            tr.appendChild(td);
        });
        const syncMonth = () => {
            if (!storageInput || !monthInput) {
                return;
            }
            const s = parseFloat(storageInput.value, 10);
            if (!Number.isNaN(s)) {
                monthInput.value = s * getDaysMultiplierFromForm();
            }
        };
        if (storageInput) {
            storageInput.addEventListener("input", syncMonth);
        }
        syncMonth();
        cTbody.appendChild(tr);
    });
    consolTable.appendChild(cTbody);
    wrap.appendChild(consolTable);

    const refreshAllConsolidationMonths = () => {
        const mult = getDaysMultiplierFromForm();
        for (const storageInp of consolTable.querySelectorAll(
            'input[data-consol-field="storage"]',
        )) {
            const tr = storageInp.closest("tr");
            if (!tr) {
                continue;
            }
            const monthInp = tr.querySelector('input[data-consol-field="month"]');
            const s = parseFloat(storageInp.value, 10);
            if (monthInp && !Number.isNaN(s)) {
                monthInp.value = s * mult;
            }
        }
    };

    const pullConsolidationFromServer = async () => {
        try {
            const res = await fetch("/api/consolidation");
            if (!res.ok) {
                return;
            }
            const payload = await res.json();
            for (const tr of consolTable.querySelectorAll("tbody tr")) {
                const region = tr.cells[0]?.textContent?.trim();
                if (!region || !payload[region]) {
                    continue;
                }
                const inner = payload[region];
                for (const field of ["bale", "storage", "month"]) {
                    const inp = tr.querySelector(`input[data-consol-field="${field}"]`);
                    if (
                        inp != null &&
                        inner[field] !== undefined &&
                        inner[field] !== null
                    ) {
                        inp.value = inner[field];
                    }
                }
            }
        } catch (e) {
            console.error(e);
        }
    };

    const consolBtnRow = document.createElement("div");
    consolBtnRow.style.marginTop = "12px";
    consolBtnRow.style.display = "flex";
    consolBtnRow.style.gap = "8px";
    consolBtnRow.style.alignItems = "center";
    const saveConsolBtn = document.createElement("button");
    saveConsolBtn.type = "button";
    saveConsolBtn.textContent = "Save consolidation";
    saveConsolBtn.style.padding = "8px 16px";
    saveConsolBtn.style.cursor = "pointer";
    saveConsolBtn.addEventListener("click", async () => {
        consolStatus.textContent = "";
        consolStatus.style.color = "";
        const body = {};
        for (const inp of wrap.querySelectorAll("input[data-consol-region]")) {
            const r = inp.dataset.consolRegion;
            const f = inp.dataset.consolField;
            const v = parseFloat(inp.value, 10);
            if (Number.isNaN(v)) {
                consolStatus.textContent = `Invalid number for ${r} (${f}).`;
                consolStatus.style.color = "#b00020";
                return;
            }
            if (!body[r]) {
                body[r] = {};
            }
            body[r][f] = v;
        }
        try {
            const res = await fetch("/api/consolidation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            consolStatus.textContent = "Consolidation saved.";
            consolStatus.style.color = "#1b5e20";
        } catch (err) {
            console.error(err);
            consolStatus.textContent = err.message || "Save failed.";
            consolStatus.style.color = "#b00020";
        }
    });
    consolBtnRow.appendChild(saveConsolBtn);
    wrap.appendChild(consolBtnRow);

    const DRAYAGE_FIELDS = [
        ["LineHaul", "Line Haul"],
        ["ChasSplit", "Chas Split"],
        ["Contrainer", "Contrainer"],
        ["Bale", "Bale"],
        ["OceanBase", "Ocean base"],
        ["Updated", "Updated"],
    ];
    const hdray = document.createElement("h3");
    hdray.style.marginTop = "28px";
    hdray.style.marginBottom = "8px";
    hdray.textContent = "Drayage";
    wrap.appendChild(hdray);

    const pdray = document.createElement("p");
    pdray.style.fontSize = "13px";
    pdray.style.color = "#444";
    pdray.style.maxWidth = "720px";
    pdray.style.lineHeight = "1.45";
    pdray.textContent =
        "Per-region Line Haul, chassis split, container, bale rate, ocean base, and updated note are saved to costings/data/drayage.json.";
    wrap.appendChild(pdray);

    wrap.appendChild(drayageStatus);

    const drayTable = document.createElement("table");
    drayTable.style.borderCollapse = "collapse";
    drayTable.style.marginTop = "8px";
    drayTable.style.minWidth = "640px";
    const drayThead = document.createElement("thead");
    const drayHr = document.createElement("tr");
    const chPort = document.createElement("th");
    chPort.textContent = "Port / region";
    chPort.style.border = "1px solid #d9d9d9";
    chPort.style.padding = "6px 10px";
    chPort.style.background = "#2f5fa7";
    chPort.style.color = "#fff";
    drayHr.appendChild(chPort);
    DRAYAGE_FIELDS.forEach(([, label]) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        drayHr.appendChild(th);
    });
    drayThead.appendChild(drayHr);
    drayTable.appendChild(drayThead);
    const drayTbody = document.createElement("tbody");

    const drayRegionKeys = Object.keys(drayageData).sort();
    drayRegionKeys.forEach((region) => {
        const tr = document.createElement("tr");
        const tdP = document.createElement("td");
        tdP.textContent = region;
        tdP.style.border = "1px solid #d9d9d9";
        tdP.style.padding = "6px 10px";
        tr.appendChild(tdP);
        const inner =
            drayageData[region] && typeof drayageData[region] === "object"
                ? drayageData[region]
                : {};
        DRAYAGE_FIELDS.forEach(([field]) => {
            const td = document.createElement("td");
            td.style.border = "1px solid #d9d9d9";
            td.style.padding = "6px 10px";
            const inp = document.createElement("input");
            if (field === "Updated") {
                inp.type = "text";
            } else {
                inp.type = "number";
                inp.step = "any";
            }
            const raw = inner[field];
            inp.value = raw !== undefined && raw !== null ? raw : "";
            inp.dataset.drayageRegion = region;
            inp.dataset.drayageField = field;
            inp.style.width = "100%";
            inp.style.boxSizing = "border-box";
            inp.style.padding = "6px 8px";
            td.appendChild(inp);
            tr.appendChild(td);
        });
        drayTbody.appendChild(tr);
    });
    drayTable.appendChild(drayTbody);
    wrap.appendChild(drayTable);

    const drayBtnRow = document.createElement("div");
    drayBtnRow.style.marginTop = "12px";
    drayBtnRow.style.display = "flex";
    drayBtnRow.style.gap = "8px";
    drayBtnRow.style.alignItems = "center";
    const saveDrayBtn = document.createElement("button");
    saveDrayBtn.type = "button";
    saveDrayBtn.textContent = "Save drayage";
    saveDrayBtn.style.padding = "8px 16px";
    saveDrayBtn.style.cursor = "pointer";
    saveDrayBtn.addEventListener("click", async () => {
        drayageStatus.textContent = "";
        drayageStatus.style.color = "";
        const body = {};
        for (const inp of wrap.querySelectorAll("input[data-drayage-region]")) {
            const r = inp.dataset.drayageRegion;
            const f = inp.dataset.drayageField;
            if (!body[r]) {
                body[r] = {};
            }
            if (f === "Updated") {
                body[r][f] = inp.value.trim();
            } else {
                const v = parseFloat(inp.value, 10);
                if (Number.isNaN(v)) {
                    drayageStatus.textContent = `Invalid number for ${r} (${f}).`;
                    drayageStatus.style.color = "#b00020";
                    return;
                }
                body[r][f] = v;
            }
        }
        try {
            const res = await fetch("/api/drayage", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            drayageStatus.textContent = "Drayage saved.";
            drayageStatus.style.color = "#1b5e20";
        } catch (err) {
            console.error(err);
            drayageStatus.textContent = err.message || "Save failed.";
            drayageStatus.style.color = "#b00020";
        }
    });
    drayBtnRow.appendChild(saveDrayBtn);
    wrap.appendChild(drayBtnRow);

    const DOC_CIF_FIELDS = [
        { key: "country", label: "Country", kind: "text" },
        { key: "GRI", label: "GRI", kind: "number", defaultZero: true },
        { key: "code", label: "Code", kind: "text" },
        { key: "LC", label: "LC", kind: "number" },
        { key: "INS", label: "INS", kind: "number" },
        { key: "CONT", label: "CONT", kind: "number" },
        { key: "COM", label: "COM", kind: "number" },
        { key: "COF", label: "COF", kind: "number" },
        { key: "CIQ_QC", label: "CIQ/QC", kind: "number" },
    ];

    const hDocCif = document.createElement("h3");
    hDocCif.style.marginTop = "28px";
    hDocCif.style.marginBottom = "8px";
    hDocCif.textContent = "Documentation / CIF (by country)";
    wrap.appendChild(hDocCif);

    const pDocCif = document.createElement("p");
    pDocCif.style.fontSize = "13px";
    pDocCif.style.color = "#444";
    pDocCif.style.maxWidth = "960px";
    pDocCif.style.lineHeight = "1.45";
    pDocCif.textContent =
        "Per-country GRI (defaults to 0), sight LC, insurance, controlling, commission, cost of funds, and CIQ/QC factors are stored in SQLite (document_cif). Leave other numeric cells blank to store null. Add or remove rows as needed, then save.";
    wrap.appendChild(pDocCif);

    wrap.appendChild(docCifStatus);

    const docCifTable = document.createElement("table");
    docCifTable.style.borderCollapse = "collapse";
    docCifTable.style.marginTop = "8px";
    docCifTable.style.minWidth = "920px";
    const docCifThead = document.createElement("thead");
    const docCifHr = document.createElement("tr");
    DOC_CIF_FIELDS.forEach(({ label }) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        docCifHr.appendChild(th);
    });
    const docCifThActions = document.createElement("th");
    docCifThActions.textContent = "";
    docCifThActions.style.border = "1px solid #d9d9d9";
    docCifThActions.style.padding = "6px 10px";
    docCifThActions.style.background = "#2f5fa7";
    docCifThActions.style.color = "#fff";
    docCifThActions.style.width = "88px";
    docCifHr.appendChild(docCifThActions);
    docCifThead.appendChild(docCifHr);
    docCifTable.appendChild(docCifThead);
    const docCifTbody = document.createElement("tbody");
    docCifTbody.id = "jarvis-doc-cif-tbody";

    function addJarvisDocCifRow(rowData) {
        const d = rowData || {};
        const tr = document.createElement("tr");
        DOC_CIF_FIELDS.forEach(({ key, kind, defaultZero }) => {
            const td = document.createElement("td");
            td.style.border = "1px solid #d9d9d9";
            td.style.padding = "6px 10px";
            const inp = document.createElement("input");
            inp.type = kind === "text" ? "text" : "number";
            if (kind === "number") {
                inp.step = "any";
            }
            const raw = d[key];
            if (kind === "number") {
                if (defaultZero) {
                    inp.value =
                        raw !== undefined && raw !== null && raw !== ""
                            ? raw
                            : "0";
                } else {
                    inp.value =
                        raw !== undefined && raw !== null && raw !== ""
                            ? raw
                            : "";
                }
            } else {
                inp.value = raw !== undefined && raw !== null ? String(raw) : "";
            }
            inp.dataset.docCifField = key;
            inp.style.width = "100%";
            inp.style.boxSizing = "border-box";
            inp.style.padding = "6px 8px";
            td.appendChild(inp);
            if (key === "country") {
                applyCountryThemeToTd(td, inp.value);
                inp.addEventListener("input", () => applyCountryThemeToTd(td, inp.value));
            }
            tr.appendChild(td);
        });
        const tdRm = document.createElement("td");
        tdRm.style.border = "1px solid #d9d9d9";
        tdRm.style.padding = "6px 10px";
        const rmBtn = document.createElement("button");
        rmBtn.type = "button";
        rmBtn.textContent = "Remove";
        rmBtn.style.fontSize = "12px";
        rmBtn.style.cursor = "pointer";
        rmBtn.addEventListener("click", () => {
            tr.remove();
        });
        tdRm.appendChild(rmBtn);
        tr.appendChild(tdRm);
        docCifTbody.appendChild(tr);
    }

    (Array.isArray(documentCifData) ? documentCifData : []).forEach((row) => {
        addJarvisDocCifRow(row);
    });

    docCifTable.appendChild(docCifTbody);
    wrap.appendChild(docCifTable);

    const docCifBtnRow = document.createElement("div");
    docCifBtnRow.style.marginTop = "12px";
    docCifBtnRow.style.display = "flex";
    docCifBtnRow.style.gap = "8px";
    docCifBtnRow.style.alignItems = "center";
    docCifBtnRow.style.flexWrap = "wrap";

    const addDocCifBtn = document.createElement("button");
    addDocCifBtn.type = "button";
    addDocCifBtn.textContent = "Add row";
    addDocCifBtn.style.padding = "8px 16px";
    addDocCifBtn.style.cursor = "pointer";
    addDocCifBtn.addEventListener("click", () => {
        addJarvisDocCifRow({ GRI: 0 });
    });

    const saveDocCifBtn = document.createElement("button");
    saveDocCifBtn.type = "button";
    saveDocCifBtn.textContent = "Save document / CIF";
    saveDocCifBtn.style.padding = "8px 16px";
    saveDocCifBtn.style.cursor = "pointer";
    saveDocCifBtn.addEventListener("click", async () => {
        docCifStatus.textContent = "";
        docCifStatus.style.color = "";
        const body = [];
        for (const tr of docCifTbody.querySelectorAll("tr")) {
            const rowObj = {};
            for (const { key, kind, defaultZero } of DOC_CIF_FIELDS) {
                const inp = tr.querySelector(`input[data-doc-cif-field="${key}"]`);
                if (!inp) {
                    continue;
                }
                if (kind === "text") {
                    rowObj[key] = inp.value.trim();
                } else {
                    const s = inp.value.trim();
                    if (s === "") {
                        rowObj[key] = defaultZero ? 0 : null;
                    } else {
                        const v = parseFloat(s);
                        if (Number.isNaN(v)) {
                            docCifStatus.textContent = `Invalid number for ${key} (${rowObj.country || "row"}).`;
                            docCifStatus.style.color = "#b00020";
                            return;
                        }
                        rowObj[key] = v;
                    }
                }
            }
            if (!rowObj.country && !rowObj.code) {
                const hasOther =
                    rowObj.GRI !== 0 ||
                    rowObj.LC != null ||
                    rowObj.INS != null ||
                    rowObj.CONT != null ||
                    rowObj.COM != null ||
                    rowObj.COF != null ||
                    rowObj.CIQ_QC != null;
                if (!hasOther) {
                    continue;
                }
            }
            body.push(rowObj);
        }
        try {
            const res = await fetch("/api/document-cif", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            documentCifData = await res.json();
            docCifTbody.replaceChildren();
            (Array.isArray(documentCifData) ? documentCifData : []).forEach((r) => {
                addJarvisDocCifRow(r);
            });
            docCifStatus.textContent = "Document / CIF saved.";
            docCifStatus.style.color = "#1b5e20";
        } catch (err) {
            console.error(err);
            docCifStatus.textContent = err.message || "Save failed.";
            docCifStatus.style.color = "#b00020";
        }
    });
    docCifBtnRow.appendChild(addDocCifBtn);
    docCifBtnRow.appendChild(saveDocCifBtn);
    wrap.appendChild(docCifBtnRow);

    const USA_FWD_TOTAL_KEYS = ["COO", "FHTO"];
    const USA_FWD_ROWS = [
        ["COO", "COO", "number"],
        ["FHTO", "FHTO", "number"],
        ["AVG_Shipment", "AVG Shipment", "number"],
        ["TOTAL", "TOTAL ((COO + FHTO) ÷ AVG Shipment)", "total"],
    ];

    const hUsaFwd = document.createElement("h3");
    hUsaFwd.style.marginTop = "28px";
    hUsaFwd.style.marginBottom = "8px";
    hUsaFwd.textContent = "USA forwarding cost";
    wrap.appendChild(hUsaFwd);

    const pUsaFwd = document.createElement("p");
    pUsaFwd.style.fontSize = "13px";
    pUsaFwd.style.color = "#444";
    pUsaFwd.style.maxWidth = "720px";
    pUsaFwd.style.lineHeight = "1.45";
    pUsaFwd.textContent =
        "Values are saved to costings/data/usa_forwarding_cost.json. TOTAL = (COO + FHTO) ÷ AVG Shipment.";
    wrap.appendChild(pUsaFwd);

    wrap.appendChild(usaFwdStatus);

    const usaFwdTable = document.createElement("table");
    usaFwdTable.style.borderCollapse = "collapse";
    usaFwdTable.style.marginTop = "8px";
    usaFwdTable.style.minWidth = "420px";
    const usaFwdThead = document.createElement("thead");
    const usaFwdHr = document.createElement("tr");
    ["Parameter", "Value"].forEach((label) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        usaFwdHr.appendChild(th);
    });
    usaFwdThead.appendChild(usaFwdHr);
    usaFwdTable.appendChild(usaFwdThead);
    const usaFwdTbody = document.createElement("tbody");

    function syncUsaFwdTotal() {
        let sum = 0;
        for (const k of USA_FWD_TOTAL_KEYS) {
            const el = usaFwdTable.querySelector(`input[data-usa-fwd-key="${k}"]`);
            if (!el) {
                continue;
            }
            const v = parseFloat(el.value, 10);
            sum += Number.isNaN(v) ? 0 : v;
        }
        const avgInp = usaFwdTable.querySelector('input[data-usa-fwd-key="AVG_Shipment"]');
        let divisor = avgInp ? parseFloat(avgInp.value) : 88;
        if (!divisor || Number.isNaN(divisor)) divisor = 88;
        const totalInp = usaFwdTable.querySelector('input[data-usa-fwd-key="TOTAL"]');
        if (totalInp) {
            const t = sum / divisor;
            totalInp.value = Math.round(t * 100) / 100;
        }
    }

    USA_FWD_ROWS.forEach(([key, label, kind]) => {
        const tr = document.createElement("tr");
        const tdL = document.createElement("td");
        tdL.textContent = label;
        tdL.style.border = "1px solid #d9d9d9";
        tdL.style.padding = "6px 10px";
        const tdR = document.createElement("td");
        tdR.style.border = "1px solid #d9d9d9";
        tdR.style.padding = "6px 10px";
        const inp = document.createElement("input");
        const raw = usaFwdData[key];
        if (kind === "text") {
            inp.type = "text";
            inp.value =
                raw !== undefined && raw !== null && raw !== ""
                    ? String(raw)
                    : "";
        } else if (kind === "total") {
            inp.type = "number";
            inp.step = "any";
            inp.readOnly = true;
            inp.title = "(COO + FHTO) ÷ AVG Shipment";
            inp.style.background = "#f4f4f4";
            inp.value = raw !== undefined && raw !== null ? raw : "";
        } else {
            inp.type = "number";
            inp.step = "any";
            inp.value = raw !== undefined && raw !== null ? raw : "";
        }
        inp.dataset.usaFwdKey = key;
        inp.style.width = "100%";
        inp.style.boxSizing = "border-box";
        inp.style.padding = "6px 8px";
        tdR.appendChild(inp);
        tr.appendChild(tdL);
        tr.appendChild(tdR);
        usaFwdTbody.appendChild(tr);
    });
    usaFwdTable.appendChild(usaFwdTbody);
    wrap.appendChild(usaFwdTable);

    for (const k of [...USA_FWD_TOTAL_KEYS, "AVG_Shipment"]) {
        const inp = usaFwdTable.querySelector(`input[data-usa-fwd-key="${k}"]`);
        if (inp) {
            inp.addEventListener("input", syncUsaFwdTotal);
        }
    }
    syncUsaFwdTotal();

    const usaFwdBtnRow = document.createElement("div");
    usaFwdBtnRow.style.marginTop = "12px";
    usaFwdBtnRow.style.display = "flex";
    usaFwdBtnRow.style.gap = "8px";
    usaFwdBtnRow.style.alignItems = "center";
    const saveUsaFwdBtn = document.createElement("button");
    saveUsaFwdBtn.type = "button";
    saveUsaFwdBtn.textContent = "Save USA forwarding cost";
    saveUsaFwdBtn.style.padding = "8px 16px";
    saveUsaFwdBtn.style.cursor = "pointer";
    saveUsaFwdBtn.addEventListener("click", async () => {
        usaFwdStatus.textContent = "";
        usaFwdStatus.style.color = "";
        const body = {};
        for (const k of USA_FWD_TOTAL_KEYS) {
            const inp = usaFwdTable.querySelector(`input[data-usa-fwd-key="${k}"]`);
            if (!inp) {
                continue;
            }
            const v = parseFloat(inp.value, 10);
            if (Number.isNaN(v)) {
                usaFwdStatus.textContent = `Invalid number for “${k}”.`;
                usaFwdStatus.style.color = "#b00020";
                return;
            }
            body[k] = v;
        }
        const avgInp = usaFwdTable.querySelector(
            'input[data-usa-fwd-key="AVG_Shipment"]',
        );
        body.AVG_Shipment = avgInp ? avgInp.value : "";
        try {
            const res = await fetch("/api/usa-forwarding-cost", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            usaFwdData = await res.json();
            usaFwdStatus.textContent = "USA forwarding cost saved.";
            usaFwdStatus.style.color = "#1b5e20";
        } catch (err) {
            console.error(err);
            usaFwdStatus.textContent = err.message || "Save failed.";
            usaFwdStatus.style.color = "#b00020";
        }
    });
    usaFwdBtnRow.appendChild(saveUsaFwdBtn);
    wrap.appendChild(usaFwdBtnRow);

    const themesH = document.createElement("h3");
    themesH.style.marginTop = "28px";
    themesH.style.marginBottom = "8px";
    themesH.textContent = "Themes";
    wrap.appendChild(themesH);

    const themesIntro = document.createElement("p");
    themesIntro.style.fontSize = "13px";
    themesIntro.style.color = "#444";
    themesIntro.style.maxWidth = "900px";
    themesIntro.style.lineHeight = "1.45";
    themesIntro.textContent =
        "SQLite table themes: Country, CountryAbbr (unique, used as primary key), Color (hex, e.g. #FF0000), and type (free text for your own grouping). " +
        "Export view matches Base (country name) to Country for background colors on the whole row; add or remove rows, edit cells, then Save themes (replaces all rows in the table).";
    wrap.appendChild(themesIntro);
    wrap.appendChild(themesStatus);

    const themesTable = document.createElement("table");
    themesTable.style.borderCollapse = "collapse";
    themesTable.style.marginTop = "8px";
    themesTable.style.minWidth = "520px";
    const themesThead = document.createElement("thead");
    const themesHeadTr = document.createElement("tr");
    ["Country", "CountryAbbr", "Color", "type", ""].forEach((label) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        themesHeadTr.appendChild(th);
    });
    themesThead.appendChild(themesHeadTr);
    themesTable.appendChild(themesThead);
    const themesTbody = document.createElement("tbody");
    themesTbody.id = "jarvis-themes-tbody";

    function addJarvisThemeRow(rowData) {
        const d = rowData || {};
        const tr = document.createElement("tr");
        function appendFieldCell(field, widthPx) {
            const td = document.createElement("td");
            td.style.border = "1px solid #d9d9d9";
            td.style.padding = "4px 6px";
            const inp = document.createElement("input");
            inp.type = "text";
            inp.value = d[field] != null ? String(d[field]) : "";
            inp.setAttribute("data-theme-field", field);
            inp.style.width = widthPx ? `${widthPx}px` : "100%";
            inp.style.boxSizing = "border-box";
            inp.style.padding = "6px 8px";
            if (field === "CountryAbbr") {
                inp.maxLength = 8;
                inp.style.textTransform = "uppercase";
            }
            td.appendChild(inp);
            tr.appendChild(td);
        }
        appendFieldCell("Country", 200);
        appendFieldCell("CountryAbbr", 88);
        appendFieldCell("Color", 100);
        appendFieldCell("type", 140);
        const tdRm = document.createElement("td");
        tdRm.style.border = "1px solid #d9d9d9";
        tdRm.style.padding = "4px 6px";
        const rmBtn = document.createElement("button");
        rmBtn.type = "button";
        rmBtn.textContent = "Remove";
        rmBtn.style.fontSize = "12px";
        rmBtn.style.cursor = "pointer";
        rmBtn.addEventListener("click", () => {
            tr.remove();
        });
        tdRm.appendChild(rmBtn);
        tr.appendChild(tdRm);
        const countryInp = tr.querySelector('input[data-theme-field="Country"]');
        if (countryInp && countryInp.parentElement) {
            applyCountryThemeToTd(countryInp.parentElement, countryInp.value);
            countryInp.addEventListener("input", () => {
                applyCountryThemeToTd(countryInp.parentElement, countryInp.value);
            });
        }
        themesTbody.appendChild(tr);
    }

    themesRows.forEach((r) => addJarvisThemeRow(r));

    themesTable.appendChild(themesTbody);
    wrap.appendChild(themesTable);

    const themesBtnRow = document.createElement("div");
    themesBtnRow.style.marginTop = "10px";
    themesBtnRow.style.display = "flex";
    themesBtnRow.style.gap = "8px";
    themesBtnRow.style.flexWrap = "wrap";
    themesBtnRow.style.alignItems = "center";

    const addThemeBtn = document.createElement("button");
    addThemeBtn.type = "button";
    addThemeBtn.textContent = "Add row";
    addThemeBtn.style.padding = "8px 16px";
    addThemeBtn.style.cursor = "pointer";
    addThemeBtn.addEventListener("click", () => {
        addJarvisThemeRow({});
    });

    const saveThemesBtn = document.createElement("button");
    saveThemesBtn.type = "button";
    saveThemesBtn.textContent = "Save themes";
    saveThemesBtn.style.padding = "8px 16px";
    saveThemesBtn.style.cursor = "pointer";
    saveThemesBtn.addEventListener("click", async () => {
        themesStatus.textContent = "";
        themesStatus.style.color = "";
        const rowsOut = [];
        for (const tr of themesTbody.querySelectorAll("tr")) {
            const row = {};
            for (const inp of tr.querySelectorAll("input[data-theme-field]")) {
                const f = inp.getAttribute("data-theme-field");
                row[f] = inp.value.trim();
            }
            const hasAny = row.CountryAbbr || row.Country || row.Color || row.type;
            if (!hasAny) {
                continue;
            }
            if (!row.CountryAbbr) {
                themesStatus.textContent = "Each non-empty row needs a CountryAbbr (unique).";
                themesStatus.style.color = "#b00020";
                return;
            }
            row.CountryAbbr = row.CountryAbbr.toUpperCase();
            rowsOut.push(row);
        }
        const abbrs = rowsOut.map((r) => r.CountryAbbr);
        if (new Set(abbrs).size !== abbrs.length) {
            themesStatus.textContent = "Duplicate CountryAbbr values are not allowed.";
            themesStatus.style.color = "#b00020";
            return;
        }
        try {
            const res = await fetch("/api/themes/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rows: rowsOut }),
            });
            const payload = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(payload.error || res.statusText);
            }
            themesStatus.textContent = `Saved ${payload.count ?? rowsOut.length} theme row(s).`;
            themesStatus.style.color = "#1b5e20";
            invalidateThemeCountryColorMapCache();
            const reload = await fetch("/api/themes");
            if (reload.ok) {
                const list = await reload.json();
                themesTbody.replaceChildren();
                (Array.isArray(list) ? list : []).forEach((r) => addJarvisThemeRow(r));
            }
        } catch (err) {
            console.error(err);
            themesStatus.textContent = err.message || "Save failed.";
            themesStatus.style.color = "#b00020";
        }
    });

    themesBtnRow.appendChild(addThemeBtn);
    themesBtnRow.appendChild(saveThemesBtn);
    wrap.appendChild(themesBtnRow);

    const h3 = document.createElement("h3");
    h3.style.marginTop = "28px";
    h3.style.marginBottom = "8px";
    h3.textContent = "Consolidation days storage";
    wrap.appendChild(h3);

    const p3 = document.createElement("p");
    p3.style.fontSize = "13px";
    p3.style.color = "#444";
    p3.style.maxWidth = "720px";
    p3.style.lineHeight = "1.45";
    p3.textContent =
        "Values saved to costings/data/consolidation_days_storage.json.";
    wrap.appendChild(p3);

    wrap.appendChild(cdsStatus);

    const cdsTable = document.createElement("table");
    cdsTable.style.borderCollapse = "collapse";
    cdsTable.style.marginTop = "8px";
    cdsTable.style.minWidth = "420px";
    const cdsThead = document.createElement("thead");
    const cdsHr = document.createElement("tr");
    ["Parameter", "Value"].forEach((label) => {
        const th = document.createElement("th");
        th.textContent = label;
        th.style.border = "1px solid #d9d9d9";
        th.style.padding = "6px 10px";
        th.style.background = "#2f5fa7";
        th.style.color = "#fff";
        cdsHr.appendChild(th);
    });
    cdsThead.appendChild(cdsHr);
    cdsTable.appendChild(cdsThead);
    const cdsTbody = document.createElement("tbody");

    Object.keys(cds)
        .sort()
        .forEach((key) => {
            const tr = document.createElement("tr");
            const tdL = document.createElement("td");
            tdL.textContent = key;
            tdL.style.border = "1px solid #d9d9d9";
            tdL.style.padding = "6px 10px";
            const tdR = document.createElement("td");
            tdR.style.border = "1px solid #d9d9d9";
            tdR.style.padding = "6px 10px";
            const inp = document.createElement("input");
            inp.type = "number";
            inp.step = "any";
            inp.value = cds[key];
            inp.setAttribute("data-cds-key", key);
            inp.style.width = "100%";
            inp.style.boxSizing = "border-box";
            inp.style.padding = "6px 8px";
            tdR.appendChild(inp);
            tr.appendChild(tdL);
            tr.appendChild(tdR);
            cdsTbody.appendChild(tr);
        });
    cdsTable.appendChild(cdsTbody);
    wrap.appendChild(cdsTable);

    const cdsBtnRow = document.createElement("div");
    cdsBtnRow.style.marginTop = "12px";
    cdsBtnRow.style.display = "flex";
    cdsBtnRow.style.gap = "8px";
    cdsBtnRow.style.alignItems = "center";
    const saveCdsBtn = document.createElement("button");
    saveCdsBtn.type = "button";
    saveCdsBtn.textContent = "Save consolidation days storage";
    saveCdsBtn.style.padding = "8px 16px";
    saveCdsBtn.style.cursor = "pointer";
    saveCdsBtn.addEventListener("click", async () => {
        cdsStatus.textContent = "";
        cdsStatus.style.color = "";
        const body = {};
        for (const inp of wrap.querySelectorAll("input[data-cds-key]")) {
            const k = inp.getAttribute("data-cds-key");
            const v = parseFloat(inp.value, 10);
            if (Number.isNaN(v)) {
                cdsStatus.textContent = `Invalid number for “${k}”.`;
                cdsStatus.style.color = "#b00020";
                return;
            }
            body[k] = v;
        }
        try {
            const res = await fetch("/api/consolidation-days-storage", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || res.statusText);
            }
            cdsStatus.textContent =
                "Saved. Consolidation months updated (saved to consolidation.json).";
            cdsStatus.style.color = "#1b5e20";
            await pullConsolidationFromServer();
        } catch (err) {
            console.error(err);
            cdsStatus.textContent = err.message || "Save failed.";
            cdsStatus.style.color = "#b00020";
        }
    });
    cdsBtnRow.appendChild(saveCdsBtn);
    wrap.appendChild(cdsBtnRow);

    for (const inp of wrap.querySelectorAll("input[data-cds-key]")) {
        inp.addEventListener("input", refreshAllConsolidationMonths);
    }
    refreshAllConsolidationMonths();

    content.appendChild(wrap);
}

async function select_view() {
    const selectElement = document.getElementById("select_view");
    const viewName = selectElement.options[selectElement.selectedIndex].text;
    document.title = "Costings - " + viewName;
    const content = document.getElementById("content");
    content.innerHTML = "";

    const derivPanel = document.getElementById("cell-derivation");
    if (derivPanel) { derivPanel.style.display = "none"; derivPanel.textContent = ""; }

    if (viewName === "Jarvis") {
        await renderControlPanelView();
        return;
    }

    if (viewName === "Notes") {
        await renderNotesView();
        return;
    }

    const config = getViewConfig(viewName);
    if (!config) {
        return;
    }

    if (viewName === "OTR") {
        await loadOtrRows(config);
        renderOtrTable(config);
        return;
    }

    if (viewName === "OCEAN") {
        await loadOceanRows(config);
        renderOceanTable(config);
        return;
    }

    if (viewName === "Ocean Costing") {
        await loadOceanCostingRows(config);
        renderOceanCostingTable(config);
        return;
    }

    if (viewName === "Seam Tariffs") {
        await loadSeamTariffRows(config);
        renderSeamTariffTable(config);
        return;
    }
    if (viewName === "Cert Tariffs") {
        await loadCertTariffRows(config);
        renderTariffTable(config);
        return;
    }
    if (viewName === "USD") {
        await loadUsdRows(config);
        renderUsdTable(config);
        return;
    }

    if (viewName === "PTS") {
        await loadPtsRows(config);
        renderPtsTable(config);
        return;
    }

    if (viewName === "CIF") {
        await loadCifRows(config);
        renderCifTable(config);
        return;
    }

    if (viewName === "Regions and Ports") {
        await loadRegionsAndPortsRows(config);
        renderRegionsAndPortsTable(config);
        return;
    }

    if (viewName === "Export") {
        renderExportTable();
        return;
    }

    renderBasicTable(config.columns, config.rows);
}

async function renderNotesView() {
    const content = document.getElementById("content");
    content.innerHTML = "<p>Loading tables...</p>";

    let tablesRaw = [];
    try {
        const resp = await fetch("/api/db-tables");
        tablesRaw = await resp.json();
    } catch (e) {
        content.innerHTML = "<p style='color:red;'>Failed to load table list.</p>";
        return;
    }

    const tables = tablesRaw.filter((t) => t !== "ocean_costing_rules");
    const initialTable = tables[0] || "";

    const options = tables
        .map((t) => `<option value="${t}"${t === initialTable ? " selected" : ""}>${t}</option>`)
        .join("");
    content.innerHTML = `<div style="font-family:Arial,sans-serif;">
        <p style="font-size:12px; color:#555; margin:0 0 10px 0;">
            Browse any SQLite table (versioned tables support <code>is_active</code> when the checkbox is on).
        </p>
        <div style="margin-bottom:12px;">
            <label style="font-size:13px; font-weight:bold; margin-right:8px;">Table:</label>
            <select id="db-table-select" style="padding:5px 8px; border:1px solid #ccc; border-radius:4px; font-size:13px;">
                ${options}
            </select>
            <label style="margin-left:16px; font-size:13px; cursor:pointer;">
                <input type="checkbox" id="db-active-toggle" checked style="margin-right:4px; cursor:pointer;" />
                Active only
            </label>
            <span id="db-row-count" style="margin-left:12px; font-size:12px; color:#666;"></span>
        </div>
        <div id="db-table-output"></div>
    </div>`;

    const sel = document.getElementById("db-table-select");
    const toggle = document.getElementById("db-active-toggle");

    async function loadTable(tableName) {
        const out = document.getElementById("db-table-output");
        const countEl = document.getElementById("db-row-count");
        out.innerHTML = "<p style='font-size:13px; color:#888;'>Loading...</p>";
        countEl.textContent = "";
        const activeOnly = toggle.checked ? "1" : "0";
        try {
            const resp = await fetch("/api/db-query?table=" + encodeURIComponent(tableName) + "&active_only=" + activeOnly);
            const data = await resp.json();
            if (data.error) {
                out.innerHTML = `<p style='color:red; font-size:13px;'>${data.error}</p>`;
                return;
            }
            const cols = data.columns || [];
            const rows = data.rows || [];
            countEl.textContent = `(${rows.length} row${rows.length !== 1 ? "s" : ""})`;
            if (!cols.length) {
                out.innerHTML = "<p style='font-size:13px; color:#888;'>No columns.</p>";
                return;
            }
            const themeMap = await getThemeCountryColorMapCached();
            let thtml = "<table><thead><tr>";
            for (const c of cols) thtml += `<th>${c}</th>`;
            thtml += "</tr></thead><tbody>";
            for (const row of rows) {
                const inactive = row["is_active"] === 0;
                const rowStyle = inactive ? " style='background:#f5e6e6; color:#999;'" : "";
                thtml += `<tr${rowStyle}>`;
                for (const c of cols) {
                    const val = row[c];
                    const display = val === null ? "<span style='color:#aaa;'>NULL</span>" : String(val).replace(/</g, "&lt;");
                    const isNum = val !== null && val !== "" && !isNaN(val);
                    let bgAttr = "";
                    if (_isThemeCountryColumn(c) && val != null && String(val).trim() !== "") {
                        const bg = _exportBaseCellBackground(String(val), themeMap);
                        if (bg) {
                            const safe = String(bg).replace(/"/g, "");
                            bgAttr = ` style="background-color:${safe}"`;
                        }
                    }
                    thtml += `<td class="${isNum ? "td-num" : "td-text"}"${bgAttr}>${display}</td>`;
                }
                thtml += "</tr>";
            }
            thtml += "</tbody></table>";
            out.innerHTML = thtml;
        } catch (e) {
            out.innerHTML = `<p style='color:red; font-size:13px;'>Request failed.</p>`;
        }
    }

    function reload() { loadTable(sel.value); }
    sel.addEventListener("change", reload);
    toggle.addEventListener("change", reload);
    if (tables.length) loadTable(initialTable);
}

async function loadOtrRows(config) {
    config.otrLoadError = null;
    try {
        const response = await fetch("/api/otr");
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail =
                payload.error ||
                payload.hint ||
                (payload.path ? `Expected file: ${payload.path}` : "") ||
                response.statusText;
            const err = new Error(
                `Failed to load OTR rows (${response.status})${detail ? `: ${detail}` : ""}`
            );
            Object.assign(err, { payload });
            throw err;
        }
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.otrLoadError = error.message || String(error);
        if (error.payload?.traceback) {
            console.error(error.payload.traceback);
        }
        config.rows = [];
    }
}

async function loadOceanRows(config) {
    try {
        const response = await fetch("/api/ocean");
        if (!response.ok) {
            throw new Error(`Failed to load OCEAN rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

function _oceanCostingCompoundKey(row) {
    const port = String(row.Port ?? "").trim().toUpperCase();
    const dest = String(row.Destination ?? "").trim().toUpperCase();
    const country = String(row.Country ?? "").trim().toUpperCase();
    return `${port}\x1f${dest}\x1f${country}`;
}

/** SCACs used for Ocean Costing averages (matches server CSV `scacCode`). */
const OCEAN_COSTING_CMDU_MAEU_SCACS = new Set(["CMDU", "MAEU"]);

const OCEAN_COSTING_RULE_CHEAPEST = new Set([
    "china",
    "indonesia",
    "thailand",
    "taiwan",
    "vietnam",
    "korea",
    "japan",
    "malaysia",
    "spain",
    "italy",
]);

const OCEAN_COSTING_RULE_CMDU_MAEU_MEAN = new Set([
    "peru",
    "guatemala",
    "honduras",
    "nicaragua",
    "colombia",
    "ecuador",
    "costa rica",
    "el salvador",
]);

const OCEAN_COSTING_RULE_TOP3_CMDU_MAEU_MEAN = new Set(["bangladesh", "turkey", "pakistan", "india"]);

function _oceanCostingCanonicalCountryName(countryRaw) {
    const c = String(countryRaw ?? "").trim().toLowerCase();
    if (c === "south korea" || c === "republic of korea") {
        return "korea";
    }
    if (c === "pakastan") {
        return "pakistan";
    }
    return c;
}

function _oceanCostingFreightRuleForCountry(countryRaw) {
    const c = _oceanCostingCanonicalCountryName(countryRaw);
    if (OCEAN_COSTING_RULE_CHEAPEST.has(c)) {
        return "cheapest";
    }
    if (OCEAN_COSTING_RULE_CMDU_MAEU_MEAN.has(c)) {
        return "cmdumaeu_mean";
    }
    if (OCEAN_COSTING_RULE_TOP3_CMDU_MAEU_MEAN.has(c)) {
        return "cmdumaeu_top3_mean";
    }
    return "cheapest";
}

function _parseOceanCostingNumber(value) {
    if (value === null || value === undefined || value === "") {
        return NaN;
    }
    if (typeof value === "number") {
        return Number.isFinite(value) ? value : NaN;
    }
    const n = parseFloat(String(value).replace(/,/g, ""));
    return Number.isFinite(n) ? n : NaN;
}

function _normOceanCostingScac(scac) {
    return String(scac ?? "").trim().toUpperCase();
}

function _roundOceanCostingMoney(n) {
    if (!Number.isFinite(n)) {
        return n;
    }
    return Math.round(n * 100) / 100;
}

function _meanFiniteOceanCosting(nums) {
    const ok = nums.filter(Number.isFinite);
    if (!ok.length) {
        return NaN;
    }
    return ok.reduce((a, b) => a + b, 0) / ok.length;
}

function _cheapestOceanFreightAmongRows(rows) {
    let best = NaN;
    for (const r of rows) {
        const n = _parseOceanCostingNumber(r["Ocean Freight"]);
        if (Number.isFinite(n) && (!Number.isFinite(best) || n < best)) {
            best = n;
        }
    }
    return best;
}

function _cmdumaeuOceanFreightValues(rows) {
    const out = [];
    for (const r of rows) {
        if (!OCEAN_COSTING_CMDU_MAEU_SCACS.has(_normOceanCostingScac(r.SCAC))) {
            continue;
        }
        const n = _parseOceanCostingNumber(r["Ocean Freight"]);
        if (Number.isFinite(n)) {
            out.push(n);
        }
    }
    return out;
}

function _computeOceanCostingAggregateFreight(rows, rule) {
    const cheapest = _cheapestOceanFreightAmongRows(rows);
    if (rule === "cheapest") {
        return cheapest;
    }
    if (rule === "cmdumaeu_mean") {
        const pool = _cmdumaeuOceanFreightValues(rows);
        if (pool.length) {
            return _meanFiniteOceanCosting(pool);
        }
        return cheapest;
    }
    if (rule === "cmdumaeu_top3_mean") {
        const scored = rows
            .filter((r) => OCEAN_COSTING_CMDU_MAEU_SCACS.has(_normOceanCostingScac(r.SCAC)))
            .map((r) => _parseOceanCostingNumber(r["Ocean Freight"]))
            .filter(Number.isFinite)
            .sort((a, b) => a - b);
        const top3 = scored.slice(0, 3);
        if (top3.length) {
            return _meanFiniteOceanCosting(top3);
        }
        return cheapest;
    }
    return cheapest;
}

function _pickOceanCostingRepresentativeRow(rows) {
    let best = null;
    let bestN = NaN;
    for (const r of rows) {
        const n = _parseOceanCostingNumber(r["Ocean Freight"]);
        if (!Number.isFinite(n)) {
            continue;
        }
        if (!best || n < bestN) {
            best = r;
            bestN = n;
        }
    }
    return best || rows[0] || {};
}

function _oceanCostingRowFromOcean(row, rowNum, columns) {
    const out = {};
    for (const col of columns) {
        if (col === "Row") {
            out[col] = rowNum;
        } else {
            out[col] = row[col] ?? "";
        }
    }
    return out;
}

function dedupeOceanCostingRows(rawRows, columns) {
    const byKey = new Map();
    for (const r of rawRows) {
        const k = _oceanCostingCompoundKey(r);
        if (!byKey.has(k)) {
            byKey.set(k, []);
        }
        byKey.get(k).push(r);
    }
    const orderedKeys = [];
    const seen = new Set();
    for (const r of rawRows) {
        const k = _oceanCostingCompoundKey(r);
        if (seen.has(k)) {
            continue;
        }
        seen.add(k);
        orderedKeys.push(k);
    }
    const merged = [];
    for (const k of orderedKeys) {
        const group = byKey.get(k) || [];
        if (!group.length) {
            continue;
        }
        const country = group[0].Country ?? "";
        const rule = _oceanCostingFreightRuleForCountry(country);
        const freight = _computeOceanCostingAggregateFreight(group, rule);
        const base = { ..._pickOceanCostingRepresentativeRow(group) };
        const gri = _parseOceanCostingNumber(base.GRI);
        const griN = Number.isFinite(gri) ? gri : 0;
        if (Number.isFinite(freight)) {
            base["Ocean Freight"] = _roundOceanCostingMoney(freight);
            const oceanTotal = freight + griN;
            base["Ocean Total"] = _roundOceanCostingMoney(oceanTotal);
            base["Total pts"] = _roundOceanCostingMoney((oceanTotal / 88.0) * 20.0);
        }
        merged.push(base);
    }
    return merged.map((r, i) => _oceanCostingRowFromOcean(r, i + 1, columns));
}

async function loadOceanCostingRows(config) {
    try {
        const response = await fetch("/api/ocean");
        if (!response.ok) {
            throw new Error(`Failed to load Ocean Costing rows (${response.status})`);
        }
        const payload = await response.json();
        const raw = Array.isArray(payload.rows) ? payload.rows : [];
        config.rows = dedupeOceanCostingRows(raw, config.columns);
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadSeamTariffRows(config) {
    try {
        const response = await fetch("/api/seam-tariffs");
        if (!response.ok) {
            throw new Error(`Failed to load Seam Tariffs rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadCertTariffRows(config) {
    try {
        const response = await fetch("/api/cert-tariffs");
        if (!response.ok) {
            throw new Error(`Failed to load Cert Tariffs rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadUsdRows(config) {
    try {
        const response = await fetch("/api/usd");
        if (!response.ok) {
            throw new Error(`Failed to load USD rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadPtsRows(config) {
    try {
        const response = await fetch("/api/pts");
        if (!response.ok) {
            throw new Error(`Failed to load PTS rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadCifRows(config, ignoreZeros = true) {
    try {
        const included = getPtsIncluded();
        const params = new URLSearchParams({
            ignore_zeros: ignoreZeros ? "1" : "0",
        });
        if (included !== null) {
            params.set("included", included.join(","));
        }
        const response = await fetch(`/api/cif?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`Failed to load CIF rows (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

async function loadRegionsAndPortsRows(config) {
    try {
        const response = await fetch("/api/regions-and-ports");
        if (!response.ok) {
            throw new Error(`Failed to load Regions and Ports (${response.status})`);
        }
        const payload = await response.json();
        config.rows = Array.isArray(payload.rows) ? payload.rows : [];
    } catch (error) {
        console.error(error);
        config.rows = [];
    }
}

/**
 * Collapsible notes under the OTR table: where each column comes from (Flask /api/otr, server.py).
 */
function createOtrColumnDiscussion() {
    const details = document.createElement("details");
    details.style.marginTop = "14px";
    details.style.maxWidth = "960px";
    details.style.fontSize = "13px";
    details.style.lineHeight = "1.5";
    details.style.color = "#222";

    const summary = document.createElement("summary");
    summary.textContent = "How OTR column values are derived";
    summary.style.cursor = "pointer";
    summary.style.fontWeight = "600";
    details.appendChild(summary);

    const box = document.createElement("div");
    box.style.marginTop = "10px";
    box.style.padding = "10px 12px";
    box.style.border = "1px solid #d9d9d9";
    box.style.borderRadius = "6px";
    box.style.background = "#f8f9fb";

    const p1 = document.createElement("p");
    p1.style.marginTop = "0";
    p1.textContent =
        "Data is built in costings/html/server.py (route /api/otr) from OTR_Rates.csv (per lane). " +
        "Fuel Surcharge and OTR GRI for OTR come from Jarvis (data/control_panel.json).";
    box.appendChild(p1);

    const ul = document.createElement("ul");
    ul.style.margin = "8px 0 0 0";
    ul.style.paddingLeft = "1.2em";

    const items = [
        "Row — 1-based index in the order rows appear in OTR_Rates.csv.",
        "Origin City / Origin State — Split from column ORIGINCITY: text before the first comma is city, after is state.",
        "Dest City / Dest State — Same split for DESTINATIONCITY.",
        "Cargo Type — CARGOTYPE from the lane row.",
        "LH (line haul) — Numeric BASE RATE from that lane row.",
        "FSC — Jarvis → Fuel Surcharge (same value on every row).",
        "GRI — Jarvis → OTR GRI (same for every lane).",
        "Final — (LH × FSC) + GRI, using the Fuel Surcharge value shown in the FSC column.",
        "PTS — (Final / 88) × 20 (same 88-pt scale used elsewhere in this app).",
        "Last Updated / Expiration — UPDATEDATE and EXPIRATIONDATE from the lane row.",
        "Previous — Prior line-haul (same basis as LH), from the lane row column PRIOR BASE RATE (also accepted: PREVIOUS BASE RATE, PREVIOUS RATE, PRIOR RATE). If that cell is empty, Previous and Delta are left blank.",
        "Delta — LH − prior line-haul when a prior value is present; otherwise blank.",
    ];
    for (const text of items) {
        const li = document.createElement("li");
        li.textContent = text;
        li.style.marginBottom = "6px";
        ul.appendChild(li);
    }
    box.appendChild(ul);
    details.appendChild(box);
    return details;
}

/**
 * Collapsible notes under the USD table: data sources and formulas (Flask /api/usd, server.py).
 */
function createUsdColumnDiscussion() {
    const details = document.createElement("details");
    details.style.marginTop = "14px";
    details.style.maxWidth = "960px";
    details.style.fontSize = "13px";
    details.style.lineHeight = "1.5";
    details.style.color = "#222";

    const summary = document.createElement("summary");
    summary.textContent = "How USD column values are derived or calculated";
    summary.style.cursor = "pointer";
    summary.style.fontWeight = "600";
    details.appendChild(summary);

    const box = document.createElement("div");
    box.style.marginTop = "10px";
    box.style.padding = "10px 12px";
    box.style.border = "1px solid #d9d9d9";
    box.style.borderRadius = "6px";
    box.style.background = "#f8f9fb";

    const intro = document.createElement("p");
    intro.style.marginTop = "0";
    intro.textContent =
        "Built in costings/html/server.py (GET /api/usd). Each output row is one warehouse " +
        "(from regions_and_ports.csv) merged with the same Warehouse row in " +
        "SEAM_TARIFFS_CERT_TARIFFS.csv. Global interest and commission come from " +
        "Jarvis (data/control_panel.json). Transit Truck uses the same FINAL as the OTR view " +
        "(from OTR_Rates.csv for that city/port lane), then ÷ 88.";
    box.appendChild(intro);

    const ul = document.createElement("ul");
    ul.style.margin = "8px 0 0 0";
    ul.style.paddingLeft = "1.2em";

    const items = [
        "Row — Output order: rows sorted by Warehouse (numeric) then Port; then numbered 1…n.",
        "Warehouse, Name, City, State — Warehouse from regions_and_ports.csv; Name/City/State prefer SEAM when present, else that file.",
        "Region, Export, Port — From regions_and_ports.csv. Certain warehouses are duplicated: a second row is added with Region set to WTXH and Port to Houston or Weslaco (see duplicated_warehouses in server.py).",
        "Terms; Recv, Load, Compr, Class, Mark — From SEAM_TARIFFS_CERT_TARIFFS.csv for that warehouse (matched by Warehouse id). Terms is stripped of leading zeros in the API.",
        "Storage (Strg) — Also from SEAM_TARIFFS_CERT_TARIFFS.csv (Strg column). If Strg is under 1.0, server.py treats it as a per-day rate and multiplies by 30 to show a monthly value in USD. This is a normalization rule so daily-storage tariffs are comparable with monthly-storage tariffs in one column.",
        "ESO — Looked up by Warehouse id in regions_and_ports.csv (ESO column).",
        "Interest — Global: (EDF Interest Rate / 100 / 12) × (Avg Purchase Price × Avg Bale Weight) from Jarvis; 0 if any of those three inputs is missing/ zero.",
        "Origin Comm — Global: Jarvis → Origin Commission (same for every row).",
        "Total Equity — Recv + Load + Compr + Class + Mark + Strg + ESO + Interest + Origin Comm.",
        "Total Origin — Depends on Terms: 1 → Strg + Interest + Origin Comm; 2 → Compr + Strg + Interest + Origin Comm; 3 → Load + Compr + Strg + Class + Interest + Origin Comm; 4 → Class + Interest + Origin Comm; otherwise 0.",
        "Flatbed, Late Fee — Looked up by Warehouse id in regions_and_ports.csv (“Flat Bed Fees” and “Late Fees”).",
        "Transit Truck — Take the FINAL rate from the OTR (OTR_Rates.csv, same as the OTR view) for that warehouse city and export port, then divide that value by 88. If there is no matching OTR lane, Transit Truck is 0.",
        "Total Transit — Flatbed + Late Fee + Transit Truck.",
        "Consolidation — InAndOut (Consol_Block): per row, Port → consolidation.json region → bale. TotalStorage (Consol_Strg): same Port → region → TotalStorage column (stored key month = Storage × Days Storage). Port “Weslaco” uses Houston’s consolidation row. Unmapped ports use Jarvis fallbacks (InAndOut, TotalStorage). Interest (Consol_Interest): (Avg Purchase Price × EDF Interest Rate ÷ 100 × Avg Bale Weight) ÷ 52 × (Days Storage ÷ 7). Total Consol: InAndOut + TotalStorage + Interest for that row. Outbound — Dray: Port → drayage.json → Bale; Ocean: same mapping → OceanBase ÷ 88. Total_Out: Dray + Ocean. Documentation — Sight LC: China LC ÷ 20; Forwarding: Jarvis usa_forwarding TOTAL ((COO + FHTO) ÷ 88); Controlling: China CONT ÷ 20; Insurance: China INS ÷ 20 (all same every row). Total Doc: sum of those four. CIF — Dest Com: China COM ÷ 20; CoF: China COF ÷ 20; Qclaim: China CIQ_QC ÷ 20 (0 if null). Total CIF: sum of those three. Weslaco / Shelby transit — per server implementation.",
    ];
    for (const text of items) {
        const li = document.createElement("li");
        li.textContent = text;
        li.style.marginBottom = "6px";
        ul.appendChild(li);
    }
    box.appendChild(ul);
    details.appendChild(box);
    return details;
}

/**
 * Notes under the PTS table: same rows as USD with monetary columns × 20 (points), 2 dp.
 */
function createPtsColumnDiscussion() {
    const details = document.createElement("details");
    details.style.marginTop = "14px";
    details.style.maxWidth = "960px";
    details.style.fontSize = "13px";
    details.style.lineHeight = "1.5";
    details.style.color = "#222";

    const summary = document.createElement("summary");
    summary.textContent = "How PTS values relate to USD";
    summary.style.cursor = "pointer";
    summary.style.fontWeight = "600";
    details.appendChild(summary);

    const box = document.createElement("div");
    box.style.marginTop = "10px";
    box.style.padding = "10px 12px";
    box.style.border = "1px solid #d9d9d9";
    box.style.borderRadius = "6px";
    box.style.background = "#f8f9fb";

    const p = document.createElement("p");
    p.style.marginTop = "0";
    p.textContent =
        "PTS is built in costings/html/server.py (GET /api/pts) from the same underlying row as USD (GET /api/usd). " +
        "Each numeric USD cell × 20 is rounded half-up to two decimal places. Identifiers are unchanged. " +
        "Total Terms — Cash: (Total Origin + Total Transit + Total_Consol + Total_Out + Total_Doc + Total_CIF) in USD × 20, rounded half-up to 2 dp. " +
        "Equity: (Total Equity + Total Transit + Total_Consol + Total_Out + Total_Doc + Total_CIF) × 20, rounded half-up to 2 dp.";
    box.appendChild(p);
    details.appendChild(box);
    return details;
}

/**
 * Notes under the CIF table: PTS columns grouped by region list from Jarvis JSON.
 */
function createCifColumnDiscussion() {
    const details = document.createElement("details");
    details.style.marginTop = "14px";
    details.style.maxWidth = "960px";
    details.style.fontSize = "13px";
    details.style.lineHeight = "1.5";
    details.style.color = "#222";

    const summary = document.createElement("summary");
    summary.textContent = "How CIF rows are built";
    summary.style.cursor = "pointer";
    summary.style.fontWeight = "600";
    details.appendChild(summary);

    const box = document.createElement("div");
    box.style.marginTop = "10px";
    box.style.padding = "10px 12px";
    box.style.border = "1px solid #d9d9d9";
    box.style.borderRadius = "6px";
    box.style.background = "#f8f9fb";

    box.innerHTML =
        "<p style='margin-top:0'><strong>Overview:</strong> CIF is served by GET /api/cif. " +
        "Row order follows the <code>cif_regions</code> array in <code>usa_forwarding_cost.json</code>. " +
        "For each region label, every column except Total Terms is the average of that PTS column over rows whose Region matches " +
        "(Terms = most common). Weslaco and Shelby transit columns are omitted. " +
        "The <em>Ignore 0s</em> toggle controls whether zeros are excluded from averages (default: yes).</p>" +

        "<p><strong>WTXH special case:</strong> WTXH has no warehouses assigned in <code>regions_and_ports.csv</code>. " +
        "The Origin Warehouse columns (Terms through Total Origin) use the <strong>WTX</strong> warehouses as an alias. " +
        "All other columns (Transit, Consolidation, Outbound, etc.) use WTXH-specific data.</p>" +

        "<p><strong>Consolidation (Consol_Block, Consol_Strg, Total_Consol):</strong> " +
        "Each warehouse's consolidation costs depend on its <strong>Port</strong> (from <code>regions_and_ports.csv</code>), " +
        "which maps to a consolidation region in <code>consolidation.json</code>:</p>" +
        "<ul style='margin:4px 0 8px 20px'>" +
        "<li><strong>WTX</strong> → all Port=Dallas (52 warehouses) → Dallas consol rates</li>" +
        "<li><strong>STEX</strong> → all Port=Houston (28) → Houston consol rates</li>" +
        "<li><strong>Memphis Rule 5</strong> → Port=Memphis (64) + Port=Houston (9) → mixed Memphis/Houston rates</li>" +
        "<li><strong>Eastern Rule 5</strong> → Port=Savannah (71) + Port=Memphis (8) → mixed Savannah/Memphis rates</li>" +
        "<li><strong>GA 30 Day</strong> → all Port=Savannah (68) → Savannah consol rates</li>" +
        "<li><strong>Southwest</strong> → all Port=Los Angeles (12) → no consol region match (falls back to Control Panel defaults)</li>" +
        "</ul>" +
        "<p>So regions with mixed Ports (Eastern Rule 5, Memphis Rule 5) will average different consol rates together.</p>" +

        "<p><strong>Total Terms:</strong> " +
        "Cash = Total Origin + Total Transit + Total_Consol + Total_Out + Total_Doc + Total_CIF. " +
        "Equity = Total Equity + Total Transit + Total_Consol + Total_Out + Total_Doc + Total_CIF.</p>";

    details.appendChild(box);
    return details;
}

function renderOtrTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const originInput = document.createElement("input");
    const destInput = document.createElement("input");

    originInput.placeholder = "Search Origin (city or state)";
    destInput.placeholder = "Search Destination (city or state)";
    originInput.id = "otr-search-origin";
    destInput.id = "otr-search-dest";

    controls.appendChild(originInput);
    controls.appendChild(destInput);
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    controls.style.flexWrap = "wrap";
    controls.style.alignItems = "center";

    // --- Local file compare controls ---
    const localSelect = document.createElement("select");
    localSelect.style.fontSize = "12px";
    localSelect.innerHTML = '<option value="">-- select local file --</option>';
    controls.appendChild(localSelect);

    const localCompareBtn = document.createElement("button");
    localCompareBtn.textContent = "Compare Local";
    localCompareBtn.style.padding = "6px 12px";
    localCompareBtn.style.fontSize = "12px";
    controls.appendChild(localCompareBtn);

    const applyBtn = document.createElement("button");
    applyBtn.textContent = "Apply Changes";
    applyBtn.style.padding = "6px 12px";
    applyBtn.style.fontSize = "12px";
    applyBtn.style.display = "none";
    controls.appendChild(applyBtn);

    const statusMsg = document.createElement("span");
    statusMsg.style.fontSize = "12px";
    statusMsg.style.color = "#555";
    controls.appendChild(statusMsg);

    // Populate local file dropdown
    fetch("/api/otr/local-files")
        .then(r => r.json())
        .then(data => {
            (data.files || []).forEach(f => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.textContent = f;
                localSelect.appendChild(opt);
            });
        })
        .catch(() => {});

    content.appendChild(controls);

    // Legend
    const legend = document.createElement("div");
    legend.style.fontSize = "11px";
    legend.style.marginBottom = "8px";
    legend.style.display = "none";
    legend.innerHTML =
        '<span style="background:#d4edda;padding:2px 6px;margin-right:8px;">Updated LH</span>' +
        '<span style="background:#d6eaf8;padding:2px 6px;margin-right:8px;">Unchanged</span>' +
        '<span style="background:#f8d7da;padding:2px 6px;margin-right:8px;">In system, not in file</span>' +
        '<span style="background:#fff9c4;padding:2px 6px;">New (in file, not in system)</span>';
    content.appendChild(legend);

    if (config.otrLoadError) {
        const errBox = document.createElement("p");
        errBox.style.cssText = "color:#b00020;font-size:13px;max-width:900px;white-space:pre-wrap;";
        errBox.textContent = config.otrLoadError;
        content.appendChild(errBox);
    }

    const tableHost = document.createElement("div");
    tableHost.id = "otr-table-host";
    content.appendChild(tableHost);

    content.appendChild(createOtrColumnDiscussion());

    let displayColumns = config.columns.filter(c => c !== "_status" && c !== "_changed_fields");
    const sortState = { column: null, ascending: true };
    let lastLocalFile = null;

    const draw = () => {
        const filteredRows = filterOtrRows(config.rows, originInput.value, destInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, displayColumns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    originInput.addEventListener("input", draw);
    destInput.addEventListener("input", draw);

    localCompareBtn.addEventListener("click", async () => {
        const filename = localSelect.value;
        if (!filename) {
            statusMsg.textContent = "Please select a file first.";
            return;
        }
        lastLocalFile = filename;
        statusMsg.textContent = "Comparing...";
        try {
            const resp = await fetch("/api/otr/compare-local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename })
            });
            if (!resp.ok) throw new Error(`Compare failed (${resp.status})`);
            const payload = await resp.json();
            config.rows = Array.isArray(payload.rows) ? payload.rows : [];
            legend.style.display = "block";
            applyBtn.style.display = "inline-block";
            const counts = { updated: 0, unchanged: 0, removed: 0, "new": 0 };
            config.rows.forEach(r => { if (r._status) counts[r._status]++; });
            statusMsg.textContent = `${counts.updated} updated, ${counts["new"]} new, ${counts.removed} removed, ${counts.unchanged} unchanged`;
            draw();
        } catch (err) {
            statusMsg.textContent = err.message;
        }
    });

    applyBtn.addEventListener("click", async () => {
        if (!lastLocalFile) return;
        showProgressModal("Saving OTR rates...");
        try {
            const resp = await fetch("/api/otr/apply-local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: lastLocalFile })
            });
            if (!resp.ok) throw new Error(`Apply failed (${resp.status})`);
            const payload = await resp.json();
            document.getElementById("progress-modal-msg").textContent = "Reloading data...";
            await loadOtrRows(config);
            hideProgressModal();
            statusMsg.textContent = `Applied. ${payload.updated || 0} updated, ${payload.new || 0} new.`;
            applyBtn.style.display = "none";
            legend.style.display = "none";
            draw();
        } catch (err) {
            hideProgressModal();
            statusMsg.textContent = err.message;
        }
    });

    draw();
}

function renderOceanTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const portInput = document.createElement("input");
    const countryInput = document.createElement("input");

    portInput.placeholder = "Search Port";
    countryInput.placeholder = "Search Country or Destination";

    controls.appendChild(portInput);
    controls.appendChild(countryInput);
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    content.appendChild(controls);

    const tableHost = document.createElement("div");
    tableHost.id = "ocean-table-host";
    content.appendChild(tableHost);

    const sortState = { column: null, ascending: true };
    const draw = () => {
        const filteredRows = filterOceanRows(config.rows, portInput.value, countryInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, config.columns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    portInput.addEventListener("input", draw);
    countryInput.addEventListener("input", draw);
    draw();
}

function renderOceanCostingTable(config) {
    const content = document.getElementById("content");

    const note = document.createElement("p");
    note.style.fontSize = "12px";
    note.style.color = "#555";
    note.style.marginBottom = "8px";
    note.textContent =
        "Same ocean data as OCEAN: one row per Port + Destination + Country. Ocean Freight is chosen by country rules (cheapest, CMDU/MAEU mean, or mean of the three lowest CMDU/MAEU rates). GRI comes from Jarvis → Documentation / CIF (per Country). Use the search boxes to filter.";
    content.appendChild(note);

    const controls = document.createElement("div");
    const portInput = document.createElement("input");
    const countryInput = document.createElement("input");

    portInput.placeholder = "Search Port";
    countryInput.placeholder = "Search Country or Destination";

    controls.appendChild(portInput);
    controls.appendChild(countryInput);
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.flexWrap = "wrap";
    controls.style.gap = "8px";
    controls.style.marginBottom = "6px";
    content.appendChild(controls);

    const tableHost = document.createElement("div");
    tableHost.id = "ocean-costing-table-host";
    content.appendChild(tableHost);

    const sortState = { column: null, ascending: true };
    const draw = () => {
        const filteredRows = filterOceanRows(config.rows, portInput.value, countryInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, config.columns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            },
        });
    };

    portInput.addEventListener("input", draw);
    countryInput.addEventListener("input", draw);
    draw();
}

function escapeCsvField(value) {
    if (value === null || value === undefined) {
        return "";
    }
    const s = String(value);
    if (/[",\r\n]/.test(s)) {
        return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
}

/**
 * Download the given rows as CSV; header row uses columnLabels when present (same labels as the table).
 */
function downloadTableAsCsv(columns, columnLabels, rows, filename) {
    const header = columns.map((col) =>
        escapeCsvField(
            columnLabels && Object.prototype.hasOwnProperty.call(columnLabels, col)
                ? columnLabels[col]
                : col,
        ),
    );
    const lines = [header.join(",")];
    for (const row of rows) {
        lines.push(columns.map((col) => escapeCsvField(row[col])).join(","));
    }
    const body = lines.join("\r\n");
    const blob = new Blob(["\uFEFF", body], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function makeExportCsvButton() {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Export as CSV";
    btn.style.padding = "6px 12px";
    btn.style.cursor = "pointer";
    btn.style.borderRadius = "4px";
    btn.style.border = "1px solid #ccc";
    btn.style.background = "#fff";
    btn.style.fontSize = "13px";
    return btn;
}

function renderUsdTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const searchInput = document.createElement("input");
    const exportBtn = makeExportCsvButton();

    searchInput.placeholder = "Search Warehouse, Name, or City";

    controls.appendChild(searchInput);
    controls.appendChild(exportBtn);
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.flexWrap = "wrap";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    content.appendChild(controls);

    // Region summary
    const regionSummary = document.createElement("div");
    regionSummary.style.marginBottom = "10px";
    regionSummary.style.fontSize = "13px";
    regionSummary.style.display = "flex";
    regionSummary.style.gap = "12px";
    regionSummary.style.flexWrap = "wrap";
    regionSummary.style.alignItems = "center";
    content.appendChild(regionSummary);

    function updateRegionSummary(rows) {
        const counts = {};
        rows.forEach(r => {
            const reg = (r.Region || "").trim() || "(blank)";
            counts[reg] = (counts[reg] || 0) + 1;
        });
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        regionSummary.innerHTML = "<strong>Regions:</strong> " +
            sorted.map(([reg, cnt]) =>
                `<span style="background:#e8eaf6;padding:2px 8px;border-radius:3px;">${reg}: ${cnt}</span>`
            ).join(" ") +
            ` <span style="padding:2px 8px;"><strong>Total: ${rows.length}</strong></span>`;
    }

    const tableHost = document.createElement("div");
    tableHost.id = "usd-table-host";
    tableHost.style.overflowX = "auto";
    content.appendChild(tableHost);

    content.appendChild(createUsdColumnDiscussion());

    const headerGroups = config.headerGroups || null;
    const sortState = { column: null, ascending: true };
    let displayRowsSnapshot = [];
    const draw = () => {
        const filteredRows = filterTariffRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        displayRowsSnapshot = sortedRows;
        updateRegionSummary(sortedRows);
        drawTable(tableHost, config.columns, sortedRows, {
            sortState,
            headerGroups,
            columnLabels: config.columnLabels || null,
            tableClass: "usd-table",
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    exportBtn.addEventListener("click", () => {
        downloadTableAsCsv(
            config.columns,
            config.columnLabels || null,
            displayRowsSnapshot,
            "usd-table.csv",
        );
    });

    searchInput.addEventListener("input", draw);
    draw();
}

function getPtsIncluded() {
    try {
        const val = localStorage.getItem("pts_included");
        if (val === null) return null;
        return JSON.parse(val);
    } catch { return null; }
}

function setPtsIncluded(list) {
    localStorage.setItem("pts_included", JSON.stringify(list));
}

function renderPtsTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const searchInput = document.createElement("input");
    const exportBtn = makeExportCsvButton();

    searchInput.placeholder = "Search Warehouse, Name, or City";

    const toggleAllBtn = document.createElement("button");
    toggleAllBtn.textContent = "Select All";
    toggleAllBtn.style.cssText = "font-size:12px;padding:4px 10px;cursor:pointer;";

    const excludeInfo = document.createElement("span");
    excludeInfo.style.cssText = "font-size:12px;color:#666;margin-left:8px;";

    controls.appendChild(searchInput);
    controls.appendChild(exportBtn);
    controls.appendChild(toggleAllBtn);
    controls.appendChild(excludeInfo);
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.flexWrap = "wrap";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    content.appendChild(controls);

    const tableHost = document.createElement("div");
    tableHost.id = "pts-table-host";
    tableHost.style.overflowX = "auto";
    content.appendChild(tableHost);

    content.appendChild(createPtsColumnDiscussion());

    const headerGroups = config.headerGroups || null;
    const sortState = { column: null, ascending: true };
    let displayRowsSnapshot = [];

    const draw = () => {
        const included = getPtsIncluded();
        const allKeys = config.rows.map(r => `${r["Warehouse"] || ""}|${r["Region"] || ""}`);
        const includedSet = included === null ? new Set(allKeys) : new Set(included);
        const inclCount = includedSet.size;
        excludeInfo.textContent = `${inclCount} of ${allKeys.length} included in CIF`;
        toggleAllBtn.textContent = inclCount === allKeys.length ? "Deselect All" : "Select All";

        const filteredRows = filterTariffRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        displayRowsSnapshot = sortedRows;

        const columnsWithCheck = ["_include", ...config.columns];
        let adjustedGroups = headerGroups;
        if (headerGroups && Array.isArray(headerGroups) && headerGroups.length > 0) {
            adjustedGroups = [
                { label: "", columns: ["_include"] },
                ...headerGroups
            ];
        }
        drawTable(tableHost, columnsWithCheck, sortedRows, {
            sortState,
            headerGroups: adjustedGroups,
            columnLabels: { ...(config.columnLabels || {}), "_include": "Incl" },
            tableClass: "usd-table",
            onHeaderClick: (column) => {
                if (column === "_include") return;
                toggleSort(sortState, column);
                draw();
            },
            customCellRenderer: (col, row) => {
                if (col !== "_include") return null;
                const wh = String(row["Warehouse"] || "");
                const region = String(row["Region"] || "");
                const key = `${wh}|${region}`;
                const cb = document.createElement("input");
                cb.type = "checkbox";
                cb.checked = includedSet.has(key);
                cb.style.cursor = "pointer";
                cb.addEventListener("change", () => {
                    let inc = getPtsIncluded();
                    if (inc === null) inc = [...allKeys];
                    if (cb.checked) {
                        if (!inc.includes(key)) inc.push(key);
                    } else {
                        inc = inc.filter(k => k !== key);
                    }
                    setPtsIncluded(inc);
                    draw();
                });
                return cb;
            }
        });
    };

    exportBtn.addEventListener("click", () => {
        downloadTableAsCsv(
            config.columns,
            config.columnLabels || null,
            displayRowsSnapshot,
            "pts-table.csv",
        );
    });

    toggleAllBtn.addEventListener("click", () => {
        const included = getPtsIncluded();
        const allKeys = config.rows.map(r => `${r["Warehouse"] || ""}|${r["Region"] || ""}`);
        if (included === null || included.length === allKeys.length) {
            setPtsIncluded([]);
        } else {
            setPtsIncluded(allKeys);
        }
        draw();
    });

    searchInput.addEventListener("input", draw);
    draw();
}

function renderCifTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const searchInput = document.createElement("input");
    const exportBtn = makeExportCsvButton();

    searchInput.placeholder = "Search Region";

    const zeroToggle = document.createElement("label");
    zeroToggle.style.fontSize = "12px";
    zeroToggle.style.display = "flex";
    zeroToggle.style.alignItems = "center";
    zeroToggle.style.gap = "4px";
    zeroToggle.style.cursor = "pointer";
    const zeroCheckbox = document.createElement("input");
    zeroCheckbox.type = "checkbox";
    zeroCheckbox.checked = true;  // default: ignore zeros
    zeroToggle.appendChild(zeroCheckbox);
    zeroToggle.appendChild(document.createTextNode("Ignore 0s in averages"));

    controls.appendChild(searchInput);
    controls.appendChild(zeroToggle);
    controls.appendChild(exportBtn);
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.flexWrap = "wrap";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    content.appendChild(controls);

    const tableHost = document.createElement("div");
    tableHost.id = "cif-table-host";
    tableHost.style.overflowX = "auto";
    content.appendChild(tableHost);

    content.appendChild(createCifColumnDiscussion());

    const headerGroups = config.headerGroups || null;
    const sortState = { column: null, ascending: true };
    let displayRowsSnapshot = [];
    const draw = () => {
        const filteredRows = filterCifRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        displayRowsSnapshot = sortedRows;
        drawTable(tableHost, config.columns, sortedRows, {
            sortState,
            headerGroups,
            columnLabels: config.columnLabels || null,
            tableClass: "usd-table",
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    exportBtn.addEventListener("click", () => {
        downloadTableAsCsv(
            config.columns,
            config.columnLabels || null,
            displayRowsSnapshot,
            "cif-table.csv",
        );
    });

    searchInput.addEventListener("input", draw);

    zeroCheckbox.addEventListener("change", async () => {
        await loadCifRows(config, zeroCheckbox.checked);
        draw();
    });

    draw();
}

function renderTariffTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const searchInput = document.createElement("input");

    searchInput.placeholder = "Search Warehouse, Name, or City";

    controls.appendChild(searchInput);
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    content.appendChild(controls);

    const tableHost = document.createElement("div");
    tableHost.id = "tariff-table-host";
    content.appendChild(tableHost);

    const sortState = { column: null, ascending: true };
    const draw = () => {
        const filteredRows = filterTariffRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, config.columns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    searchInput.addEventListener("input", draw);
    draw();
}

function renderSeamTariffTable(config) {
    const content = document.getElementById("content");

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    controls.style.alignItems = "center";
    controls.style.flexWrap = "wrap";

    const searchInput = document.createElement("input");
    searchInput.placeholder = "Search Warehouse, Name, or City";
    controls.appendChild(searchInput);

    // --- Local file compare (no browser upload needed) ---
    const localSelect = document.createElement("select");
    localSelect.style.fontSize = "12px";
    localSelect.innerHTML = '<option value="">-- select local CSV --</option>';
    controls.appendChild(localSelect);

    const localCompareBtn = document.createElement("button");
    localCompareBtn.textContent = "Compare Local";
    localCompareBtn.style.padding = "6px 12px";
    localCompareBtn.style.fontSize = "12px";
    controls.appendChild(localCompareBtn);

    const applyBtn = document.createElement("button");
    applyBtn.textContent = "Apply Changes";
    applyBtn.style.padding = "6px 12px";
    applyBtn.style.fontSize = "12px";
    applyBtn.style.display = "none";
    controls.appendChild(applyBtn);

    const statusMsg = document.createElement("span");
    statusMsg.style.fontSize = "12px";
    statusMsg.style.color = "#555";
    controls.appendChild(statusMsg);

    // Populate local file dropdown
    fetch("/api/seam-tariffs/local-files")
        .then(r => r.json())
        .then(data => {
            (data.files || []).forEach(f => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.textContent = f;
                localSelect.appendChild(opt);
            });
        })
        .catch(() => {});

    content.appendChild(controls);

    // Legend
    const legend = document.createElement("div");
    legend.style.fontSize = "11px";
    legend.style.marginBottom = "8px";
    legend.style.display = "none";
    legend.innerHTML =
        '<span style="background:#d4edda;padding:2px 6px;margin-right:8px;">Updated</span>' +
        '<span style="background:#d6eaf8;padding:2px 6px;margin-right:8px;">Unchanged</span>' +
        '<span style="background:#f8d7da;padding:2px 6px;margin-right:8px;">In system, not in CSV</span>' +
        '<span style="background:#fdebd0;padding:2px 6px;">New (in CSV, not in system)</span>';
    content.appendChild(legend);

    const tableHost = document.createElement("div");
    tableHost.id = "tariff-table-host";
    content.appendChild(tableHost);

    let displayColumns = config.columns.filter(c => c !== "_status" && c !== "_changed_fields");
    const sortState = { column: null, ascending: true };
    let lastLocalFile = null;

    const draw = () => {
        const filteredRows = filterTariffRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, displayColumns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };

    searchInput.addEventListener("input", draw);

    localCompareBtn.addEventListener("click", async () => {
        const filename = localSelect.value;
        if (!filename) {
            statusMsg.textContent = "Please select a local CSV file first.";
            return;
        }
        lastLocalFile = filename;
        statusMsg.textContent = "Comparing...";
        try {
            const resp = await fetch("/api/seam-tariffs/compare-local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename })
            });
            if (!resp.ok) throw new Error(`Compare failed (${resp.status})`);
            const payload = await resp.json();
            config.rows = Array.isArray(payload.rows) ? payload.rows : [];
            legend.style.display = "block";
            applyBtn.style.display = "inline-block";
            const counts = { updated: 0, unchanged: 0, removed: 0, "new": 0 };
            config.rows.forEach(r => { if (r._status) counts[r._status]++; });
            statusMsg.textContent = `${counts.updated} updated, ${counts["new"]} new, ${counts.removed} removed, ${counts.unchanged} unchanged`;
            draw();
        } catch (err) {
            statusMsg.textContent = err.message;
        }
    });

    applyBtn.addEventListener("click", async () => {
        if (!lastLocalFile) return;
        showProgressModal("Saving SEAM tariffs...");
        try {
            const resp = await fetch("/api/seam-tariffs/apply-local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: lastLocalFile })
            });
            if (!resp.ok) throw new Error(`Apply failed (${resp.status})`);
            const payload = await resp.json();
            document.getElementById("progress-modal-msg").textContent = "Reloading data...";
            await loadSeamTariffRows(config);
            hideProgressModal();
            statusMsg.textContent = `Applied. ${payload.updated || 0} updated, ${payload.new || 0} new.`;
            applyBtn.style.display = "none";
            legend.style.display = "none";
            draw();
        } catch (err) {
            hideProgressModal();
            statusMsg.textContent = err.message;
        }
    });

    draw();
}

function renderRegionsAndPortsTable(config) {
    const content = document.getElementById("content");
    const controls = document.createElement("div");
    const searchInput = document.createElement("input");

    searchInput.placeholder =
        "Search Warehouse, Name, City, State, Region, Export, Port, ESO…";

    controls.appendChild(searchInput);
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginBottom = "10px";
    controls.style.flexWrap = "wrap";
    controls.style.alignItems = "center";
    searchInput.style.minWidth = "280px";
    searchInput.style.flex = "1 1 280px";

    // --- Local file compare controls ---
    const localSelect = document.createElement("select");
    localSelect.style.fontSize = "12px";
    localSelect.innerHTML = '<option value="">-- select local CSV --</option>';
    controls.appendChild(localSelect);

    const localCompareBtn = document.createElement("button");
    localCompareBtn.textContent = "Compare Local";
    localCompareBtn.style.padding = "6px 12px";
    localCompareBtn.style.fontSize = "12px";
    controls.appendChild(localCompareBtn);

    const saveBtn = document.createElement("button");
    saveBtn.textContent = "Save";
    saveBtn.style.padding = "6px 12px";
    saveBtn.style.fontSize = "12px";
    saveBtn.style.fontWeight = "bold";
    controls.appendChild(saveBtn);

    const statusMsg = document.createElement("span");
    statusMsg.style.fontSize = "12px";
    statusMsg.style.color = "#555";
    controls.appendChild(statusMsg);

    // Populate local file dropdown
    fetch("/api/regions-and-ports/local-files")
        .then(r => r.json())
        .then(data => {
            (data.files || []).forEach(f => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.textContent = f;
                localSelect.appendChild(opt);
            });
        })
        .catch(() => {});

    content.appendChild(controls);

    // Legend
    const legend = document.createElement("div");
    legend.style.fontSize = "11px";
    legend.style.marginBottom = "8px";
    legend.style.display = "none";
    legend.innerHTML =
        '<span style="background:#d6eaf8;padding:2px 6px;margin-right:8px;">In both</span>' +
        '<span style="background:#f8d7da;padding:2px 6px;margin-right:8px;">In system, not in CSV</span>' +
        '<span style="background:#fff9c4;padding:2px 6px;">New (in CSV, not in system)</span>';
    content.appendChild(legend);

    const tableHost = document.createElement("div");
    tableHost.id = "regions-ports-table-host";
    tableHost.style.overflowX = "auto";
    content.appendChild(tableHost);

    let displayColumns = config.columns.filter(c => c !== "_status" && c !== "_changed_fields");
    const sortState = { column: null, ascending: true };

    const rapInputColumns = ["Region", "Export", "Port"];

    const draw = () => {
        const filteredRows = filterRegionsAndPortsRows(config.rows, searchInput.value);
        const sortedRows = sortRows(filteredRows, sortState);
        drawTable(tableHost, displayColumns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            },
            inputColumns: rapInputColumns
        });
    };

    searchInput.addEventListener("input", draw);

    saveBtn.addEventListener("click", async () => {
        showProgressModal("Saving Regions & Ports...");
        const edits = config.rows
            .filter(r => r.Warehouse)
            .map(r => ({
                warehouse: r.Warehouse,
                Region: r.Region || "",
                Export: r.Export || "",
                Port: r.Port || ""
            }));
        try {
            const resp = await fetch("/api/regions-and-ports/save-edits", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ edits })
            });
            if (!resp.ok) throw new Error(`Save failed (${resp.status})`);
            const payload = await resp.json();
            document.getElementById("progress-modal-msg").textContent = "Done!";
            await new Promise(r => setTimeout(r, 500));
            hideProgressModal();
            statusMsg.textContent = `Saved. ${payload.count} warehouses updated.`;
        } catch (err) {
            hideProgressModal();
            statusMsg.textContent = err.message;
        }
    });

    localCompareBtn.addEventListener("click", async () => {
        const filename = localSelect.value;
        if (!filename) {
            statusMsg.textContent = "Please select a local CSV file first.";
            return;
        }
        statusMsg.textContent = "Comparing...";
        try {
            const resp = await fetch("/api/regions-and-ports/compare-local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename })
            });
            if (!resp.ok) throw new Error(`Compare failed (${resp.status})`);
            const payload = await resp.json();
            config.rows = Array.isArray(payload.rows) ? payload.rows : [];
            legend.style.display = "block";
            const counts = { unchanged: 0, removed: 0, "new": 0 };
            config.rows.forEach(r => { if (r._status) counts[r._status]++; });
            statusMsg.textContent = `${counts["new"]} new (not in system), ${counts.removed} in system not in CSV, ${counts.unchanged} in both`;
            draw();
        } catch (err) {
            statusMsg.textContent = err.message;
        }
    });

    draw();
}

function filterOtrRows(rows, originSearch, destSearch) {
    const originTerm = originSearch.trim().toLowerCase();
    const destTerm = destSearch.trim().toLowerCase();

    return rows.filter((row) => {
        const originCity = String(row["Origin City"] || "").toLowerCase();
        const originState = String(row["Origin State"] || "").toLowerCase();
        const destCity = String(row["Dest City"] || "").toLowerCase();
        const destState = String(row["Dest State"] || "").toLowerCase();

        const originMatch =
            !originTerm ||
            originCity.includes(originTerm) ||
            originState.includes(originTerm);
        const destMatch =
            !destTerm ||
            destCity.includes(destTerm) ||
            destState.includes(destTerm);

        return originMatch && destMatch;
    });
}

function filterOceanRows(rows, portSearch, countrySearch) {
    const portTerm = portSearch.trim().toLowerCase();
    const countryTerm = countrySearch.trim().toLowerCase();

    return rows.filter((row) => {
        const port = String(row["Port"] || "").toLowerCase();
        const country = String(row["Country"] || "").toLowerCase();
        const destination = String(row["Destination"] || "").toLowerCase();

        const portMatch = !portTerm || port.includes(portTerm);
        const countryMatch =
            !countryTerm ||
            country.includes(countryTerm) ||
            destination.includes(countryTerm);

        return portMatch && countryMatch;
    });
}

function filterTariffRows(rows, searchText) {
    const term = searchText.trim().toLowerCase();
    if (!term) {
        return rows;
    }

    return rows.filter((row) => {
        const warehouse = String(row["Warehouse"] || "").toLowerCase();
        const name = String(row["Name"] || "").toLowerCase();
        const city = String(row["City"] || "").toLowerCase();
        const region = String(row["Region"] || "").toLowerCase();

        return (
            warehouse.includes(term) ||
            name.includes(term) ||
            city.includes(term) ||
            region.includes(term)
        );
    });
}

function filterCifRows(rows, searchText) {
    const term = searchText.trim().toLowerCase();
    if (!term) {
        return rows;
    }
    return rows.filter((row) => String(row["Region"] || "").toLowerCase().includes(term));
}

const REGIONS_AND_PORTS_SEARCH_FIELDS = [
    "Warehouse",
    "Name",
    "City",
    "State",
    "Region",
    "Export",
    "Port",
    "ESO",
];

function filterRegionsAndPortsRows(rows, searchText) {
    const term = searchText.trim().toLowerCase();
    if (!term) {
        return rows;
    }

    return rows.filter((row) =>
        REGIONS_AND_PORTS_SEARCH_FIELDS.some((key) =>
            String(row[key] ?? "").toLowerCase().includes(term),
        ),
    );
}

function renderBasicTable(columns, rows) {
    const content = document.getElementById("content");
    const sortState = { column: null, ascending: true };
    const draw = () => {
        const sortedRows = sortRows(rows, sortState);
        drawTable(content, columns, sortedRows, {
            sortState,
            onHeaderClick: (column) => {
                toggleSort(sortState, column);
                draw();
            }
        });
    };
    draw();
}

function drawTable(hostElement, columns, rows, options = {}) {
    hostElement.innerHTML = "";
    const sortState = options.sortState || { column: null, ascending: true };
    const onHeaderClick = typeof options.onHeaderClick === "function" ? options.onHeaderClick : null;
    const headerGroups = options.headerGroups || null;
    const columnLabels = options.columnLabels || null;
    const tableClass = options.tableClass || "";
    const editableColumns = options.editableColumns || {};  // { columnName: { onSave(row, newValue) } }
    const inputColumns = options.inputColumns || [];  // columns rendered as persistent <input> fields
    const customCellRenderer = options.customCellRenderer || null;

    const table = document.createElement("table");
    if (tableClass) {
        table.className = tableClass;
    }

    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");

    if (headerGroups && Array.isArray(headerGroups) && headerGroups.length > 0) {
        const flattened = [];
        headerGroups.forEach((g) => {
            (g.columns || []).forEach((c) => flattened.push(c));
        });
        const columnsMatch =
            flattened.length === columns.length &&
            flattened.every((c, i) => c === columns[i]);
        if (!columnsMatch) {
            console.warn("USD headerGroups do not match columns; falling back to single header row.");
            buildSingleHeaderRow(thead, columns, sortState, onHeaderClick, columnLabels);
        } else {
            const groupRow = document.createElement("tr");
            headerGroups.forEach((g) => {
                const th = document.createElement("th");
                const count = (g.columns || []).length;
                th.colSpan = count;
                th.textContent = g.label || "";
                th.className = g.label ? "usd-group-header" : "usd-group-header usd-group-empty";
                groupRow.appendChild(th);
            });
            thead.appendChild(groupRow);

            const subRow = document.createElement("tr");
            columns.forEach((column) => {
                const th = document.createElement("th");
                const arrow =
                    sortState.column === column
                        ? (sortState.ascending ? " ▲" : " ▼")
                        : "";
                const label =
                    columnLabels && columnLabels[column] !== undefined
                        ? columnLabels[column]
                        : column;
                th.textContent = `${label}${arrow}`;
                th.className = "usd-sub-header";
                if (onHeaderClick) {
                    th.style.cursor = "pointer";
                    th.addEventListener("click", () => onHeaderClick(column));
                }
                subRow.appendChild(th);
            });
            thead.appendChild(subRow);
        }
    } else {
        buildSingleHeaderRow(thead, columns, sortState, onHeaderClick, columnLabels);
    }

    table.appendChild(thead);

    if (rows.length === 0) {
        const emptyRow = document.createElement("tr");
        const emptyCell = document.createElement("td");
        emptyCell.colSpan = columns.length;
        emptyCell.textContent = "No rows available";
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);
    } else {
        const statusColors = {
            updated: "#d4edda",   // green
            unchanged: "#d6eaf8", // blue
            removed: "#f8d7da",   // red
            "new": "#fff9c4",     // yellow
        };
        rows.forEach((row, rowIdx) => {
            const tr = document.createElement("tr");
            if (row._status && statusColors[row._status]) {
                tr.style.background = statusColors[row._status];
            }
            const changedFields = row._changed_fields || [];
            columns.forEach((column) => {
                if (column === "_status" || column === "_changed_fields") return;
                const td = document.createElement("td");
                if (customCellRenderer) {
                    const custom = customCellRenderer(column, row, rowIdx);
                    if (custom) {
                        td.appendChild(custom);
                        tr.appendChild(td);
                        return;
                    }
                }
                const value = row[column] ?? "";
                if (inputColumns.includes(column)) {
                    const inp = document.createElement("input");
                    inp.type = "text";
                    inp.value = value;
                    inp.style.width = "100%";
                    inp.style.fontSize = "inherit";
                    inp.style.boxSizing = "border-box";
                    inp.style.border = "1px solid #ccc";
                    inp.style.padding = "2px 4px";
                    inp.addEventListener("input", () => {
                        row[column] = inp.value;
                        if (_isThemeCountryColumn(column)) {
                            applyCountryThemeToTd(td, inp.value);
                        }
                    });
                    td.appendChild(inp);
                    if (_isThemeCountryColumn(column)) {
                        applyCountryThemeToTd(td, inp.value);
                    }
                    tr.appendChild(td);
                    return;
                }
                td.textContent = value;
                td.classList.add(isNumericValue(value) ? "td-num" : "td-text");
                if (_isThemeCountryColumn(column)) {
                    applyCountryThemeToTd(td, value);
                }
                if (row._status === "updated" && Array.isArray(changedFields) && changedFields.includes(column)) {
                    td.style.fontWeight = "bold";
                    td.style.fontSize = "15px";
                }
                td.style.cursor = "pointer";
                if (editableColumns[column]) {
                    td.style.cursor = "cell";
                    td.style.borderBottom = "1px dashed #999";
                    td.addEventListener("dblclick", (e) => {
                        e.stopPropagation();
                        const input = document.createElement("input");
                        input.type = "text";
                        input.value = value;
                        input.style.width = "100%";
                        input.style.fontSize = "inherit";
                        input.style.boxSizing = "border-box";
                        td.textContent = "";
                        td.appendChild(input);
                        input.focus();
                        input.select();
                        const commit = async () => {
                            const newVal = input.value.trim();
                            td.textContent = newVal;
                            row[column] = newVal;
                            if (_isThemeCountryColumn(column)) {
                                applyCountryThemeToTd(td, newVal);
                            }
                            if (newVal !== value) {
                                await editableColumns[column].onSave(row, newVal);
                            }
                        };
                        input.addEventListener("blur", commit);
                        input.addEventListener("keydown", (ke) => {
                            if (ke.key === "Enter") input.blur();
                            if (ke.key === "Escape") { input.value = value; input.blur(); }
                        });
                    });
                }
                td.addEventListener("click", () => {
                    showCellDerivation(row, column, value, rowIdx);
                });
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    table.appendChild(tbody);
    hostElement.appendChild(table);
}

function buildSingleHeaderRow(thead, columns, sortState, onHeaderClick, columnLabels) {
    const headRow = document.createElement("tr");
    columns.forEach((column) => {
        const th = document.createElement("th");
        const arrow =
            sortState.column === column
                ? (sortState.ascending ? " ▲" : " ▼")
                : "";
        const label =
            columnLabels && columnLabels[column] !== undefined
                ? columnLabels[column]
                : column;
        th.textContent = `${label}${arrow}`;
        if (onHeaderClick) {
            th.style.cursor = "pointer";
            th.addEventListener("click", () => onHeaderClick(column));
        }
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
}

function toggleSort(sortState, column) {
    if (sortState.column === column) {
        sortState.ascending = !sortState.ascending;
        return;
    }
    sortState.column = column;
    sortState.ascending = true;
}

function sortRows(rows, sortState) {
    if (!sortState.column) {
        return [...rows];
    }

    const column = sortState.column;
    const multiplier = sortState.ascending ? 1 : -1;
    return [...rows].sort((a, b) => {
        const av = a[column];
        const bv = b[column];

        const aNum = Number(av);
        const bNum = Number(bv);
        const aNumOk = Number.isFinite(aNum) && String(av).trim() !== "";
        const bNumOk = Number.isFinite(bNum) && String(bv).trim() !== "";

        if (aNumOk && bNumOk) {
            return (aNum - bNum) * multiplier;
        }

        return String(av ?? "").localeCompare(String(bv ?? ""), undefined, { numeric: true }) * multiplier;
    });
}

function isNumericValue(value) {
    if (typeof value === "number") {
        return Number.isFinite(value);
    }
    if (typeof value !== "string") {
        return false;
    }
    const trimmed = value.trim();
    if (trimmed === "") {
        return false;
    }
    const normalized = trimmed.replace(/,/g, "");
    const parsed = Number(normalized);
    return Number.isFinite(parsed);
}

function showCellDerivation(row, column, value, rowIdx) {
    const panel = document.getElementById("cell-derivation");
    if (!panel) return;
    panel.style.display = "block";

    // If the row carries explicit derivation metadata, use it
    if (row._derivations && row._derivations[column]) {
        panel.textContent = `${column} = ${row._derivations[column]}`;
        return;
    }

    // Identify the row by warehouse or first meaningful key
    const rowId = row["Warehouse"] || row["Row"] || `row ${rowIdx + 1}`;

    // Determine current view
    const sel = document.getElementById("select_view");
    const viewName = sel ? sel.options[sel.selectedIndex].text : "";

    // Build derivation description based on view
    let derivation = "";
    if (viewName === "Seam Tariffs" || viewName === "Cert Tariffs") {
        const csvCol = column === "Basis Adj." ? "Basis Adj" : column;
        if (column === "Row") {
            derivation = `Row number (auto-generated sequence)`;
        } else {
            derivation = `CSV → SEAM_TARIFFS_CERT_TARIFFS.csv [ Warehouse=${rowId} ] . "${csvCol}"`;
        }
    } else if (viewName === "OTR") {
        derivation = `CSV → OTR source [ row ${rowIdx + 1} ] . "${column}"`;
    } else if (viewName === "OCEAN") {
        if (column === "GRI") {
            derivation = `document_cif (Jarvis Documentation / CIF), Country="${row.Country || "?"}" . "GRI" (included in GET /api/ocean)`;
        } else {
            derivation = `GET /api/ocean [ row ${rowIdx + 1} ] . "${column}"`;
        }
    } else if (viewName === "Ocean Costing") {
        if (column === "GRI") {
            derivation = `document_cif (Jarvis Documentation / CIF), Country="${row.Country || "?"}" . "GRI" (included in GET /api/ocean)`;
        } else {
            derivation = `GET /api/ocean (deduped by Port+Destination+Country) [ row ${rowIdx + 1} ] . "${column}"`;
        }
    } else if (viewName === "USD") {
        derivation = _usdDerivation(row, column);
    } else {
        derivation = `"${column}" from row ${rowIdx + 1}`;
    }

    panel.textContent = `${column} = ${value === "" ? '""' : value}  ←  ${derivation}`;
}

function _usdDerivation(row, column) {
    const wh = row["Warehouse"] || "?";
    const port = row["Port"] || "?";
    const terms = row["Terms"] || "?";

    // Direct from SEAM_TARIFFS CSV
    const seamFields = ["Recv", "Load", "Compr", "Class", "Mark", "Terms"];
    if (seamFields.includes(column)) {
        return `SEAM_TARIFFS_CERT_TARIFFS.csv [ Warehouse=${wh} ] . "${column}"`;
    }

    // Storage has special logic
    if (column === "Strg") {
        return `SEAM_TARIFFS.csv [ Warehouse=${wh} ] . "Strg"  (if < 1.0 then × 30)`;
    }

    // From regions_and_ports.csv
    if (column === "ESO") return `regions_and_ports.csv [ Warehouse=${wh} ] . "ESO"`;
    if (column === "Flatbed") return `regions_and_ports.csv [ Warehouse=${wh} ] . "Flat Bed Fees"`;
    if (column === "Late Fee") return `regions_and_ports.csv [ Warehouse=${wh} ] . "Late Fees"`;
    if (column === "Region") return `regions_and_ports.csv [ Warehouse=${wh} ] . "Region"`;
    if (column === "Export") return `regions_and_ports.csv [ Warehouse=${wh} ] . "Export"`;
    if (column === "Port") return `regions_and_ports.csv [ Warehouse=${wh} ] . "Port"`;

    // Identity fields
    if (column === "Name" || column === "City" || column === "State") {
        return `SEAM_TARIFFS.csv [ Warehouse=${wh} ] . "${column}" (fallback: regions_and_ports.csv)`;
    }
    if (column === "Warehouse") return `regions_and_ports.csv row key`;
    if (column === "Row") return `Auto-generated sequence number`;

    // Computed: Interest
    if (column === "Interest") {
        return `(EDF Interest Rate / 100 / 12) × Avg Purchase Price × Avg Bale Weight  [from control_panel.json]`;
    }

    // Origin Commission
    if (column === "Origin Comm") {
        return `control_panel.json . "Origin Commission"`;
    }

    // Total Equity
    if (column === "Total Equity") {
        return `Recv + Load + Compr + Class + Mark + Strg + ESO + Interest + Origin Comm`;
    }

    // Total Origin (depends on Terms)
    if (column === "Total Origin") {
        if (terms === "1") return `Terms=1: Strg + Interest + Origin Comm`;
        if (terms === "2") return `Terms=2: Compr + Strg + Interest + Origin Comm`;
        if (terms === "3") return `Terms=3: Load + Compr + Strg + Class + Interest + Origin Comm`;
        if (terms === "4") return `Terms=4: Class + Interest + Origin Comm`;
        return `Terms=${terms}: formula depends on Terms value (1-4)`;
    }

    // Transit Truck
    if (column === "Transit Truck") {
        return `OTR_Rates.csv [ City="${row["City"]}", Port="${port}" ] . Final ÷ 88`;
    }

    // Total Transit
    if (column === "Total Transit") {
        return `Flatbed + Late Fee + Transit Truck`;
    }

    // Consolidation
    if (column === "Consol_Block") return `consolidation.json [ Port="${port}" ] . InAndOut`;
    if (column === "Consol_Strg") return `consolidation.json [ Port="${port}" ] . TotalStorage  (from consolidation_days_storage.json)`;
    if (column === "Consol_Interest") {
        return `(Avg Purchase Price × Avg Bale Weight × EDF Rate / 100 / 365) × days_storage_factor  [control_panel.json + consolidation_days_storage.json]`;
    }
    if (column === "Total_Consol") return `Consol InAndOut + Consol TotalStorage + Consol Interest`;

    // Outbound
    if (column === "Dray") return `drayage.json [ Port="${port}" ] . "Bale"`;
    if (column === "Ocean") return `drayage.json [ Port="${port}" ] . "OceanBase" ÷ 88`;
    if (column === "Total_Out") return `Dray + Ocean base`;

    // Documentation
    if (column === "Sight_LC") return `document_cif.json [ Country="China" ] . "LC" ÷ 20`;
    if (column === "Forwarding") return `usa_forwarding_cost.json . "TOTAL"`;
    if (column === "Controlling") return `document_cif.json [ Country="China" ] . "CONT" ÷ 20`;
    if (column === "Insurance") return `document_cif.json [ Country="China" ] . "INS" ÷ 20`;
    if (column === "Total_Doc") return `Sight LC + Forwarding + Controlling + Insurance`;

    // CIF
    if (column === "Dest_Commission") return `document_cif.json [ Country="China" ] . "COM" ÷ 20`;
    if (column === "Cost_of_Funds") return `document_cif.json [ Country="China" ] . "COF" ÷ 20`;
    if (column === "Qclaim") return `document_cif.json [ Country="China" ] . "CIQ_QC" ÷ 20`;
    if (column === "Total_CIF") return `Dest Commission + Cost of Funds + Qclaim`;

    // Weslaco / Shelby
    if (column === "Weslaco_Transit" || column === "Shelby_Transit") return `(placeholder — not yet computed)`;

    return `"${column}" from USD calculation`;
}

/* ── Export view ───────────────────────────────────────────── */
const EXPORT_DATA = [
    { base: "China",      code: "CN", c: "38", d: "18", ports: ["Qingdao","Xiamen","Nantong"] },
    { base: "Vietnam",    code: "VN", c: "50", d: "14", ports: ["Ho Chi Minh","DaNang","Haiphong"] },
    { base: "Korea",      code: "KO", c: "46", d: "18", ports: ["Busan","Kwangyang"] },
    { base: "Japan",      code: "JP", c: "43", d: "14", ports: ["Osaka","Kobe","Nagoya"] },
    { base: "Malaysia",   code: "MA", c: "40", d: "14", ports: ["Tanjung Pelepas","Penang","Port Klang"] },
    { base: "Taiwan",     code: "TW", c: "45", d: "21", ports: ["Keelung","Taichung","Kaohsiung","Tao Yuan"] },
    { base: "Indonesia",  code: "ID", c: "38", d: "14", ports: ["Jakarta","Semarang","Cikarang","Surabaya"] },
    { base: "Thailand",   code: "TH", c: "45", d: "14", ports: ["Bangkok","Lat Krabang","Laem Chabang"] },
    { base: "Bangladesh", code: "BD", c: "52", d: "14", ports: ["Chittagong"] },
    { base: "Pakistan",   code: "PK", c: "45", d: "14", ports: ["Port Qasim/Karachi"] },
    { base: "India",      code: "IN", c: "50", d: "14", ports: ["Mundra","Tuticorin","Chennai"] },
    { base: "Turkey",     code: "TR", c: "37", d: "14", ports: ["Iskenderun","Mersin","Izmir"] },
    { base: "Mexico",     code: "MX", c: "",   d: "N/A",ports: ["Yecapixtla","Parras","CD Victoria"], extra: {secondCode: "Weslaco"} },
    { base: "Peru",       code: "PE", c: "11", d: "18", ports: ["Callao"] },
    { base: "Guatemala",  code: "GU", c: "8",  d: "21", ports: ["Amatitlan","Palin"] },
    { base: "Honduras",   code: "HO", c: "11", d: "18", ports: ["Naco"] },
    { base: "Spain",      code: "ES", c: "",   d: "14", ports: ["Santa Barbara"] },
    { base: "Italy",      code: "IT", c: "",   d: "14", ports: ["Bergamo","Salerno"] },
    { base: "Other",      code: "OT", c: "-",  d: "-",  ports: ["Batumi"] },
];

const EXPORT_REGIONS = ["WTX","WTXH","STX","MRS","ER5","EMOT","ME","HOU","DAL","BRZ","AUS"];

const EXPORT_REGION_TO_CIF = {
    WTX:  "WTX",
    WTXH: "WTXH",
    STX:  "STEX",
    MRS:  "Memphis Rule 5",
    ER5:  "Eastern Rule 5",
    EMOT: "GA 30 Day",
    ME:   "Memphis Equity",
    /** Export HOU column → CIF / hub name Houston */
    HOU:  "Houston",
    /** Export DAL column → CIF / hub name Dallas */
    DAL:  "Dallas",
    BRZ:  "BRZ",
    AUS:  "AUS",
};

const EXPORT_CIF_GROUP_LABELS = [
    "Origin Warehouse", "Inland Logistics", "Consolidation",
    "Outbound Logistics", "Documentation", "CIF", "Total Terms"
];

/** Map themes.Country (lower) → Color. Export "Other" → themes "Other International". */
function _exportThemeColorByCountry(themesRows) {
    const m = new Map();
    for (const t of themesRows || []) {
        const color = String(t.Color ?? t.color ?? "").trim();
        if (!color) {
            continue;
        }
        const name = String(t.Country ?? t.country ?? "").trim().toLowerCase();
        if (name) {
            m.set(name, color);
        }
    }
    return m;
}

function _exportBaseCellBackground(baseText, colorByCountry) {
    if (!baseText || !colorByCountry?.size) {
        return "";
    }
    const key = baseText.trim().toLowerCase();
    if (!key) {
        return "";
    }
    if (key === "other") {
        return colorByCountry.get("other international") || "";
    }
    return colorByCountry.get(key) || "";
}

let _themeCountryColorMapPromise = null;

function invalidateThemeCountryColorMapCache() {
    _themeCountryColorMapPromise = null;
}

function getThemeCountryColorMapCached() {
    if (!_themeCountryColorMapPromise) {
        _themeCountryColorMapPromise = fetch("/api/themes")
            .then((r) => (r.ok ? r.json() : []))
            .then((rows) => _exportThemeColorByCountry(Array.isArray(rows) ? rows : []))
            .catch(() => new Map());
    }
    return _themeCountryColorMapPromise;
}

function _isThemeCountryColumn(columnName) {
    if (columnName == null) {
        return false;
    }
    const s = String(columnName);
    if (s === "Country") {
        return true;
    }
    return s.toLowerCase() === "country";
}

function applyCountryThemeToTd(td, countryText) {
    if (!td) {
        return;
    }
    getThemeCountryColorMapCached().then((map) => {
        const bg = _exportBaseCellBackground(String(countryText || ""), map);
        if (bg) {
            td.style.backgroundColor = bg;
        }
    });
}

function _exportRowMatchesSearch(row, baseQuery, cifFeQuery) {
    const b = (baseQuery || "").trim().toLowerCase();
    const c = (cifFeQuery || "").trim().toLowerCase();
    if (b) {
        const group = String(row._exportBaseGroup ?? row.Base ?? "").trim().toLowerCase();
        if (!group.includes(b)) {
            return false;
        }
    }
    if (c) {
        const port = String(row["CIF FE"] ?? "").trim().toLowerCase();
        if (!port.includes(c)) {
            return false;
        }
    }
    return true;
}

function _buildExportColumns() {
    const cols = ["Base", "CIF FE"];
    EXPORT_CIF_GROUP_LABELS.forEach(group => {
        EXPORT_REGIONS.forEach(region => {
            cols.push(group + "|" + region);
        });
    });
    return cols;
}

function _exportCifFieldForGroup(groupLabel) {
    const map = {
        "Origin Warehouse": "Total Origin",
        "Inland Logistics": "Total Transit",
        Consolidation: "Total_Consol",
        "Outbound Logistics": "Total_Out",
        Documentation: "Total_Doc",
        CIF: "Total_CIF",
        "Total Terms": "Cash",
    };
    return map[groupLabel] || "";
}

const EXPORT_BODY_POPULATED_GROUPS = new Set(["Origin Warehouse", "Inland Logistics", "Consolidation"]);

/** Export Outbound (hub columns): CIF Dray + Ocean Total pts; same Country / Destination / hub-Port match for all. */
const EXPORT_OUTBOUND_CIF_OCEAN_HUB_ABBRS = new Set([
    "WTX", "WTXH", "STX", "MRS", "ER5", "HOU", "DAL",
]);

/** Ocean row Port must match this hub (normalized substring) for the export column.
 *  HOU / DAL hubs are taken from EXPORT_REGION_TO_CIF ("Houston", "Dallas"). */
const EXPORT_OUTBOUND_OCEAN_HUB_PORT = {
    WTX: "dallas",
    WTXH: "houston",
    STX: "houston",
    MRS: "memphis",
    ER5: "savannah",
};

function _exportOutboundUsesCifDrayAndOceanHubPts(abbr) {
    return EXPORT_OUTBOUND_CIF_OCEAN_HUB_ABBRS.has(String(abbr ?? "").trim());
}

function _exportOceanHubPortNorm(abbr) {
    const a = String(abbr ?? "").trim();
    if (a === "HOU" || a === "DAL") {
        const cifLabel = EXPORT_REGION_TO_CIF[a];
        return cifLabel ? _exportNormLoose(cifLabel) : "";
    }
    return EXPORT_OUTBOUND_OCEAN_HUB_PORT[a] || "";
}

function _exportOceanPortMatchesHub(portRaw, abbr) {
    const hub = _exportOceanHubPortNorm(abbr);
    if (!hub) {
        return false;
    }
    const p = _exportNormLoose(portRaw);
    if (!p) {
        return false;
    }
    return p === hub || p.includes(hub);
}

function _exportDestinationMatchesExportCity(destRaw, cifFe) {
    const fe = _exportNormLoose(cifFe);
    const d = _exportNormLoose(destRaw);
    if (!fe || !d) {
        return false;
    }
    return d === fe || fe === d || d.includes(fe) || fe.includes(d);
}

/** CIF Outbound Dray for this export column’s region (same Region row as rest of CIF). */
function _exportCifDrayForAbbr(cifByRegion, abbr) {
    const cifRegion = EXPORT_REGION_TO_CIF[abbr];
    const row = cifRegion && cifByRegion ? cifByRegion[cifRegion] : null;
    if (!row) {
        return "";
    }
    const v = row.Dray;
    if (v === undefined || v === null || v === "") {
        return "";
    }
    return String(v);
}

/**
 * Ocean Costing Total pts: Country = Export Base; Destination matches Export CIF FE (city);
 * Port matches export hub (Dallas / Houston / Memphis / Savannah).
 */
function _exportOceanTotalPtsForOutboundRow(oceanCostingRows, baseGroup, cifFe, abbr) {
    if (!Array.isArray(oceanCostingRows)) {
        return "";
    }
    const country = _exportNormLoose(baseGroup);
    const fe = String(cifFe || "").trim();
    if (!country || !fe) {
        return "";
    }
    for (const r of oceanCostingRows) {
        if (_exportNormLoose(r.Country) !== country) {
            continue;
        }
        if (!_exportOceanPortMatchesHub(r.Port, abbr)) {
            continue;
        }
        if (!_exportDestinationMatchesExportCity(r.Destination, fe)) {
            continue;
        }
        const tp = r["Total pts"];
        if (tp === undefined || tp === null || tp === "") {
            return "";
        }
        return String(tp);
    }
    return "";
}

function _exportNormLoose(s) {
    return String(s ?? "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ");
}

function _exportParseNumericCell(s) {
    if (s === null || s === undefined || s === "") {
        return NaN;
    }
    const n = parseFloat(String(s).replace(/,/g, ""));
    return Number.isFinite(n) ? n : NaN;
}

/**
 * Human-readable derivation for Export view cells (click-to-explain panel).
 * @param {object} ctx — { cifByRegion, oceanCostingRows }
 */
function _exportCellDerivation(row, column, rowIdx, ctx) {
    const cifByRegion = (ctx && ctx.cifByRegion) || {};
    const oceanRows = (ctx && ctx.oceanCostingRows) || [];
    if (column === "Base") {
        return `Preset country from EXPORT_DATA in script.js (first port row shows name; later rows blank; _exportBaseGroup = country for the block). Filtered row #${rowIdx + 1}.`;
    }
    if (column === "CIF FE") {
        return `Preset destination / foreign port from EXPORT_DATA.ports for this country; used with Base for Ocean Costing matches.`;
    }
    const pipe = column.indexOf("|");
    if (pipe <= 0) {
        return `Export column "${column}".`;
    }
    const group = column.slice(0, pipe);
    const abbr = column.slice(pipe + 1);
    const cifRegion = EXPORT_REGION_TO_CIF[abbr];
    if (!cifRegion) {
        return `Unknown region code "${abbr}".`;
    }
    const cifKey = _exportCifFieldForGroup(group);

    if (group === "Outbound Logistics" && _exportOutboundUsesCifDrayAndOceanHubPts(abbr)) {
        const baseG = String(row._exportBaseGroup || row.Base || "").trim();
        const cifFe = String(row["CIF FE"] || "").trim();
        if (!baseG || !cifFe) {
            return "ERROR: Base (country) or CIF FE (city) is blank on this row; cannot match Ocean Costing.";
        }
        const hub = _exportOceanHubPortNorm(abbr);
        const drayStr = _exportCifDrayForAbbr(cifByRegion, abbr);
        const ptsStr = _exportOceanTotalPtsForOutboundRow(oceanRows, baseG, cifFe, abbr);
        const drayN = _exportParseNumericCell(drayStr);
        const ptsN = _exportParseNumericCell(ptsStr);
        const hasD = Number.isFinite(drayN);
        const hasP = Number.isFinite(ptsN);
        const loc = `Country="${baseG}", Destination≈"${cifFe}", Port hub "${hub || "?"}"`;
        if (!hasD && !hasP) {
            return `ERROR: no numeric CIF Dray and no Ocean Total pts for ${loc}. Cell shows ERROR (not CIF Total_Out).`;
        }
        const bits = [];
        if (hasD) {
            bits.push(`CIF Dray: GET /api/cif [ Region="${cifRegion}" ] . Dray = ${drayStr}`);
        }
        if (hasP) {
            bits.push(`Ocean Total pts: deduped GET /api/ocean row where ${loc} → Total pts = ${ptsStr}`);
        }
        bits.push(`Cell = sum of available parts, rounded to a whole number.`);
        return bits.join(" · ");
    }

    if (group === "Outbound Logistics") {
        return `GET /api/cif [ Region="${cifRegion}" ] . Total_Out (${abbr}).`;
    }

    if (EXPORT_BODY_POPULATED_GROUPS.has(group)) {
        const field = cifKey || column;
        return `GET /api/cif [ Region="${cifRegion}" ] . "${field}" (${group}: PTS averages for that region).`;
    }

    const field = cifKey || "?";
    return `GET /api/cif [ Region="${cifRegion}" ] . "${field}" (${group}).`;
}

function _exportOutboundLogisticsBodyCell(cifByRegion, exportOpts, exportRow, abbr) {
    if (!_exportOutboundUsesCifDrayAndOceanHubPts(abbr)) {
        return _exportCellValueForGroupRegion(cifByRegion, "Outbound Logistics", abbr);
    }
    const opts = exportOpts || {};
    const baseG = String(exportRow._exportBaseGroup || exportRow.Base || "").trim();
    const cifFe = String(exportRow["CIF FE"] || "").trim();
    if (!baseG || !cifFe) {
        return "ERROR";
    }
    const oceanPtsStr = _exportOceanTotalPtsForOutboundRow(opts.oceanCostingRows, baseG, cifFe, abbr);
    const drayStr = _exportCifDrayForAbbr(cifByRegion, abbr);

    const oceanN = _exportParseNumericCell(oceanPtsStr);
    const drayN = _exportParseNumericCell(drayStr);
    const hasOcean = String(oceanPtsStr).trim() !== "" && Number.isFinite(oceanN);
    const hasDray = String(drayStr).trim() !== "" && Number.isFinite(drayN);

    if (!hasOcean && !hasDray) {
        return "ERROR";
    }
    const sum = (hasDray ? drayN : 0) + (hasOcean ? oceanN : 0);
    if (!Number.isFinite(sum)) {
        return "ERROR";
    }
    return _exportWholeNumberString(sum);
}

/** Export view: numeric CIF / computed values display as whole numbers. */
function _exportWholeNumberString(raw) {
    if (raw === undefined || raw === null || raw === "") {
        return "";
    }
    const n = parseFloat(String(raw).replace(/,/g, ""));
    if (!Number.isFinite(n)) {
        return String(raw);
    }
    return String(Math.round(n));
}

function _exportCellValueForGroupRegion(cifByRegion, group, abbr) {
    const cifKey = _exportCifFieldForGroup(group);
    const cifRegion = EXPORT_REGION_TO_CIF[abbr];
    const cifRow = cifRegion ? cifByRegion[cifRegion] : null;
    if (!cifRow || !cifKey) return "";
    const raw = cifRow[cifKey];
    if (raw === undefined || raw === null || raw === "") return "";
    return _exportWholeNumberString(raw);
}

function _buildExportRows(cifByRegion, exportOpts) {
    const columns = _buildExportColumns();
    const cif = cifByRegion || {};

    const rows = [];
    EXPORT_DATA.forEach(entry => {
        entry.ports.forEach((port, i) => {
            const isFirst = i === 0;
            const row = {};
            columns.forEach(c => { row[c] = ""; });
            row["Base"] = isFirst ? entry.base : "";
            row["CIF FE"] = port;
            row._exportBaseGroup = entry.base;

            EXPORT_CIF_GROUP_LABELS.forEach(group => {
                EXPORT_REGIONS.forEach(abbr => {
                    const key = group + "|" + abbr;
                    if (EXPORT_BODY_POPULATED_GROUPS.has(group)) {
                        row[key] = _exportCellValueForGroupRegion(cif, group, abbr);
                    } else if (group === "Outbound Logistics") {
                        row[key] = _exportOutboundLogisticsBodyCell(cif, exportOpts, row, abbr);
                    }
                });
            });

            rows.push(row);
        });
    });
    return rows;
}

async function renderExportTable() {
    const content = document.getElementById("content");
    content.innerHTML = "";

    invalidateThemeCountryColorMapCache();

    const derivPanel = document.createElement("div");
    derivPanel.id = "export-cell-derivation";
    derivPanel.setAttribute("role", "status");
    derivPanel.setAttribute("aria-live", "polite");
    derivPanel.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace";
    derivPanel.style.fontSize = "12px";
    derivPanel.style.background = "#f8f8f0";
    derivPanel.style.border = "1px solid #ccc";
    derivPanel.style.borderRadius = "4px";
    derivPanel.style.padding = "10px 12px";
    derivPanel.style.margin = "0 0 12px 0";
    derivPanel.style.minHeight = "2.8em";
    derivPanel.style.color = "#555";
    derivPanel.style.whiteSpace = "pre-wrap";
    derivPanel.style.lineHeight = "1.45";
    derivPanel.style.maxWidth = "100%";
    derivPanel.textContent = "Click any cell in the Export table to see how that value was derived.";
    content.appendChild(derivPanel);

    const exportThemeColors = await getThemeCountryColorMapCached();

    let cifData = null;
    let oceanRaw = [];
    try {
        const [cifRes, oceanRes] = await Promise.all([
            fetch("/api/cif"),
            fetch("/api/ocean"),
        ]);
        if (cifRes.ok) cifData = await cifRes.json();
        if (oceanRes.ok) {
            const od = await oceanRes.json();
            oceanRaw = Array.isArray(od.rows) ? od.rows : [];
        }
    } catch (e) { /* proceed with partial data */ }
    const cifByRegion = {};
    if (cifData && cifData.rows) {
        cifData.rows.forEach(r => { cifByRegion[r.Region] = r; });
    }
    const oceanCfg = getViewConfig("Ocean Costing");
    const oceanColumns = (oceanCfg && oceanCfg.columns) ? oceanCfg.columns : [];
    const oceanCostingRows = dedupeOceanCostingRows(oceanRaw, oceanColumns);
    const exportCellOpts = {
        oceanCostingRows,
    };
    const columns = _buildExportColumns();
    const rows = _buildExportRows(cifByRegion, exportCellOpts);
    const regionCount = EXPORT_REGIONS.length;

    const derivationCtx = { cifByRegion, oceanCostingRows };

    function showExportDerivation(row, column, value, rowIdx) {
        const disp = value === "" || value === undefined ? '""' : String(value);
        const explain = _exportCellDerivation(row, column, rowIdx, derivationCtx);
        derivPanel.style.color = "#222";
        derivPanel.textContent = `${column} = ${disp}  ←  ${explain}`;
    }

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.flexWrap = "wrap";
    controls.style.gap = "8px";
    controls.style.alignItems = "center";
    controls.style.marginBottom = "10px";
    const baseSearchInput = document.createElement("input");
    baseSearchInput.type = "search";
    baseSearchInput.placeholder = "Search Base";
    baseSearchInput.setAttribute("aria-label", "Search Base");
    baseSearchInput.style.padding = "6px 10px";
    baseSearchInput.style.fontSize = "13px";
    baseSearchInput.style.minWidth = "160px";
    const cifFeSearchInput = document.createElement("input");
    cifFeSearchInput.type = "search";
    cifFeSearchInput.placeholder = "Search CIF FE";
    cifFeSearchInput.setAttribute("aria-label", "Search CIF FE");
    cifFeSearchInput.style.padding = "6px 10px";
    cifFeSearchInput.style.fontSize = "13px";
    cifFeSearchInput.style.minWidth = "160px";
    controls.appendChild(baseSearchInput);
    controls.appendChild(cifFeSearchInput);
    content.appendChild(controls);

    const table = document.createElement("table");
    table.className = "usd-table";
    const thead = document.createElement("thead");

    const dividerBorder = "3px solid #333";

    // Row 1: CIF group headers, each spanning 11 region columns
    const r1 = document.createElement("tr");
    const emptyTh = document.createElement("th");
    emptyTh.colSpan = 2;
    emptyTh.className = "usd-group-empty";
    r1.appendChild(emptyTh);
    EXPORT_CIF_GROUP_LABELS.forEach(label => {
        const th = document.createElement("th");
        th.colSpan = regionCount;
        th.textContent = label;
        th.className = "usd-group-header";
        th.style.borderLeft = dividerBorder;
        r1.appendChild(th);
    });
    thead.appendChild(r1);

    // Row 2: Country | City (labels) | then regions under each group
    const r2 = document.createElement("tr");
    const countryTh = document.createElement("th");
    countryTh.textContent = "Country";
    countryTh.className = "usd-sub-header";
    r2.appendChild(countryTh);
    const cityTh = document.createElement("th");
    cityTh.textContent = "City";
    cityTh.className = "usd-sub-header";
    r2.appendChild(cityTh);
    EXPORT_CIF_GROUP_LABELS.forEach(() => {
        EXPORT_REGIONS.forEach((label, ri) => {
            const th = document.createElement("th");
            th.textContent = label;
            th.className = "usd-sub-header";
            if (ri === 0) th.style.borderLeft = dividerBorder;
            r2.appendChild(th);
        });
    });
    thead.appendChild(r2);

    // Row 3: Base | CIF FE | CIF sample values per group × region
    const r3 = document.createElement("tr");
    columns.forEach((col, i) => {
        const th = document.createElement("th");
        th.className = "usd-sub-header";
        if (i < 2) {
            th.textContent = col;
        } else {
            const pipe = col.indexOf("|");
            if (pipe > 0) {
                const group = col.slice(0, pipe);
                const abbr = col.slice(pipe + 1);
                const v = _exportCellValueForGroupRegion(cifByRegion, group, abbr);
                th.textContent = v;
                th.className = "usd-sub-header td-num";
            }
        }
        if (i > 1 && (i - 2) % regionCount === 0) th.style.borderLeft = dividerBorder;
        r3.appendChild(th);
    });
    thead.appendChild(r3);

    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    table.appendChild(tbody);

    function redrawExportBody() {
        tbody.replaceChildren();
        const baseQ = baseSearchInput.value;
        const cifQ = cifFeSearchInput.value;
        const filtered = rows.filter((r) => _exportRowMatchesSearch(r, baseQ, cifQ));
        filtered.forEach((row, rowIdx) => {
            const tr = document.createElement("tr");
            const rowBg = _exportBaseCellBackground(
                String(row._exportBaseGroup || row.Base || "").trim(),
                exportThemeColors,
            );
            columns.forEach((col, i) => {
                const td = document.createElement("td");
                const val = row[col] ?? "";
                td.textContent = val;
                const isNumCol =
                    val !== "ERROR" &&
                    (col.indexOf("|") > 0 || typeof row[col] === "number");
                td.className = isNumCol ? "td-num" : "td-text";
                td.style.cursor = "pointer";
                td.title = "Click for derivation";
                td.addEventListener("click", () => {
                    showExportDerivation(row, col, val, rowIdx);
                });
                if (rowBg) {
                    td.style.backgroundColor = rowBg;
                }
                if (i > 1 && (i - 2) % regionCount === 0) td.style.borderLeft = dividerBorder;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    baseSearchInput.addEventListener("input", redrawExportBody);
    cifFeSearchInput.addEventListener("input", redrawExportBody);
    redrawExportBody();

    content.appendChild(table);
}

function openViewFromHash() {
    const h = location.hash.toLowerCase();
    const sel = document.getElementById("select_view");
    if (!sel) return;

    if (h === "#jarvis" || h === "#javis" || h === "#control-panel" || !h) {
        for (let i = 0; i < sel.options.length; i++) {
            if (sel.options[i].text === "Jarvis") { sel.selectedIndex = i; break; }
        }
    } else if (h === "#notes") {
        for (let i = 0; i < sel.options.length; i++) {
            if (sel.options[i].text === "Notes") { sel.selectedIndex = i; break; }
        }
    }
    select_view();
}

document.addEventListener("DOMContentLoaded", openViewFromHash);
window.addEventListener("hashchange", openViewFromHash);

/**
 * Hermes Frontend Interactive Client
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const browseBtn = document.getElementById("browseBtn");
  const sampleDataBtn = document.getElementById("sampleDataBtn");
  
  const datasetOverviewCard = document.getElementById("datasetOverviewCard");
  const activeFilename = document.getElementById("activeFilename");
  const statRows = document.getElementById("statRows");
  const statCols = document.getElementById("statCols");
  const statMissing = document.getElementById("statMissing");
  const statSize = document.getElementById("statSize");
  
  const llmStatusBadge = document.getElementById("llmStatusBadge");
  const llmStatusText = document.getElementById("llmStatusText");
  const datasetStatusBadge = document.getElementById("datasetStatusBadge");
  const datasetStatusText = document.getElementById("datasetStatusText");

  const queryForm = document.getElementById("queryForm");
  const questionInput = document.getElementById("questionInput");
  const askBtn = document.getElementById("askBtn");
  const btnText = askBtn.querySelector(".btn-text");
  const spinner = askBtn.querySelector(".spinner");
  const resultsFeed = document.getElementById("resultsFeed");
  const welcomeState = document.getElementById("welcomeState");

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  const promptChips = document.querySelectorAll(".chip");

  // Initial State Check
  checkSystemStatus();

  // -------------------------------------------------------------------------
  // Drag & Drop / File Upload Events
  // -------------------------------------------------------------------------
  browseBtn.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("click", (e) => {
    if (e.target !== browseBtn) fileInput.click();
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });

  sampleDataBtn.addEventListener("click", async () => {
    sampleDataBtn.disabled = true;
    sampleDataBtn.textContent = "⏳ Loading sample dataset...";
    try {
      const res = await fetch("/load-sample", { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        renderDatasetOverview(data.dataset);
      } else {
        alert(data.detail || "Failed to load sample dataset.");
      }
    } catch (err) {
      console.error(err);
      alert("Error connecting to server.");
    } finally {
      sampleDataBtn.disabled = false;
      sampleDataBtn.textContent = "⚡ Load Sample Sales Dataset";
    }
  });

  // -------------------------------------------------------------------------
  // Tab Switching
  // -------------------------------------------------------------------------
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetTab = document.getElementById(btn.dataset.tab);
      if (targetTab) targetTab.classList.add("active");
    });
  });

  // -------------------------------------------------------------------------
  // Quick Prompt Chips
  // -------------------------------------------------------------------------
  promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      questionInput.value = chip.textContent.trim();
      questionInput.focus();
      submitQuery(questionInput.value);
    });
  });

  // -------------------------------------------------------------------------
  // Form Submission
  // -------------------------------------------------------------------------
  queryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (q) submitQuery(q);
  });

  // Enter to submit (Shift+Enter for newline)
  questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const q = questionInput.value.trim();
      if (q) submitQuery(q);
    }
  });

  // -------------------------------------------------------------------------
  // API Call: Upload File
  // -------------------------------------------------------------------------
  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    dropZone.querySelector(".drop-title").textContent = `Uploading ${file.name}...`;

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (res.ok && data.success) {
        renderDatasetOverview(data.dataset);
      } else {
        alert(data.detail || "Upload failed. Please check file format.");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to upload file. Make sure server is running.");
    } finally {
      dropZone.querySelector(".drop-title").textContent = "Drag & drop CSV or Excel file here";
      fileInput.value = "";
    }
  }

  // -------------------------------------------------------------------------
  // API Call: System Status & Dataset Info
  // -------------------------------------------------------------------------
  async function checkSystemStatus() {
    try {
      const res = await fetch("/dataset-info");
      const data = await res.json();

      // Update Groq Status Badge
      if (data.system_status && data.system_status.groq_configured) {
        llmStatusBadge.className = "status-badge status-online";
        llmStatusText.textContent = `Groq LLM Ready (${data.system_status.groq_model})`;
      } else {
        llmStatusBadge.className = "status-badge status-warning";
        llmStatusText.textContent = "Groq Key Missing (Add to .env)";
      }

      // Update Dataset Overview if already loaded
      if (data.dataset && data.dataset.loaded) {
        renderDatasetOverview(data.dataset);
      }
    } catch (err) {
      console.error("System status check failed:", err);
    }
  }

  // -------------------------------------------------------------------------
  // Render Dataset Overview
  // -------------------------------------------------------------------------
  function renderDatasetOverview(dataset) {
    if (!dataset || !dataset.loaded) return;

    datasetOverviewCard.classList.remove("hidden");
    activeFilename.textContent = dataset.filename;
    statRows.textContent = Number(dataset.num_rows).toLocaleString();
    statCols.textContent = dataset.num_columns;
    statMissing.textContent = Number(dataset.total_missing_values).toLocaleString();
    statSize.textContent = `${dataset.file_size_kb} KB`;

    // Header Status update
    datasetStatusBadge.className = "status-badge status-online";
    datasetStatusText.textContent = `${dataset.filename} (${dataset.num_rows} rows)`;

    // 1. Columns & Schema Table
    const colTableBody = document.querySelector("#columnsTable tbody");
    colTableBody.innerHTML = "";
    (dataset.columns || []).forEach((c) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="mono font-semibold">${escapeHtml(c.name)}</td>
        <td><span class="file-tag">${escapeHtml(c.dtype)}</span></td>
        <td>${c.missing_count} (${c.missing_pct}%)</td>
        <td class="mono text-muted">${escapeHtml(JSON.stringify(c.sample_values || []))}</td>
      `;
      colTableBody.appendChild(tr);
    });

    // 2. Preview Table
    const previewHead = document.querySelector("#previewTable thead");
    const previewBody = document.querySelector("#previewTable tbody");
    previewHead.innerHTML = "";
    previewBody.innerHTML = "";

    if (dataset.preview_rows && dataset.preview_rows.length > 0) {
      const cols = dataset.column_names || Object.keys(dataset.preview_rows[0]);
      const headerTr = document.createElement("tr");
      cols.forEach((col) => {
        const th = document.createElement("th");
        th.textContent = col;
        headerTr.appendChild(th);
      });
      previewHead.appendChild(headerTr);

      dataset.preview_rows.forEach((row) => {
        const tr = document.createElement("tr");
        cols.forEach((col) => {
          const td = document.createElement("td");
          td.textContent = row[col] !== null ? row[col] : "—";
          tr.appendChild(td);
        });
        previewBody.appendChild(tr);
      });
    }

    // 3. Numeric Stats Table
    const statsHead = document.querySelector("#statsTable thead");
    const statsBody = document.querySelector("#statsTable tbody");
    statsHead.innerHTML = "";
    statsBody.innerHTML = "";

    const statsObj = dataset.numeric_stats || {};
    const numericCols = Object.keys(statsObj);

    if (numericCols.length > 0) {
      const metrics = Object.keys(statsObj[numericCols[0]] || {});
      const headerTr = document.createElement("tr");
      headerTr.innerHTML = "<th>Metric</th>" + numericCols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
      statsHead.appendChild(headerTr);

      metrics.forEach((metric) => {
        const tr = document.createElement("tr");
        let rowHtml = `<td class="mono font-semibold">${escapeHtml(metric)}</td>`;
        numericCols.forEach((col) => {
          const val = statsObj[col][metric];
          rowHtml += `<td>${val !== undefined ? val : "—"}</td>`;
        });
        tr.innerHTML = rowHtml;
        statsBody.appendChild(tr);
      });
    } else {
      statsBody.innerHTML = "<tr><td colspan='4'>No numeric columns available.</td></tr>";
    }
  }

  // -------------------------------------------------------------------------
  // API Call: Ask Question
  // -------------------------------------------------------------------------
  async function submitQuery(question) {
    // Show spinner
    askBtn.disabled = true;
    btnText.textContent = "Analyzing...";
    spinner.classList.remove("hidden");

    if (welcomeState) welcomeState.classList.add("hidden");

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();

      renderResultCard(question, data);
    } catch (err) {
      console.error(err);
      renderResultCard(question, {
        success: false,
        answer: "Failed to communicate with Hermes backend server.",
        analysis_type: "error",
      });
    } finally {
      askBtn.disabled = false;
      btnText.textContent = "Ask Hermes";
      spinner.classList.add("hidden");
    }
  }

  // -------------------------------------------------------------------------
  // Render Result Card in Feed
  // -------------------------------------------------------------------------
  function renderResultCard(question, data) {
    const card = document.createElement("div");
    card.className = "result-card";

    const analysisType = (data.analysis_type || "pandas").toLowerCase();
    const badgeClass = `badge-${analysisType}`;

    let codeBlockHtml = "";
    if (data.code_or_query) {
      const codeType = analysisType === "duckdb" ? "SQL Query" : "Python Code";
      codeBlockHtml = `
        <details class="code-details">
          <summary>🔍 View Generated ${codeType}</summary>
          <pre><code>${escapeHtml(data.code_or_query)}</code></pre>
        </details>
      `;
    }

    let chartHtml = "";
    if (data.chart_url) {
      // Add timestamp query parameter to prevent browser caching
      const chartUrlWithTs = `${data.chart_url}?t=${Date.now()}`;
      chartHtml = `
        <div class="chart-display">
          <img src="${chartUrlWithTs}" alt="Data Visualization" loading="lazy" />
        </div>
      `;
    }

    let tableHtml = "";
    if (data.result && Array.isArray(data.result) && data.result.length > 0) {
      const cols = data.columns || Object.keys(data.result[0]);
      let tableRows = "";
      data.result.slice(0, 15).forEach((row) => {
        tableRows += "<tr>" + cols.map((col) => `<td>${row[col] !== null ? escapeHtml(String(row[col])) : "—"}</td>`).join("") + "</tr>";
      });

      tableHtml = `
        <div class="table-container small-table">
          <table>
            <thead>
              <tr>${cols.map((col) => `<th>${escapeHtml(col)}</th>`).join("")}</tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      `;
    }

    // Markdown conversion for bold, headers, and bullet points
    const formattedAnswer = formatMarkdown(data.answer || "No response received.");

    let autoHealBadgeHtml = "";
    let healDetailsHtml = "";

    if (data.is_auto_healed) {
      const retries = data.retry_count || (data.healing_history ? data.healing_history.length : 1);
      autoHealBadgeHtml = `<span class="badge badge-autoheal">⚡ Auto-Healed (${retries} ${retries === 1 ? 'retry' : 'retries'})</span>`;
      
      if (data.healing_history && data.healing_history.length > 0) {
        let attemptsHtml = "";
        data.healing_history.forEach((h, idx) => {
          attemptsHtml += `
            <div class="heal-attempt-card">
              <span class="heal-attempt-title">Attempt #${idx + 1} Fix:</span>
              <div class="heal-error-text">❌ Error: ${escapeHtml(h.error || 'Execution Error')}</div>
              <div class="heal-fix-text">🛠️ Resolution: ${escapeHtml(h.fix_explanation || 'Auto-corrected query/code')}</div>
            </div>
          `;
        });

        healDetailsHtml = `
          <details class="heal-details">
            <summary>🛠️ Self-Healing Diagnostics (${data.healing_history.length} automatic correction${data.healing_history.length > 1 ? 's' : ''})</summary>
            ${attemptsHtml}
          </details>
        `;
      }
    }

    card.innerHTML = `
      <div class="result-card-header">
        <span class="user-question-title">❓ ${escapeHtml(question)}</span>
        <div class="badge-container">
          ${autoHealBadgeHtml}
          <span class="badge ${badgeClass}">${analysisType}</span>
        </div>
      </div>
      <div class="result-card-body">
        <div class="answer-box">
          ${formattedAnswer}
        </div>
        ${healDetailsHtml}
        ${chartHtml}
        ${tableHtml}
        ${codeBlockHtml}
      </div>
    `;

    // Insert at the top of results feed
    resultsFeed.insertBefore(card, resultsFeed.firstChild);
  }

  // -------------------------------------------------------------------------
  // Utilities
  // -------------------------------------------------------------------------
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Inline code `code`
    html = html.replace(/`(.*?)`/g, "<code class='file-tag'>$1</code>");
    // Headers ###
    html = html.replace(/^### (.*$)/gim, "<h4>$1</h4>");
    // Bullet lists
    html = html.replace(/^\* (.*$)/gim, "<li>$1</li>");
    html = html.replace(/^- (.*$)/gim, "<li>$1</li>");
    // Newlines to breaks
    html = html.replace(/\n/g, "<br>");
    return html;
  }
});

# Hermes — Local AI Data Analyst

**Hermes** is a local AI Data Analyst application that allows users to upload **CSV or Excel files** and ask questions about their data using natural language. It combines the power of **LangGraph**, **Groq LLM**, **Pandas**, **DuckDB**, and **Matplotlib** behind a modern, responsive single-page web interface.

---

## 1. Project Overview

Hermes acts as an autonomous data analyst on your local machine. When a user asks a question in plain English:
1. It analyzes the dataset's schema, data types, and values.
2. An intelligent **LangGraph Agent** routes the task to the most appropriate engine:
   - **Pandas** for descriptive stats, correlation, filtering, and data manipulation.
   - **DuckDB SQL** for relational queries, group-by aggregations, top-k ranking, and filtering.
   - **Matplotlib** for generating publication-ready charts (bar, line, pie, histogram, scatter).
3. The **Groq LLM** interprets the quantitative result or chart context and generates an insightful, professional natural language answer.

---

## 2. Architecture

```text
┌────────────────────────────────────────────────────────┐
│                   Web Frontend (UI)                    │
│     File Upload • Schema Inspector • Interactive Chat  │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP POST /upload | /ask
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
│         (app/main.py • app/data_loader.py)             │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                  LangGraph Workflow                    │
│               (app/graph.py • app/agent.py)            │
└───────┬───────────────────┬────────────────────┬───────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌────────────────┐
│  Pandas Tool  │   │  DuckDB Tool  │   │  Matplotlib    │
│ (app/tools/   │   │ (app/tools/   │   │ Visualization  │
│  pandas_tool) │   │  duckdb_tool) │   │(app/visualize) │
└───────┬───────┘   └───────┬───────┘   └────────┬───────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │ Tool Execution Results
┌───────────────────────────▼────────────────────────────┐
│                    Groq LLM Engine                     │
│               (ChatGroq / LLaMA 3.3 70B)               │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│           Final Markdown Answer & Visual Assets        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Features

* **Flexible File Ingestion**: Upload `.csv`, `.xlsx`, or `.xls` files. Includes a 1-click sample dataset loader.
* **Automated Data Profiling**: Instantly view row/column counts, memory usage, missing value metrics, column data types, and descriptive statistics.
* **Multi-Engine Query Routing**:
  * **Pandas**: Summary statistics, missing value analysis, correlations.
  * **DuckDB SQL**: Blazing-fast in-memory SQL execution over DataFrame tables.
  * **Matplotlib**: Automatic generation of bar charts, line trends, histograms, and pie charts.
* **LangGraph Agent Workflow**: State-managed reasoning cycle ensuring accurate tool invocation and answer synthesis.
* **Interactive Dashboard**: Modern dark-mode interface with live metric cards, tabbed data exploration, prompt chips, syntax-highlighted code accordions, and embedded charts.

---

## 4. Project Structure

```text
hermes/
│
├── app/
│   ├── main.py              # FastAPI application & REST endpoints
│   ├── llm.py               # Groq LLM client & environment configuration
│   ├── agent.py             # Hermes agent orchestration layer
│   ├── graph.py             # LangGraph state machine & routing workflow
│   ├── data_loader.py       # CSV/Excel parsing, profiling & state management
│   ├── analysis.py          # Data analysis helpers & JSON sanitizers
│   ├── visualization.py     # Matplotlib chart generator & asset manager
│   │
│   └── tools/
│       ├── pandas_tool.py   # Pandas execution tool
│       └── duckdb_tool.py   # DuckDB SQL execution tool
│
├── data/
│   └── uploads/             # Directory for stored uploaded datasets
│
├── generated/
│   └── charts/              # Directory for rendered PNG charts
│
├── frontend/
│   ├── index.html           # Single-page dashboard HTML
│   ├── style.css            # Dark/light modern CSS styles
│   └── script.js            # Asynchronous JavaScript client
│
├── sample_data/
│   └── sample_sales.csv     # Sample dataset for immediate testing
│
├── .env                     # Environment variables (Groq API Key)
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## 5. Installation

### Prerequisites
* Python 3.9, 3.10, 3.11, or 3.12 installed on your machine.

### Setup Steps
1. Open a terminal in the project root directory.
2. (Optional but recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   ```
   Activate the virtual environment:
   * **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
   * **Windows (CMD)**: `.\venv\Scripts\activate.bat`
   * **Linux/macOS**: `source venv/bin/activate`

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 6. Environment Setup

Configure your **Groq API Key** in the `.env` file located at the project root:

```env
# Add your Groq API Key below
GROQ_API_KEY=gsk_your_actual_groq_api_key_here

# Groq Model (default: llama-3.3-70b-versatile or llama3-70b-8192)
GROQ_MODEL=llama-3.3-70b-versatile
```

> **Note**: You can obtain a free Groq API key from [Groq Console](https://console.groq.com/).

---

## 7. How to Run

Start the Hermes backend server locally using Uvicorn:

```bash
uvicorn app.main:app --reload
```

Open your browser and navigate to:
```text
http://127.0.0.1:8000
```

---

## 8. How to Upload a Dataset

1. Open `http://127.0.0.1:8000`.
2. In the **Dataset Ingestion** card on the left:
   * **Option A**: Click **Browse File** or drag & drop any `.csv` or `.xlsx` file into the upload zone.
   * **Option B**: Click **⚡ Load Sample Sales Dataset** to instantly load the built-in sales dataset.
3. Once loaded, the **Dataset Overview** card will display:
   * Total row count, column count, missing value counts, and file size.
   * **Columns & Schema** tab: Lists every column, data type, null counts, and sample values.
   * **Data Preview** tab: Displays the first 10 rows.
   * **Stats Summary** tab: Shows mean, std, min, 25%, 50%, 75%, and max for all numeric columns.

---

## 9. Example Questions

Once a dataset is loaded, you can ask questions directly in the query box or click the suggestion chips:

### Pandas Analysis
* *"What is the average unit price and profit?"*
* *"What are the summary statistics of revenue?"*
* *"Are there any missing values in this dataset?"*
* *"What is the correlation between revenue and profit?"*

### DuckDB SQL Analysis
* *"Which department has the highest revenue?"*
* *"Show me the top 5 transactions by profit."*
* *"How many units were sold in each region?"*
* *"List distinct payment methods and their total revenue."*

### Visualization
* *"Show me a bar chart of revenue by department."*
* *"What is the monthly sales trend as a line chart?"*
* *"Show the distribution of unit prices as a histogram."*
* *"Create a pie chart showing sales by customer region."*

---

## 10. LangGraph Workflow with Self-Healing Error Correction

Hermes uses an autonomous compiled `StateGraph` equipped with an **Error-Correction Self-Healing Loop**:

```text
               [ understand_and_plan ]
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
     [ pandas_node ] [ duckdb_node ] [ visualization_node ]
           │              │              │
           └──────┬───────┴──────┬───────┘
                  │              │
          (on error &            │ (on success or
          retries < 2)           │  max retries)
                  │              │
                  ▼              │
          [ self_heal_node ]     │
                  │              │
       (loops back to tool)      │
                  │              │
                  └──────────────┼────────┐
                                 │        │
                                 ▼        ▼
                         [ synthesize_node ]
                                 ▼
                              [ END ]
```

1. **`understand_and_plan`**: The Groq LLM evaluates the user's question alongside the dataset schema and produces a JSON routing plan containing `analysis_type` (`pandas`, `duckdb`, `visualization`, or `direct`) and the initial executable code or query.
2. **`pandas_node`**: Executes Python Pandas data manipulations with `df` in local scope.
3. **`duckdb_node`**: Executes SQL against table `data` in an in-memory DuckDB database.
4. **`visualization_node`**: Generates a styled chart using Matplotlib and saves the PNG to `generated/charts/`.
5. **`self_heal_node` (Self-Healing Loop)**: If any tool node encounters a syntax error, invalid column reference, or execution exception, Hermes intercepts the error and routes the context, original query, and exception traceback back into Groq LLM to diagnose and auto-correct the query without failing.
6. **`synthesize_node`**: The Groq LLM receives the final numerical result, error state, or chart context and synthesizes a concise, professional markdown explanation.
7. **UI Diagnostics**: When auto-healing triggers, the frontend displays an animated `⚡ Auto-Healed` badge and a collapsible diagnostic report showing the original error and the correction applied.

---

## 11. Pandas Usage

When Pandas is selected, Hermes runs Python code against `df`:
```python
# Example: Aggregating average profit by category
result = df.groupby('category')['profit'].mean().reset_index()
```
The result is converted into structured JSON records and displayed as an interactive table with column headers in the UI.

---

## 12. DuckDB Usage

When SQL is selected, Hermes registers the active DataFrame as table `data` in DuckDB:
```sql
SELECT department, SUM(revenue) AS total_revenue
FROM data
GROUP BY department
ORDER BY total_revenue DESC
LIMIT 5;
```
DuckDB executes the query with zero-copy table scanning and returns the output directly to the user.

---

## 13. Visualization Workflow

When a visual request is made, Hermes:
1. Generates Matplotlib plotting code (using `fig`, `ax`, `plt`, and `df`).
2. Applies consistent styling (modern color palette, rotated axis labels, tight layout).
3. Renders the plot to `generated/charts/chart_<id>.png` using the headless `Agg` backend.
4. Serves the image via FastAPI at `/charts/chart_<id>.png`.
5. Displays the chart immediately within the chat result card.

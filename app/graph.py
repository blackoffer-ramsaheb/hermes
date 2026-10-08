"""Hermes LangGraph Workflow Module.

Defines the AgentState and LangGraph state graph for query understanding,
routing (Pandas, DuckDB, Visualization, Direct), execution, Self-Healing Error-Correction Loop,
and answer synthesis.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from app.llm import get_llm, is_groq_configured
from app.data_loader import dataset_manager
from app.tools.pandas_tool import PandasAnalysisTool
from app.tools.duckdb_tool import DuckDBAnalysisTool
from app.visualization import VisualizationEngine


class AgentState(TypedDict, total=False):
    """LangGraph State representation for Hermes analysis flow with Self-Healing."""
    question: str
    dataset_schema: str
    analysis_type: str  # "pandas" | "duckdb" | "visualization" | "direct"
    code_or_query: str
    reasoning: str
    tool_result: Optional[Dict[str, Any]]
    chart_url: Optional[str]
    final_answer: str
    error: Optional[str]
    retry_count: int
    max_retries: int
    is_auto_healed: bool
    healing_history: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Node 1: Understand Question & Plan Routing
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """You are Hermes, an expert AI Data Analyst.
Your role is to understand the user's question about a dataset and decide the most effective analysis approach.

You have three analysis tools:
1. "duckdb": Use DuckDB SQL when the question involves SQL aggregations, GROUP BY, WHERE filtering, TOP/LIMIT ranking, counts, sums, averages, or when relational querying is most natural. The table name is `data`.
   Example SQL: `SELECT department, SUM(revenue) AS total_revenue FROM data GROUP BY department ORDER BY total_revenue DESC LIMIT 5`

2. "pandas": Use Pandas when the query involves statistical summaries (describe, correlation, std), complex dataframe manipulations, missing value checks, or series operations. You write Python code operating on DataFrame `df`. Assign the final output to variable `result`.
   Example code: `result = df.groupby('category')['profit'].mean().reset_index()`

3. "visualization": Use Matplotlib when the user asks for a chart, graph, plot, visual representation, distribution, or visual comparison. You write Python code using `plt`, `ax`, and `df`. Do NOT call `plt.show()` - the system saves the figure automatically.
   Example code:
   `agg = df.groupby('department')['revenue'].sum()`
   `ax.bar(agg.index, agg.values, color='#3B82F6')`
   `ax.set_title('Revenue by Department')`
   `ax.set_ylabel('Total Revenue')`
   `plt.xticks(rotation=30, ha='right')`

4. "direct": Use direct only if the question is general or can be answered strictly from the schema info without querying.

Respond ONLY with valid JSON in the following format:
{
  "analysis_type": "duckdb" | "pandas" | "visualization" | "direct",
  "reasoning": "brief explanation of why this route was chosen",
  "code_or_query": "The SQL query or Python code snippet to execute"
}
"""


def understand_and_plan_node(state: AgentState) -> Dict[str, Any]:
    """Analyze the user's question with schema context and select the analysis path."""
    question = state.get("question", "")
    schema = state.get("dataset_schema", "")

    # Check if Groq API is configured
    if not is_groq_configured():
        # Heuristic fallback for offline/unconfigured state
        q_lower = question.lower()
        if any(w in q_lower for w in ["chart", "plot", "graph", "visual", "bar", "pie", "histogram"]):
            df = dataset_manager.get_active_dataframe()
            cat_cols = list(df.select_dtypes(include=["object"]).columns) if df is not None else []
            num_cols = list(df.select_dtypes(include=["number"]).columns) if df is not None else []
            x_col = cat_cols[0] if cat_cols else (df.columns[0] if df is not None else "x")
            y_col = num_cols[0] if num_cols else None

            code = (
                f"agg = df.groupby('{x_col}')['{y_col}'].sum().head(10)\n"
                f"ax.bar(agg.index.astype(str), agg.values, color='#3B82F6')\n"
                f"ax.set_title('Sum of {y_col} by {x_col}')\n"
                f"plt.xticks(rotation=30, ha='right')"
                if y_col else
                f"df['{x_col}'].value_counts().head(10).plot(kind='bar', ax=ax, color='#3B82F6')"
            )
            return {
                "analysis_type": "visualization",
                "reasoning": "Detected chart keyword (offline fallback)",
                "code_or_query": code,
                "retry_count": 0,
                "max_retries": 2,
                "is_auto_healed": False,
                "healing_history": [],
            }
        elif any(w in q_lower for w in ["select", "group by", "count", "sum", "average", "avg", "highest", "top", "lowest"]):
            return {
                "analysis_type": "duckdb",
                "reasoning": "Relational query (offline fallback)",
                "code_or_query": "SELECT * FROM data LIMIT 10",
                "retry_count": 0,
                "max_retries": 2,
                "is_auto_healed": False,
                "healing_history": [],
            }
        else:
            return {
                "analysis_type": "pandas",
                "reasoning": "Exploratory statistics (offline fallback)",
                "code_or_query": "result = df.describe()",
                "retry_count": 0,
                "max_retries": 2,
                "is_auto_healed": False,
                "healing_history": [],
            }

    try:
        llm = get_llm(temperature=0.0)
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Dataset Schema and Context:\n{schema}\n\nUser Question:\n{question}\n\nPlan the analysis:"
            ),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            plan = json.loads(json_match.group(0))
            return {
                "analysis_type": plan.get("analysis_type", "duckdb").lower(),
                "reasoning": plan.get("reasoning", "Plan determined by Hermes Agent."),
                "code_or_query": plan.get("code_or_query", "").strip(),
                "retry_count": 0,
                "max_retries": 2,
                "is_auto_healed": False,
                "healing_history": [],
            }
        else:
            return {
                "analysis_type": "duckdb",
                "reasoning": "Default SQL route",
                "code_or_query": "SELECT * FROM data LIMIT 10",
                "retry_count": 0,
                "max_retries": 2,
                "is_auto_healed": False,
                "healing_history": [],
            }
    except Exception as e:
        return {
            "analysis_type": "pandas",
            "reasoning": f"Planner encountered an error: {str(e)}",
            "code_or_query": "result = df.head(10)",
            "error": str(e),
            "retry_count": 0,
            "max_retries": 2,
            "is_auto_healed": False,
            "healing_history": [],
        }


# ---------------------------------------------------------------------------
# Node 2: Pandas Analysis Execution
# ---------------------------------------------------------------------------

def pandas_node(state: AgentState) -> Dict[str, Any]:
    """Execute Pandas code against active dataframe."""
    df = dataset_manager.get_active_dataframe()
    code = state.get("code_or_query", "")
    result = PandasAnalysisTool.execute(df, code)
    return {"tool_result": result}


# ---------------------------------------------------------------------------
# Node 3: DuckDB SQL Analysis Execution
# ---------------------------------------------------------------------------

def duckdb_node(state: AgentState) -> Dict[str, Any]:
    """Execute SQL query using DuckDB against active dataframe."""
    df = dataset_manager.get_active_dataframe()
    sql = state.get("code_or_query", "")
    result = DuckDBAnalysisTool.execute(df, sql)
    return {"tool_result": result}


# ---------------------------------------------------------------------------
# Node 4: Visualization Execution
# ---------------------------------------------------------------------------

def visualization_node(state: AgentState) -> Dict[str, Any]:
    """Execute visualization script to generate and save chart image."""
    df = dataset_manager.get_active_dataframe()
    code = state.get("code_or_query", "")
    viz_result = VisualizationEngine.execute_visualization(df, code)

    data_summary = None
    if df is not None:
        try:
            data_summary = df.head(5).to_dict(orient="records")
        except Exception:
            pass

    tool_result = {
        "success": viz_result.get("success", False),
        "data_type": "chart",
        "chart_url": viz_result.get("chart_url"),
        "error": viz_result.get("error"),
        "data": data_summary,
        "text_summary": f"Generated chart: {viz_result.get('chart_url')}" if viz_result.get("success") else None,
    }

    return {
        "chart_url": viz_result.get("chart_url"),
        "tool_result": tool_result,
    }


# ---------------------------------------------------------------------------
# Node 5: Self-Healing / Error Correction Loop Node
# ---------------------------------------------------------------------------

SELF_HEAL_SYSTEM_PROMPT = """You are Hermes Self-Healing Diagnostic Engine.
A previously generated data query or code snippet failed with an execution error.
Your job is to diagnose the failure, inspect the dataset schema, and output a corrected version of the code/SQL query that will succeed.

Guidelines:
1. Carefully check column names (case-sensitivity and exact spelling), data types, and syntax.
2. For DuckDB: Table is named `data`. Ensure valid DuckDB SQL functions.
3. For Pandas: Ensure variable `result` is assigned.
4. For Visualization: Ensure `ax` or `plt` is used properly without calling `plt.show()`.
5. Return ONLY valid JSON in this format:
{
  "fixed_code": "the corrected SQL query or Python script",
  "explanation": "brief explanation of what was fixed"
}
"""


def self_heal_node(state: AgentState) -> Dict[str, Any]:
    """Diagnose execution failure and generate corrected code/SQL."""
    question = state.get("question", "")
    schema = state.get("dataset_schema", "")
    analysis_type = state.get("analysis_type", "duckdb")
    failed_code = state.get("code_or_query", "")
    tool_result = state.get("tool_result") or {}
    error_msg = tool_result.get("error", "Unknown execution error")
    retry_count = state.get("retry_count", 0)
    history = list(state.get("healing_history", []))

    # If Groq is not configured, apply heuristic correction
    if not is_groq_configured():
        if analysis_type == "duckdb":
            fixed_code = "SELECT * FROM data LIMIT 10"
        elif analysis_type == "visualization":
            fixed_code = "df.iloc[:, 0].value_counts().head(10).plot(kind='bar', ax=ax)\nax.set_title('Overview')"
        else:
            fixed_code = "result = df.head(10)"

        history.append({
            "attempt": retry_count + 1,
            "failed_code": failed_code,
            "error": error_msg,
            "fixed_code": fixed_code,
            "fix_explanation": "Offline fallback heuristic applied.",
        })

        return {
            "code_or_query": fixed_code,
            "retry_count": retry_count + 1,
            "is_auto_healed": True,
            "healing_history": history,
        }

    try:
        llm = get_llm(temperature=0.0)
        user_prompt = (
            f"Dataset Schema:\n{schema}\n\n"
            f"User Question:\n{question}\n\n"
            f"Analysis Type:\n{analysis_type}\n\n"
            f"Failed Code/Query:\n{failed_code}\n\n"
            f"Execution Error Message:\n{error_msg}\n\n"
            f"Diagnose and fix the code/query:"
        )

        messages = [
            SystemMessage(content=SELF_HEAL_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            heal_data = json.loads(json_match.group(0))
            fixed_code = heal_data.get("fixed_code", failed_code)
            explanation = heal_data.get("explanation", "Self-healed query.")
        else:
            fixed_code = failed_code
            explanation = "Could not parse JSON fix."

        history.append({
            "attempt": retry_count + 1,
            "failed_code": failed_code,
            "error": error_msg,
            "fixed_code": fixed_code,
            "fix_explanation": explanation,
        })

        return {
            "code_or_query": fixed_code,
            "retry_count": retry_count + 1,
            "is_auto_healed": True,
            "healing_history": history,
        }

    except Exception as exc:
        history.append({
            "attempt": retry_count + 1,
            "failed_code": failed_code,
            "error": error_msg,
            "fixed_code": failed_code,
            "fix_explanation": f"Healing attempt failed: {str(exc)}",
        })
        return {
            "retry_count": retry_count + 1,
            "healing_history": history,
        }


# ---------------------------------------------------------------------------
# Node 6: Synthesize Final Natural Language Answer
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = """You are Hermes, a knowledgeable and concise AI Data Analyst.
Your goal is to provide a clear, professional, and insight-driven answer to the user's question based on the analysis results provided.

Guidelines:
1. Directly answer the user's question using the specific numbers, names, or values from the tool results.
2. Highlight key takeaways, maximums, minimums, or patterns when relevant.
3. Keep the tone professional, concise, and easy to read using Markdown formatting (bullet points, bold text for key figures).
4. If a chart was generated, mention what the chart displays.
5. If the query was self-healed, smoothly present the accurate final numbers.
6. If an error persists after retries, explain what happened constructively.
"""


def synthesize_node(state: AgentState) -> Dict[str, Any]:
    """Synthesize final user response using Groq LLM or structured formatting."""
    question = state.get("question", "")
    analysis_type = state.get("analysis_type", "")
    tool_result = state.get("tool_result") or {}
    chart_url = state.get("chart_url")
    is_auto_healed = state.get("is_auto_healed", False)

    # If Groq is not configured, generate a clean deterministic summary
    if not is_groq_configured():
        if chart_url:
            answer = (
                f"### Analysis Result\n\n"
                f"Generated visualization for your query: **{question}**.\n\n"
                f"The chart has been rendered and displayed below. "
                f"*(Tip: Configure `GROQ_API_KEY` in `.env` to enable deep AI insights and automated reasoning.)*"
            )
        elif tool_result.get("text_summary"):
            answer = (
                f"### Analysis Result\n\n"
                f"Results for **{question}** using **{analysis_type.upper()}**:\n\n"
                f"```\n{tool_result.get('text_summary')}\n```\n\n"
                f"*(Tip: Set your `GROQ_API_KEY` in `.env` for AI natural language synthesis.)*"
            )
        else:
            answer = f"Completed analysis for '{question}'."

        return {"final_answer": answer}

    # Use LLM to synthesize answer
    try:
        llm = get_llm(temperature=0.2)
        result_text = tool_result.get("text_summary", "No textual result.")
        error_text = tool_result.get("error", "")

        user_content = (
            f"User Question: {question}\n"
            f"Analysis Type Used: {analysis_type}\n"
            f"Code/Query Executed: {state.get('code_or_query', '')}\n"
            f"Result Summary:\n{result_text}\n"
        )
        if chart_url:
            user_content += f"\nA visualization chart was successfully created at {chart_url}.\n"
        if is_auto_healed:
            user_content += "\nNote: The query was automatically self-healed and corrected during execution.\n"
        if error_text and not tool_result.get("success"):
            user_content += f"\nExecution Note / Error: {error_text}\n"

        messages = [
            SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        response = llm.invoke(messages)
        return {"final_answer": response.content.strip()}
    except Exception as exc:
        fallback_ans = (
            f"Analysis for **{question}** executed via {analysis_type}.\n\n"
            f"{tool_result.get('text_summary', '')}"
        )
        return {"final_answer": fallback_ans, "error": str(exc)}


# ---------------------------------------------------------------------------
# Routing & Conditional Edges
# ---------------------------------------------------------------------------

def route_decision(state: AgentState) -> str:
    """Routing from planner to tool nodes."""
    route = state.get("analysis_type", "duckdb").lower()
    if route == "pandas":
        return "pandas_node"
    elif route == "visualization":
        return "visualization_node"
    elif route == "direct":
        return "synthesize_node"
    else:
        return "duckdb_node"


def check_tool_result_condition(state: AgentState) -> str:
    """Check if tool execution failed and whether we should self-heal or proceed."""
    tool_result = state.get("tool_result") or {}
    success = tool_result.get("success", True)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    # If execution failed and retries remain, loop into self-healing
    if not success and retry_count < max_retries:
        return "self_heal_node"

    # Otherwise continue to final synthesis
    return "synthesize_node"


def route_after_heal(state: AgentState) -> str:
    """Route from self_heal_node back to the corresponding execution engine."""
    route = state.get("analysis_type", "duckdb").lower()
    if route == "pandas":
        return "pandas_node"
    elif route == "visualization":
        return "visualization_node"
    else:
        return "duckdb_node"


def build_hermes_graph():
    """Construct and compile the LangGraph workflow with Self-Healing Loop."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("understand_and_plan", understand_and_plan_node)
    workflow.add_node("pandas_node", pandas_node)
    workflow.add_node("duckdb_node", duckdb_node)
    workflow.add_node("visualization_node", visualization_node)
    workflow.add_node("self_heal_node", self_heal_node)
    workflow.add_node("synthesize_node", synthesize_node)

    # Set Entry Point
    workflow.set_entry_point("understand_and_plan")

    # Edges from Planner
    workflow.add_conditional_edges(
        "understand_and_plan",
        route_decision,
        {
            "pandas_node": "pandas_node",
            "duckdb_node": "duckdb_node",
            "visualization_node": "visualization_node",
            "synthesize_node": "synthesize_node",
        },
    )

    # Conditional Edges from Tools to Self-Healing or Synthesis
    for node_name in ["pandas_node", "duckdb_node", "visualization_node"]:
        workflow.add_conditional_edges(
            node_name,
            check_tool_result_condition,
            {
                "self_heal_node": "self_heal_node",
                "synthesize_node": "synthesize_node",
            },
        )

    # Edge from Self-Healing back to the corresponding tool
    workflow.add_conditional_edges(
        "self_heal_node",
        route_after_heal,
        {
            "pandas_node": "pandas_node",
            "duckdb_node": "duckdb_node",
            "visualization_node": "visualization_node",
        },
    )

    # End
    workflow.add_edge("synthesize_node", END)

    return workflow.compile()


# Compile global graph instance
hermes_workflow = build_hermes_graph()

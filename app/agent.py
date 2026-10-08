"""Hermes Agent Runner Interface.

Coordinates query execution against the LangGraph workflow and packages
structured results for API responses and UI presentation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.data_loader import dataset_manager
from app.graph import hermes_workflow
from app.analysis import sanitize_for_json


class HermesAgent:
    """Agent orchestrator for handling natural language questions on active datasets."""

    @classmethod
    def ask(cls, question: str) -> Dict[str, Any]:
        """Execute a natural language query against the active dataset using LangGraph.

        Args:
            question: The user's natural language question.

        Returns:
            Dict containing answer, analysis_type, result table, chart_url, query code,
            and self-healing diagnostic history.
        """
        df = dataset_manager.get_active_dataframe()
        if df is None:
            return {
                "success": False,
                "question": question,
                "answer": "No dataset is currently loaded. Please upload a CSV or Excel file first.",
                "analysis_type": "none",
                "result": None,
                "chart_url": None,
                "code_or_query": None,
                "error": "Dataset not found",
                "is_auto_healed": False,
                "healing_history": [],
            }

        schema_context = dataset_manager.get_schema_summary_for_llm()

        initial_state = {
            "question": question.strip(),
            "dataset_schema": schema_context,
            "analysis_type": "",
            "code_or_query": "",
            "reasoning": "",
            "tool_result": None,
            "chart_url": None,
            "final_answer": "",
            "error": None,
            "retry_count": 0,
            "max_retries": 2,
            "is_auto_healed": False,
            "healing_history": [],
        }

        try:
            # Run LangGraph workflow
            final_state = hermes_workflow.invoke(initial_state)

            tool_result = final_state.get("tool_result") or {}
            analysis_type = final_state.get("analysis_type", "unknown")
            code_or_query = final_state.get("code_or_query", "")
            chart_url = final_state.get("chart_url")
            final_answer = final_state.get("final_answer", "")
            is_auto_healed = final_state.get("is_auto_healed", False)
            healing_history = final_state.get("healing_history", [])

            # Extract structured result data (for table/metric rendering on frontend)
            result_data = None
            columns = None
            if isinstance(tool_result, dict):
                result_data = tool_result.get("data")
                columns = tool_result.get("columns")

            return {
                "success": True,
                "question": question,
                "answer": final_answer,
                "analysis_type": analysis_type,
                "code_or_query": code_or_query,
                "columns": columns,
                "result": sanitize_for_json(result_data),
                "chart_url": chart_url,
                "error": final_state.get("error") or tool_result.get("error"),
                "is_auto_healed": is_auto_healed,
                "healing_history": sanitize_for_json(healing_history),
                "retry_count": final_state.get("retry_count", 0),
            }

        except Exception as exc:
            return {
                "success": False,
                "question": question,
                "answer": f"An error occurred while analyzing the dataset: {str(exc)}",
                "analysis_type": "error",
                "result": None,
                "chart_url": None,
                "code_or_query": None,
                "error": str(exc),
                "is_auto_healed": False,
                "healing_history": [],
            }

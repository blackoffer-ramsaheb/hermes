"""Hermes Pandas Analysis Tool.

Executes Pandas data transformations, aggregations, filtering, statistical calculations,
and exploratory analysis against the active dataset.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class PandasAnalysisTool:
    """Executes pandas python code expressions or scripts safely on a DataFrame."""

    @staticmethod
    def clean_code(code: str) -> str:
        """Extract clean Python code from markdown code blocks if present."""
        code = code.strip()
        code_block_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", code, re.IGNORECASE)
        if code_block_match:
            return code_block_match.group(1).strip()
        return code

    @classmethod
    def execute(cls, df: pd.DataFrame, code: str) -> Dict[str, Any]:
        """Execute Python pandas code with `df` in local scope.

        The code can set `result` variable or have an expression as the final evaluation.
        """
        if df is None:
            return {
                "success": False,
                "error": "No DataFrame available to execute pandas code.",
                "data": None,
                "text_summary": None,
            }

        cleaned_code = cls.clean_code(code)

        # Restricted execution environment with df, pd, np
        local_scope: Dict[str, Any] = {
            "df": df.copy(),
            "pd": pd,
            "np": np,
            "result": None,
        }

        # Global scope with built-ins needed for standard data operations
        global_scope = {
            "__builtins__": {
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "min": min,
                "max": max,
                "sum": sum,
                "round": round,
                "sorted": sorted,
                "print": print,
            }
        }

        try:
            # First attempt single expression evaluation if single line or result assignment
            lines = [l.strip() for l in cleaned_code.splitlines() if l.strip() and not l.strip().startswith("#")]
            
            # If multi-line, execute with exec()
            exec(cleaned_code, global_scope, local_scope)

            result_val = local_scope.get("result")
            # If 'result' was not explicitly assigned, check if the last line created a variable or value
            if result_val is None and len(lines) == 1:
                # Try evaluating as expression
                try:
                    result_val = eval(lines[0], global_scope, local_scope)
                except Exception:
                    pass

            return cls._format_result(result_val, cleaned_code)

        except Exception as exc:
            return {
                "success": False,
                "error": f"Pandas Execution Error: {str(exc)}",
                "code": cleaned_code,
                "data": None,
                "text_summary": None,
            }

    @classmethod
    def _format_result(cls, res: Any, code: str) -> Dict[str, Any]:
        """Format the execution output into structured JSON-compatible dictionaries."""
        if res is None:
            return {
                "success": True,
                "code": code,
                "data_type": "none",
                "data": None,
                "text_summary": "Execution completed with no return value.",
            }

        if isinstance(res, pd.DataFrame):
            # Limit rows for output payload
            preview_df = res.head(50).replace({np.nan: None})
            return {
                "success": True,
                "code": code,
                "data_type": "dataframe",
                "columns": list(res.columns),
                "shape": [int(res.shape[0]), int(res.shape[1])],
                "data": preview_df.to_dict(orient="records"),
                "text_summary": f"DataFrame with {len(res)} rows and {len(res.columns)} columns:\n{res.head(10).to_string()}",
            }

        if isinstance(res, pd.Series):
            res_df = res.reset_index()
            res_df.columns = [str(c) for c in res_df.columns]
            preview_df = res_df.head(50).replace({np.nan: None})
            return {
                "success": True,
                "code": code,
                "data_type": "series",
                "columns": list(res_df.columns),
                "data": preview_df.to_dict(orient="records"),
                "text_summary": f"Series ({res.name or 'result'}):\n{res.head(10).to_string()}",
            }

        if isinstance(res, (int, float, np.integer, np.floating)):
            val = round(float(res), 4) if isinstance(res, (float, np.floating)) else int(res)
            return {
                "success": True,
                "code": code,
                "data_type": "scalar",
                "data": val,
                "text_summary": str(val),
            }

        if isinstance(res, (list, tuple)):
            return {
                "success": True,
                "code": code,
                "data_type": "list",
                "data": list(res)[:50],
                "text_summary": str(list(res)[:20]),
            }

        if isinstance(res, dict):
            return {
                "success": True,
                "code": code,
                "data_type": "dict",
                "data": res,
                "text_summary": str(res),
            }

        return {
            "success": True,
            "code": code,
            "data_type": "string",
            "data": str(res),
            "text_summary": str(res),
        }

"""Hermes DuckDB SQL Analysis Tool.

Executes SQL queries against the active dataset using DuckDB's in-memory SQL engine.
The active dataset is registered as table 'data'.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd
import numpy as np


class DuckDBAnalysisTool:
    """Executes SQL queries over an in-memory DataFrame registered as table `data`."""

    @staticmethod
    def clean_sql(sql_query: str) -> str:
        """Extract clean SQL string from markdown code blocks if present."""
        query = sql_query.strip()
        sql_block_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", query, re.IGNORECASE)
        if sql_block_match:
            query = sql_block_match.group(1).strip()
        return query

    @classmethod
    def execute(cls, df: pd.DataFrame, sql_query: str) -> Dict[str, Any]:
        """Execute a SQL query against table `data` (backed by df).

        Args:
            df: Active pandas DataFrame.
            sql_query: SQL statement (e.g. 'SELECT department, SUM(revenue) FROM data GROUP BY department').

        Returns:
            Dict containing success status, columns, rows, data, and text summary.
        """
        if df is None:
            return {
                "success": False,
                "error": "No dataset available to query with DuckDB.",
                "data": None,
                "text_summary": None,
            }

        cleaned_sql = cls.clean_sql(sql_query)

        try:
            con = duckdb.connect(database=":memory:")
            # Register dataframe as table 'data'
            con.register("data", df)

            # Also register case-insensitive or table name variations if needed
            con.register("dataset", df)
            con.register("df", df)

            # Execute query and convert to pandas DataFrame
            result_df: pd.DataFrame = con.execute(cleaned_sql).fetchdf()
            con.close()

            preview_df = result_df.head(50).replace({np.nan: None})

            return {
                "success": True,
                "sql": cleaned_sql,
                "data_type": "table",
                "columns": list(result_df.columns),
                "shape": [int(result_df.shape[0]), int(result_df.shape[1])],
                "data": preview_df.to_dict(orient="records"),
                "text_summary": (
                    f"SQL Result ({len(result_df)} rows):\n{result_df.head(10).to_string()}"
                    if not result_df.empty
                    else "Query returned 0 rows."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"DuckDB SQL Error: {str(exc)}",
                "sql": cleaned_sql,
                "data": None,
                "text_summary": None,
            }

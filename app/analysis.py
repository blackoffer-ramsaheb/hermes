"""Hermes Analysis Helper Utilities.

Provides profiling utilities, dataset summary formatters, and analysis metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


def format_dataframe_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate quick statistical metrics on the dataset for prompt enrichment."""
    if df is None or df.empty:
        return {}

    summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
        "missing_counts": df.isna().sum().to_dict(),
        "numeric_columns": list(df.select_dtypes(include=[np.number]).columns),
        "categorical_columns": list(df.select_dtypes(include=["object", "category"]).columns),
        "datetime_columns": list(df.select_dtypes(include=["datetime64"]).columns),
    }
    return summary


def sanitize_for_json(data: Any) -> Any:
    """Recursively convert NumPy and Pandas types into standard JSON serializable types."""
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, np.ndarray):
        return [sanitize_for_json(item) for item in data.tolist()]
    elif isinstance(data, (pd.Timestamp, np.datetime64)):
        return str(data)
    elif pd.isna(data):
        return None
    return data

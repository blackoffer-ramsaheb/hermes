"""Hermes Data Loader Module.

Handles dataset uploading, format parsing (CSV/XLSX), metadata extraction,
descriptive statistics generation, and active dataset state management.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DatasetManager:
    """Manages the currently active dataset in memory and disk storage."""

    _instance: Optional[DatasetManager] = None

    def __init__(self):
        self.active_dataframe: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None
        self.file_path: Optional[str] = None
        self.file_size_bytes: int = 0

    @classmethod
    def get_instance(cls) -> DatasetManager:
        """Singleton pattern for managing the single active dataset session."""
        if cls._instance is None:
            cls._instance = DatasetManager()
        return cls._instance

    def load_file(self, source_path: str | Path, original_filename: str) -> Dict[str, Any]:
        """Load a CSV or Excel file into pandas DataFrame and update active state."""
        source_path = Path(source_path)
        ext = source_path.suffix.lower()

        if ext == ".csv":
            # Try utf-8 first, fallback to latin-1
            try:
                df = pd.read_csv(source_path)
            except UnicodeDecodeError:
                df = pd.read_csv(source_path, encoding="latin-1")
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(source_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Only .csv and .xlsx/.xls are supported.")

        # Clean column names (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]

        self.active_dataframe = df
        self.filename = original_filename
        self.file_path = str(source_path)
        self.file_size_bytes = source_path.stat().st_size if source_path.exists() else 0

        return self.get_dataset_overview()

    def save_and_load_uploaded_file(self, upload_file_obj, filename: str) -> Dict[str, Any]:
        """Save an uploaded file to data/uploads/ and load it into memory."""
        safe_filename = Path(filename).name
        target_path = UPLOAD_DIR / safe_filename

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(upload_file_obj, buffer)

        return self.load_file(target_path, safe_filename)

    def get_dataset_overview(self) -> Dict[str, Any]:
        """Generate comprehensive metadata, statistics, and preview for active dataset."""
        if self.active_dataframe is None:
            return {
                "loaded": False,
                "message": "No dataset currently loaded. Please upload a CSV or Excel file.",
            }

        df = self.active_dataframe

        # Column schema and missing values
        columns_info: List[Dict[str, Any]] = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            missing_count = int(df[col].isna().sum())
            missing_pct = round((missing_count / len(df)) * 100, 2) if len(df) > 0 else 0
            unique_count = int(df[col].nunique(dropna=True))

            # Sample values for preview
            sample_non_null = df[col].dropna().head(3).tolist()

            columns_info.append({
                "name": col,
                "dtype": dtype_str,
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "unique_count": unique_count,
                "sample_values": sample_non_null,
            })

        # Numeric and categorical descriptive statistics
        numeric_df = df.select_dtypes(include=[np.number])
        numeric_stats: Dict[str, Any] = {}
        if not numeric_df.empty:
            desc = numeric_df.describe().round(2).to_dict()
            numeric_stats = desc

        # Replace NaN/inf with None for JSON compliance
        preview_df = df.head(10).replace({np.nan: None})
        preview_records = preview_df.to_dict(orient="records")

        return {
            "loaded": True,
            "filename": self.filename,
            "file_size_kb": round(self.file_size_bytes / 1024, 2),
            "num_rows": int(len(df)),
            "num_columns": int(len(df.columns)),
            "column_names": list(df.columns),
            "columns": columns_info,
            "total_missing_values": int(df.isna().sum().sum()),
            "numeric_stats": numeric_stats,
            "preview_rows": preview_records,
        }

    def get_active_dataframe(self) -> Optional[pd.DataFrame]:
        """Return the current active pandas DataFrame."""
        return self.active_dataframe

    def get_schema_summary_for_llm(self) -> str:
        """Create a compact string representation of the dataset schema for LLM context."""
        if self.active_dataframe is None:
            return "No dataset loaded."

        df = self.active_dataframe
        lines = [
            f"Dataset Name: {self.filename}",
            f"Shape: {len(df)} rows x {len(df.columns)} columns",
            "Columns & Types:",
        ]
        for col in df.columns:
            dtype = df[col].dtype
            nulls = df[col].isna().sum()
            sample_vals = df[col].dropna().head(3).tolist()
            lines.append(f" - {col} ({dtype}): {nulls} nulls, sample values: {sample_vals}")

        return "\n".join(lines)


# Helper singleton getter
dataset_manager = DatasetManager.get_instance()

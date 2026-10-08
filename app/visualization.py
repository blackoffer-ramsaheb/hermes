"""Hermes Visualization Engine.

Generates charts (bar, line, histogram, pie, scatter) using Matplotlib,
styles them with a modern aesthetic, and saves them to `generated/charts/`.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import matplotlib

# Use headless Agg backend for thread-safe server rendering
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Output directory for generated charts
BASE_DIR = Path(__file__).resolve().parent.parent
CHARTS_DIR = BASE_DIR / "generated" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


class VisualizationEngine:
    """Manages creation, execution, and export of matplotlib charts."""

    @staticmethod
    def clean_code(code: str) -> str:
        """Extract clean python code from markdown code blocks."""
        code = code.strip()
        match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", code, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return code

    @classmethod
    def execute_visualization(cls, df: pd.DataFrame, code: str) -> Dict[str, Any]:
        """Execute custom matplotlib Python script on `df` and save output chart.

        The script has access to `df`, `plt`, `pd`, `np`, and `fig`.
        """
        if df is None:
            return {
                "success": False,
                "error": "No dataset available for visualization.",
                "chart_url": None,
            }

        cleaned_code = cls.clean_code(code)
        chart_id = f"chart_{uuid.uuid4().hex[:8]}.png"
        output_file = CHARTS_DIR / chart_id

        # Setup plot aesthetic
        plt.close("all")
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, ax = plt.subplots(figsize=(9, 5), dpi=130)

        local_scope: Dict[str, Any] = {
            "df": df.copy(),
            "pd": pd,
            "np": np,
            "plt": plt,
            "fig": fig,
            "ax": ax,
        }

        global_scope = {
            "__builtins__": {
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "min": min,
                "max": max,
                "round": round,
                "print": print,
            }
        }

        try:
            exec(cleaned_code, global_scope, local_scope)

            # Improve layout and typography
            plt.tight_layout()
            plt.savefig(output_file, bbox_inches="tight", dpi=130)
            plt.close("all")

            return {
                "success": True,
                "chart_filename": chart_id,
                "chart_url": f"/charts/{chart_id}",
                "code": cleaned_code,
            }

        except Exception as exc:
            plt.close("all")
            return {
                "success": False,
                "error": f"Visualization Execution Error: {str(exc)}",
                "chart_url": None,
                "code": cleaned_code,
            }

    @classmethod
    def generate_chart_auto(
        cls,
        df: pd.DataFrame,
        chart_type: str,
        x_col: str,
        y_col: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience generator for standard chart types (bar, line, hist, pie)."""
        chart_id = f"chart_{uuid.uuid4().hex[:8]}.png"
        output_file = CHARTS_DIR / chart_id

        plt.close("all")
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, ax = plt.subplots(figsize=(9, 5), dpi=130)

        palette = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6"]

        try:
            chart_type = chart_type.lower().strip()
            if chart_type == "bar":
                if y_col:
                    agg = df.groupby(x_col)[y_col].sum().reset_index()
                    ax.bar(agg[x_col].astype(str), agg[y_col], color=palette[0], edgecolor="none", alpha=0.9)
                    ax.set_ylabel(y_col)
                else:
                    counts = df[x_col].value_counts().head(10)
                    ax.bar(counts.index.astype(str), counts.values, color=palette[0], edgecolor="none", alpha=0.9)
                    ax.set_ylabel("Count")
                ax.set_xlabel(x_col)
                plt.xticks(rotation=30, ha="right")

            elif chart_type == "line":
                if y_col:
                    agg = df.groupby(x_col)[y_col].sum().reset_index()
                    ax.plot(agg[x_col].astype(str), agg[y_col], marker="o", color=palette[0], linewidth=2.5)
                    ax.set_ylabel(y_col)
                ax.set_xlabel(x_col)
                plt.xticks(rotation=30, ha="right")

            elif chart_type == "hist" or chart_type == "histogram":
                data_col = y_col or x_col
                ax.hist(df[data_col].dropna(), bins=20, color=palette[1], edgecolor="white", alpha=0.85)
                ax.set_xlabel(data_col)
                ax.set_ylabel("Frequency")

            elif chart_type == "pie":
                counts = df[x_col].value_counts().head(8)
                ax.pie(
                    counts.values,
                    labels=counts.index.astype(str),
                    autopct="%1.1f%%",
                    colors=palette[:len(counts)],
                    startangle=140,
                )

            elif chart_type == "scatter" and y_col:
                ax.scatter(df[x_col], df[y_col], color=palette[2], alpha=0.7, edgecolors="none")
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)

            ax.set_title(title or f"{chart_type.capitalize()} of {y_col or x_col}", fontsize=13, fontweight="bold", pad=12)
            plt.tight_layout()
            plt.savefig(output_file, bbox_inches="tight", dpi=130)
            plt.close("all")

            return {
                "success": True,
                "chart_filename": chart_id,
                "chart_url": f"/charts/{chart_id}",
            }

        except Exception as exc:
            plt.close("all")
            return {
                "success": False,
                "error": f"Auto Chart Error: {str(exc)}",
                "chart_url": None,
            }

"""Hermes FastAPI Application.

Main entry point providing endpoints for file upload, dataset profiling,
natural language querying via LangGraph agent, and static asset serving.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.data_loader import dataset_manager
from app.agent import HermesAgent
from app.llm import is_groq_configured, get_groq_model_name

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
CHARTS_DIR = BASE_DIR / "generated" / "charts"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Ensure directories exist
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI App
app = FastAPI(
    title="Hermes AI Data Analyst",
    description="Local AI Data Analyst for CSV and Excel files using LangGraph & Groq",
    version="1.0.0",
)

# Enable CORS for local testing flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file routes
app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class QuestionRequest(BaseModel):
    """Payload for /ask endpoint."""
    question: str


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def get_index():
    """Serve the single-page frontend interface."""
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(str(index_file))


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV or XLSX file, profile the dataset, and initialize active session."""
    filename = file.filename or "uploaded_data.csv"
    ext = Path(filename).suffix.lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Supported types are .csv, .xlsx, and .xls",
        )

    try:
        overview = dataset_manager.save_and_load_uploaded_file(file.file, filename)
        return {
            "success": True,
            "message": f"Successfully loaded '{filename}'",
            "dataset": overview,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(exc)}")


@app.get("/dataset-info")
def get_dataset_info():
    """Retrieve detailed metadata, schema, and sample rows for the active dataset."""
    overview = dataset_manager.get_dataset_overview()
    groq_ready = is_groq_configured()
    return {
        "success": True,
        "dataset": overview,
        "system_status": {
            "groq_configured": groq_ready,
            "groq_model": get_groq_model_name() if groq_ready else "Not Configured",
        },
    }


@app.post("/ask")
def ask_question(req: QuestionRequest):
    """Ask a natural language question about the active dataset."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = HermesAgent.ask(req.question)
    return result


@app.post("/load-sample")
def load_sample_dataset():
    """Convenience endpoint to load the bundled sample sales dataset."""
    sample_file = SAMPLE_DATA_DIR / "sample_sales.csv"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="Sample dataset not found.")

    try:
        overview = dataset_manager.load_file(sample_file, "sample_sales.csv")
        return {
            "success": True,
            "message": "Loaded sample sales dataset successfully.",
            "dataset": overview,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load sample dataset: {str(exc)}")

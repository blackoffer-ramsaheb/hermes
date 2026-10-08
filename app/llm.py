"""Hermes LLM Configuration Module.

Handles Groq Chat Model initialization and configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables from .env file located at root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_groq_api_key() -> str:
    """Retrieve the Groq API key from environment variables."""
    return os.getenv("GROQ_API_KEY", "").strip()


def get_groq_model_name() -> str:
    """Retrieve configured Groq model name or fallback to a default."""
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def is_groq_configured() -> bool:
    """Check if a valid non-placeholder Groq API key is present."""
    key = get_groq_api_key()
    return bool(key and key != "your_groq_api_key_here")


def get_llm(temperature: float = 0.0) -> ChatGroq:
    """Return an initialized ChatGroq LLM client.

    Raises:
        ValueError: If GROQ_API_KEY is not configured in .env.
    """
    api_key = get_groq_api_key()
    if not is_groq_configured():
        raise ValueError(
            "GROQ_API_KEY is not configured. Please set your valid Groq API key in the .env file."
        )

    model_name = get_groq_model_name()
    return ChatGroq(
        groq_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
    )

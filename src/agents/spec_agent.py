import os
from typing import Optional
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas import SpecArtifact


def _read_secret(name: str) -> str:
    val = os.getenv(name, "").strip().strip(chr(34)).strip(chr(39))
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(name, "")).strip().strip(chr(34)).strip(chr(39))
    except Exception:
        return ""


def get_gemini_llm(temperature: float = 0.0) -> BaseChatModel:
    load_dotenv(override=True)
    api_key = _read_secret("GOOGLE_API_KEY") or _read_secret("OPENAI_API_KEY")
    model_name = _read_secret("GEMINI_MODEL") or "gemini-3.8-flash"
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY in .env or Streamlit Secrets.")
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, api_key=api_key)


SPEC_SYSTEM_PROMPT = (
    "You are a Principal Product & Requirements Engineer. "
    "Decompose the user feature request into a deterministic technical specification. "
    "Define exact Python class/function interfaces in interfaces, explicit concurrency/edge-case "
    "requirements in requirements, and concrete pytest test scenarios in test_cases. "
    "All code must target standard library Python 3.11+ with zero third-party runtime dependencies."
)


def run_spec_agent(user_request: str, llm: Optional[BaseChatModel] = None) -> SpecArtifact:
    model = llm or get_gemini_llm(temperature=0.0)
    structured_llm = model.with_structured_output(SpecArtifact)
    result = structured_llm.invoke([
        SystemMessage(content=SPEC_SYSTEM_PROMPT),
        HumanMessage(content=f"Feature Request:\n{user_request.strip()}"),
    ])
    if isinstance(result, SpecArtifact):
        return result
    return SpecArtifact.model_validate(result)

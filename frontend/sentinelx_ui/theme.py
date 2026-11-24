"""Loads the shared design system. Every page calls ``apply_theme()`` once."""
from pathlib import Path

import streamlit as st

_FRONTEND = Path(__file__).resolve().parent.parent
_FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
          "&family=Space+Grotesk:wght@500;600;700&display=swap');")


def _read(name: str) -> str:
    path = _FRONTEND / name if name == "theme.css" else Path(__file__).resolve().parent / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def apply_theme(dashboard: bool = False) -> None:
    css = _FONTS + _read("theme.css") + _read("components.css") + (_read("dashboard.css") if dashboard else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

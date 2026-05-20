"""
app.py
------
Streamlit entry point for the CognitBotz Voice AI Consultant application.

Design rationale:
  - Simple, robust startup that sets page configuration and renders the UI.
  - Adds the parent directory to sys.path to allow imports from local packages.
"""

import sys
import warnings
import faulthandler
from pathlib import Path

# Enable faulthandler to output stack traces on C-level crashes
faulthandler.enable()

# Suppress all deprecation, future, and user warnings to keep terminal output clean
warnings.filterwarnings("ignore")

import streamlit as st

# Configure the Streamlit page before any other modules load.
# Page title, icon, and wide layout are set once here.
st.set_page_config(
    page_title="CognitBotz Voice AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure the voice_agent package folder is on the Python path
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from frontend.ui import render_full_ui
from utils.logger import get_logger

logger = get_logger("app")


def main() -> None:
    """Run the Streamlit application."""
    try:
        render_full_ui()
    except Exception as exc:
        logger.critical(f"Application crashed: {exc}", exc_info=True)
        st.error(
            f"A critical error occurred while running the application:\n\n"
            f"```{exc}```\n\n"
            f"Please check the application logs for details."
        )


if __name__ == "__main__":
    main()

import streamlit as st
from datetime import datetime
from typing import Any
import sys

class Logger:
    def __init__(self):
        if 'debug_logs' not in st.session_state:
            st.session_state.debug_logs = []
        self.original_stdout = sys.stdout

    def log(self, *args: Any, **kwargs: Any):
        """Log a message to both streamlit and console"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        message = " ".join(map(str, args))
        
        # Log to console
        print(f"\n[{timestamp}] {message}", file=self.original_stdout)
        
        # Log to streamlit session state
        try:
            if hasattr(st, 'session_state'):
                st.session_state.debug_logs.append(f"[{timestamp}] {message}")
        except:
            pass  # Ignore streamlit logging errors

# Create a global logger instance
logger = Logger()

def log_debug(*args: Any, **kwargs: Any):
    """Global logging function"""
    logger.log(*args, **kwargs)
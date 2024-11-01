import os
import sys
import streamlit as st

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.visualizers.tabs.events_tab import render_events_tab
from src.visualizers.tabs.markets_tab import render_markets_tab
from src.visualizers.tabs.logs_tab import render_logs_tab

def run_dashboard():
    """Main function to run the dashboard."""
    st.set_page_config(page_title="ArbiTrade", layout="wide")
    st.title("ArbiTrade")
    
    # Initialize session state
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    if 'selected_events' not in st.session_state:
        st.session_state.selected_events = set()
    if 'selected_state' not in st.session_state:
        st.session_state.selected_state = {}
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Events", "Markets", "Logs"])
    
    # Render each tab
    with tab1:
        render_events_tab()
    
    with tab2:
        render_markets_tab()
    
    with tab3:
        render_logs_tab()

if __name__ == "__main__":
    run_dashboard()
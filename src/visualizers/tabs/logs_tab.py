import streamlit as st

display_length = 200

def render_logs_tab():
    """Render the Debug Log tab content."""
    st.header("Debug Log")
    
    col1, col2 = st.columns([6,1])
    with col1:
        st.text("Real-time debug output")
    with col2:
        if st.button("Clear Log"):
            st.session_state.debug_logs = []
    
    # Display logs in reverse chronological order with expanders
    for i, log in enumerate(reversed(st.session_state.debug_logs)):
        # Create a preview of the log message (first 50 chars)
        preview = log[:display_length] + "..." if len(log) > display_length else log
        
        # Create an expander with the preview as the label
        with st.expander(preview):
            st.write(log) 
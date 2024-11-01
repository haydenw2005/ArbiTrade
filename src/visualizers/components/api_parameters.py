import streamlit as st

def render_api_parameters():
    """Render API parameters section and return the selected parameters."""
    with st.expander("📲 API Parameters"):
        col1, col2 = st.columns(2)
        
        with col1:
            limit = st.number_input(
                "Number of results (1-200):",
                min_value=1,
                max_value=200,
                value=100
            )
            
            status_options = ['open', 'closed', 'settled', 'unopened']
            selected_statuses = st.multiselect(
                "Status:",
                options=status_options,
                default=['open']
            )
            status = ','.join(selected_statuses) if selected_statuses else 'open'
            with_nested_markets = st.checkbox("Include nested markets", value=True)
        
        with col2:
            series_ticker = st.text_input("Series Ticker (optional):")
            
            cursor = st.text_input("Cursor (for pagination):")
    
    return {
        'limit': limit,
        'status': status,
        'series_ticker': series_ticker if series_ticker else None,
        'with_nested_markets': with_nested_markets,
        'cursor': cursor if cursor else None
    } 
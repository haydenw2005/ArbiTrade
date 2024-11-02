import streamlit as st
import pandas as pd
from typing import List
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.grid_options_builder import GridOptionsBuilder
import asyncio

from src.visualizers.components.api_parameters import render_api_parameters
from src.data_collectors.kalshi_scraper import KalshiScraper
from src.utils.logger import log_debug
from src.research_tools.margin_examiner import MarginExaminer

def convert_currency_to_float(value):
    """Convert currency string to float value."""
    if pd.isna(value) or value == '':
        return 0.0
    try:
        return float(str(value).replace('$', '').replace(',', ''))
    except (ValueError, AttributeError):
        return 0.0

def convert_percentage_to_float(value):
    """Convert percentage string to float value."""
    if pd.isna(value) or value == '':
        return 0.0
    try:
        return float(str(value).replace('%', '')) / 100
    except (ValueError, AttributeError):
        return 0.0

def show_research_sidebar(ticker=None):
    """Show research sidebar with ticker information."""
    with st.sidebar:
        #st.header("Research Panel")
        
        #st.divider()
        
        # Show ticker input, populated with selected ticker if provided
        st.markdown("<div style='text-align: center; font-size:24px;'>🌍 Market Research 🌍</div>", unsafe_allow_html=True)
        input_ticker = st.text_input(
            "Enter Ticker:",
            value=ticker if ticker else "",
            key="research_ticker"
        )
        
        if input_ticker:
        
            # Get event details from API
            scraper = KalshiScraper()
            try:
                event_data = scraper.get_event_details(input_ticker)
                if not event_data:
                    st.error("No data found for this ticker")
                    return
                
                event_data = event_data.get('event', {})
                if not event_data:
                    st.error("No event data found")
                    return
                
                # Display event information
                st.title(event_data['title'])
                st.caption(f"Ticker: {event_data['event_ticker']}")
                
                # Event Details
                st.markdown("### 📊 Market Overview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Category", event_data['category'])
                with col2:
                    st.metric("Series", event_data['series_ticker'])
                
                # Market Data
                if event_data.get('markets'):
                    st.markdown("### 💹 Market Data")
                    for market in event_data['markets']:
                        with st.expander(f"Market: {market['ticker']}", expanded=True):
                            # Market type and status
                            st.caption(f"Type: {market['market_type']} | Status: {market['status']}")
                            
                            # Market Rules section without expanders
                            st.markdown("#### 📜 Market Rules")
                            st.markdown("**Primary Rules:**")
                            st.write(market.get('rules_primary', 'No rules available'))
                            st.markdown("**Secondary Rules:**")
                            st.write(market.get('rules_secondary', 'No secondary rules available'))
                            
                            # Current prices
                            price_col1, price_col2 = st.columns(2)
                            with price_col1:
                                st.metric("Yes Bid", f"${market['yes_bid']/100:.2f}")
                                st.metric("Yes Ask", f"${market['yes_ask']/100:.2f}")
                            with price_col2:
                                st.metric("No Bid", f"${market['no_bid']/100:.2f}")
                                st.metric("No Ask", f"${market['no_ask']/100:.2f}")
                            
                            # Volume and liquidity
                            vol_col1, vol_col2 = st.columns(2)
                            with vol_col1:
                                st.metric("Volume", f"{market['volume']:,}")
                                st.metric("24h Volume", f"{market['volume_24h']:,}")
                            with vol_col2:
                                st.metric("Open Interest", f"{market['open_interest']:,}")
                                st.metric("Liquidity", f"${market['liquidity']/100:,.2f}")
                            
                            # Market details
                            st.markdown("#### Market Details")
                            st.write(f"- Notional Value: ${market['notional_value']/100:.2f}")
                            st.write(f"- Risk Limit: ${market['risk_limit_cents']/100:.2f}")
                            st.write(f"- Settlement Timer: {market['settlement_timer_seconds']}s")
                            
                            # Timestamps
                            st.markdown("#### Important Dates")
                            st.write(f"- Open: {market['open_time']}")
                            st.write(f"- Close: {market['close_time']}")
                            st.write(f"- Expiration: {market['expiration_time']}")
                
            except Exception as e:
                st.error(f"Error fetching event details: {str(e)}")
        # else:
        #     st.markdown("<div style='text-align: center; font-size:12px;'>Enter a ticker to begin research</div>", unsafe_allow_html=True)

def initialize_selection_state():
    """Initialize selection-related session state variables."""
    if 'selected_events' not in st.session_state:
        st.session_state.selected_events = []

def initialize_cursor_state():
    """Initialize cursor-related session state variables."""
    if 'cursor_history' not in st.session_state:
        st.session_state.cursor_history = []  # List of previous cursors
    if 'current_cursor_index' not in st.session_state:
        st.session_state.current_cursor_index = -1  # Current position in cursor history

def handle_cursor_navigation(direction, current_cursor):
    """Handle cursor navigation and update session state."""
    if direction == 'next' and current_cursor:
        # Add new cursor to history if going forward
        if st.session_state.current_cursor_index == len(st.session_state.cursor_history) - 1:
            st.session_state.cursor_history.append(current_cursor)
        st.session_state.current_cursor_index += 1
    elif direction == 'back' and st.session_state.current_cursor_index > 0:
        # Move back in history
        st.session_state.current_cursor_index -= 1
    
    # Update the cursor in API parameters
    if st.session_state.current_cursor_index >= 0:
        return st.session_state.cursor_history[st.session_state.current_cursor_index]
    return None

def render_events_tab():
    """Render the Events tab content."""
    # Initialize states
    initialize_selection_state()
    initialize_cursor_state()
    
    # Initialize show_research and clear_filters in session state if not present
    if 'show_research' not in st.session_state:
        st.session_state.show_research = False
    if 'clear_filters_clicked' not in st.session_state:
        st.session_state.clear_filters_clicked = False

    # Function to handle clear filters click
    def handle_clear_filters():
        st.session_state.clear_filters_clicked = True

    # Add Research button in the header area
    col1, col2 = st.columns([6, 1])
    with col1:
        st.header("Events")
    #with col2:
    
    # Show research sidebar if enabled
    if st.session_state.show_research:
        show_research_sidebar()
    
    # Get API parameters
    api_params = render_api_parameters()
    
    # Override the cursor from API parameters with the one from navigation if available
    current_cursor = None
    if st.session_state.current_cursor_index >= 0:
        current_cursor = st.session_state.cursor_history[st.session_state.current_cursor_index]
    
    # Initialize scraper
    scraper = KalshiScraper()
    
    # Fetch events with selected parameters, using the navigation cursor if available
    events_df = scraper.get_events(
        limit=api_params['limit'],
        status=api_params['status'],
        series_ticker=api_params['series_ticker'],
        with_nested_markets=api_params['with_nested_markets'],
        cursor=current_cursor or api_params['cursor']  # Use navigation cursor if available, otherwise use API params cursor
    )
    
    if not events_df.empty:
        # Convert volume and market_value directly to floats
        events_df['market_value'] = events_df['market_value'].apply(convert_currency_to_float)
        events_df['volume'] = events_df['volume'].apply(convert_currency_to_float)
        
        # Calculate total markets before filtering
        total_markets = events_df['market_count'].sum() if 'market_count' in events_df.columns else 0
        
        # Move filters into a collapsible section
        with st.expander("🔍 Filter Events", expanded=False):
            # Check if clear filters was clicked and reset the session state
            if st.session_state.clear_filters_clicked:
                st.session_state.clear_filters_clicked = False
                # Don't try to modify the widget states directly
                search_events = ""
                selected_category = "All"
            else:
                # Get the current filter values from session state or use defaults
                search_events = st.session_state.get('search_filter', '')
                selected_category = st.session_state.get('category_filter', 'All')

            categories = ['All'] + sorted(events_df['category'].unique().tolist())
            f_col1, f_col2 = st.columns([3, 3])
            
            # Category filter
            with f_col1:
                selected_category = st.selectbox(
                    "Select Category:", 
                    categories,
                    key="category_filter",
                    index=categories.index(selected_category)
                )
                
            # Search filter
            with f_col2:
                search_events = st.text_input(
                    "Search events by title or ticker:",
                    value=search_events,
                    key="search_filter"
                )

            if st.button("Clear Filters", type="secondary", key="clear_filters", on_click=handle_clear_filters, use_container_width=True):
                st.rerun()
            
          
        # Apply filters
        filtered_df = events_df.copy()
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]

        if search_events:
            filtered_df = filtered_df[
                filtered_df['title'].str.contains(search_events, case=False) |
                filtered_df['event_ticker'].str.contains(search_events, case=False)
            ]

        # Calculate metrics based on filtered DataFrame
        total_markets_filtered = filtered_df['market_count'].sum() if 'market_count' in filtered_df.columns else 0
        
        # Update metrics to show filtered counts
        col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
        with col1:
            st.metric(
                "Total Events", 
                f"{len(filtered_df)} / {len(events_df)}",
                help="Filtered events / Total events"
            )
        with col2:
            st.metric(
                "Total Markets", 
                f"{int(total_markets_filtered)} / {int(total_markets)}",
                help="Filtered markets / Total markets"
            )
        with col3:
            st.metric(
                "Categories", 
                f"{filtered_df['category'].nunique()} / {events_df['category'].nunique()}",
                help="Filtered categories / Total categories"
            )
        with col4:
            st.write("")
            if st.button("🔍 Research", type="secondary"):
                st.session_state.show_research = True
                st.rerun()
        #     if 'cursor' in events_df.attrs:
        #         st.text(f"Next Cursor: {events_df.attrs['cursor']}")
        #     if 'last_cursor' in events_df.attrs:
        #         st.text(f"Last Cursor: {events_df.attrs['last_cursor']}")

        # Continue with the rest of the code, but use filtered_df instead of events_df
        filtered_df = filtered_df.copy()
        filtered_df.set_index('event_ticker', inplace=True)
        
        # Add ticker column back (it was previously the index)
        filtered_df['ticker'] = filtered_df.index
        
        # Prepare the dataframe for AgGrid
        display_df = filtered_df.copy()
        
        # Configure grid options
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_selection(
            selection_mode='multiple',
            use_checkbox=True,
            pre_selected_rows=[
                i for i, ticker in enumerate(display_df.index)
                if ticker in st.session_state.selected_events
            ]
        )
        
        # Configure specific columns
        gb.configure_column(
            "checkbox",
            headerName="",
            pinned="left",
            checkboxSelection=True,  # Only this column should have checkboxSelection
            headerCheckboxSelection=True,
            headerCheckboxSelectionFilteredOnly=True,
            width=50,
            minWidth=50,
            maxWidth=50
        )
        
        # Configure title column explicitly without checkbox
        gb.configure_column(
            "title",
            headerName="Title",
            width=300,
            checkboxSelection=False  # Explicitly disable checkbox for title
        )
        
        gb.configure_default_column(
            min_column_width=100,
            resizable=True,
            sorteable=True
        )
        
        # Configure ticker column (now without checkbox)
        gb.configure_column(
            "ticker",
            headerName="Ticker",
            #pinned="left",
            width='auto'
        )
        
        # Configure other specific columns
        gb.configure_column(
            "title",
            headerName="Title",
            width='auto'
        )
        
        grid_options = gb.build()

        # Add checkbox column to display_df
        display_df['checkbox'] = ''

        # Display the AgGrid
        grid_response = AgGrid(
            display_df,
            gridOptions=grid_options,
            update_mode='MODEL_CHANGED',
            fit_columns_on_grid_load=True,
            height=500,
            allow_unsafe_jscode=True,
            key='event_grid',
            reload_data=False
        )

        
        # Add pagination controls at the bottom
        pagination_col1, pagination_col2, pagination_col3 = st.columns([1, 3, 1])
        
        with pagination_col1:
            # Back button - disabled if we're at the start (no previous cursors)
            back_disabled = st.session_state.current_cursor_index < 0
            if st.button("← Back", 
                        disabled=back_disabled,
                        use_container_width=True):
                current_cursor = handle_cursor_navigation('back', None)
                st.rerun()
        
        with pagination_col2:
            # Show current page number
            if 'last_cursor' in events_df.attrs:
                # If we have a last_cursor, we can show total pages
                total_pages = events_df.attrs['last_cursor']
                current_page = st.session_state.current_cursor_index + 1
                st.markdown(f"<div style='text-align: center'>Page {current_page} of {total_pages}</div>", 
                          unsafe_allow_html=True)
            else:
                # If no last_cursor, just show current page
                current_page = st.session_state.current_cursor_index + 1
                st.markdown(f"<div style='text-align: center'>Page {current_page}</div>", 
                          unsafe_allow_html=True)
        
        with pagination_col3:
            # Next button - disabled if we're at the last page or no next cursor
            has_next_cursor = 'cursor' in events_df.attrs and events_df.attrs.get('cursor')
            has_more_pages = True
            if 'last_cursor' in events_df.attrs:
                current_page = st.session_state.current_cursor_index + 1
                has_more_pages = current_page < int(events_df.attrs['last_cursor'])
            
            next_disabled = not has_next_cursor or not has_more_pages
            if st.button("Next →", 
                        disabled=next_disabled,
                        use_container_width=True):
                current_cursor = handle_cursor_navigation('next', events_df.attrs.get('cursor'))
                st.rerun()
                
        # Update selected events in session state
        if grid_response is not None and grid_response.get('selected_rows') is not None and len(grid_response['selected_rows']) > 0:
            # st.session_state.selected_events = [
            #     row['ticker'] for row in grid_response['selected_rows']
            # ]
            st.session_state.selected_events = [row[1].ticker for row in grid_response['selected_rows'].iterrows()]
        else:
            st.session_state.selected_events = []  # Clear selection if nothing is selected
        # Show selection status
        num_selected = len(st.session_state.selected_events)
                
        # Add the "Initiate Margins Examination" button
        examine_button = st.button(
            label="Initiate Margins Examination", 
            type="primary",
            use_container_width=True,
            disabled=(num_selected == 0),
            key='examine_button'
        )

        #if num_selected > 0:
        st.caption(f"Selected {num_selected} events: {', '.join(st.session_state.selected_events)}")
        if examine_button and num_selected > 0:
            try:
                examiner = MarginExaminer() 
                
                with st.spinner('Analyzing selected markets...'):
                    # Run the analysis
                    results = asyncio.run(examiner.examine_events(st.session_state.selected_events))
                    
                    # Display results
                    st.success("Analysis complete!")
                    log_debug(results)
                    for event_ticker, analyses in results.items():
                        with st.expander(f"Analysis for {event_ticker}"):
                            for analysis in analyses:
                                st.markdown(f"### Market: {analysis.market_ticker}")
                                st.markdown(f"**Current YES Ask:** ${analysis.current_yes_ask:.2f}")
                                st.markdown(f"**Estimated Probability:** {analysis.estimated_probability:.1%}")
                                st.markdown(f"**Confidence Score:** {analysis.confidence_score:.1%}")
                                st.markdown("**Reasoning:**")
                                st.write(analysis.reasoning)
                                st.markdown("**Sources:**")
                                for source in analysis.sources:
                                    st.write(f"- {source}")
                                st.markdown(f"**Recommendation:** {analysis.recommendation}")
                                st.divider()
                    
            except Exception as e:
                st.error(f"Error during margin examination: {str(e)}")

                
    else:
        st.error("No events found or error occurred.") 
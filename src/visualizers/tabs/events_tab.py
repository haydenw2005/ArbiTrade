import streamlit as st
import pandas as pd
from typing import List, Dict
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.grid_options_builder import GridOptionsBuilder
import asyncio

from src.visualizers.components.api_parameters import render_api_parameters
from src.data_collectors.kalshi_scraper import KalshiScraper
from src.utils.logger import log_debug
from src.research_tools.margin_examiner import MarginExaminer
from src.research_tools.margin_schemas import MarginAnalysis

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
        events_df['liquidity'] = events_df['liquidity'].apply(convert_currency_to_float)
        
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
            type="secondary",
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
                    
                    # First show the summary grid
                    st.markdown("### 📊 Analysis Summary")
                    st.markdown("Click on the 'View' buttons to see detailed information.")
                    summary_grid = create_analysis_summary_grid(results)
                    if summary_grid is None:
                        st.warning("No analysis results to display in summary.")
                    
                    # Then show the detailed analyses using tabs instead of expanders
                    st.markdown("### 📑 Detailed Analysis")
                    
                    # Create tabs for each event
                    if results:
                        event_tabs = st.tabs(list(results.keys()))
                        
                        # Display analyses for each event in its tab
                        for event_tab, (event_ticker, analyses) in zip(event_tabs, results.items()):
                            with event_tab:
                                # Create columns for analyses to show them side by side
                                if analyses:
                                    cols = st.columns(min(2, len(analyses)))  # Show max 2 analyses per row
                                    for i, analysis in enumerate(analyses):
                                        col_idx = i % 2  # Alternate between columns
                                        with cols[col_idx]:
                              
                                            
                                            # Market info
                                            st.markdown(f"#### Market: {analysis.market_ticker}")
                                            st.markdown(f"**Current YES Ask:** ${analysis.current_yes_ask:.2f}")
                                            st.markdown(f"**Estimated Probability:** {analysis.estimated_probability:.1%}")
                                            st.markdown(f"**Confidence Score:** {analysis.confidence_score:.1%}")
                                            
                                            # Research context in a container
                                            with st.container():
                                                st.markdown("##### 📰 Research Context")
                                                st.markdown(f"**Market Sentiment:** {analysis.research_context.market_sentiment:+.2f}")
                                                
                                                # Collapsible sections using st.expander
                                                with st.expander("📝 Research Summary"):
                                                    st.write(analysis.research_context.summary)
                                                
                                                with st.expander("🔑 Key Points"):
                                                    for point in analysis.research_context.key_points:
                                                        st.write(f"• {point}")
                                                
                                                with st.expander("📚 News Sources"):
                                                    for article in analysis.research_context.articles:
                                                        st.markdown(f"**[{article.title}]({article.url})**")
                                                        st.caption(f"Source: {article.source_name} | Published: {article.published_at}")
                                                        if article.description:
                                                            st.write(article.description)
                                                        st.markdown("---")
                                        
                                                # Analysis and recommendation
                                                with st.container():
                                                    with st.expander("🎯 View Reasoning"):
                                                        st.write(analysis.reasoning)
                                                        st.markdown("**Sources:**")
                                                        for source in analysis.sources:
                                                            st.write(f"• {source}")
                                        
                                                st.markdown(f"**Recommendation:** {analysis.recommendation}")
                                    
                                    st.markdown('</div>', unsafe_allow_html=True)
                                    
                                    # Start new row after every 2 analyses
                                    if col_idx == 1:
                                        st.markdown("---")
                                else:
                                    st.info("No analyses available for this event.")
                                    
            except Exception as e:
                st.error(f"Error during margin examination: {str(e)}")

                
    else:
        st.error("No events found or error occurred.") 

def create_analysis_summary_grid(results: Dict[str, List[MarginAnalysis]]):
    """Create a summary grid of all analysis results"""
    # Flatten the results into a list of dictionaries for the grid
    summary_data = []
    for event_ticker, analyses in results.items():
        for analysis in analyses:
            summary_data.append({
                'Event Ticker': event_ticker,
                'Market Ticker': analysis.market_ticker,
                'Current YES Ask': f"${analysis.current_yes_ask:.2f}",
                'Estimated Prob': f"{analysis.estimated_probability:.1%}",
                'Confidence': f"{analysis.confidence_score:.1%}",
                'Sentiment': f"{analysis.research_context.market_sentiment:+.2f}",
                'Recommendation': analysis.recommendation,
                'Reasoning': analysis.reasoning,  # Will be shown in popup
                'Research Summary': analysis.research_context.summary,  # Will be shown in popup
                'Key Points': '\n• ' + '\n• '.join(analysis.research_context.key_points),  # Will be shown in popup
                'News Count': len(analysis.research_context.articles)
            })
    
    if not summary_data:
        return None
        
    df = pd.DataFrame(summary_data)
    
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Configure columns
    gb.configure_column('Event Ticker', pinned='left', width=120)
    gb.configure_column('Market Ticker', width=120)
    gb.configure_column('Current YES Ask', width=120)
    gb.configure_column('Estimated Prob', width=120)
    gb.configure_column('Confidence', width=120)
    gb.configure_column('Sentiment', width=100)
    gb.configure_column('Recommendation', width=140)
    
    # Configure popup/expandable columns
    gb.configure_column(
        'Reasoning',
        width=120,
        cellRenderer="""
        function(params) {
            return params.value ? 
                '<div class="expand-trigger" title="Click to view full text">📝 View Analysis</div>' : 
                '';
        }
        """,
        cellStyle={'cursor': 'pointer'},
        onCellClicked="""
        function(params) {
            const text = params.value;
            if (text) {
                const modal = document.createElement('div');
                modal.style = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;max-width:80%;max-height:80%;overflow:auto;z-index:1000;border-radius:8px;box-shadow:0 0 15px rgba(0,0,0,0.2);';
                modal.innerHTML = `<h3>Detailed Analysis</h3><p style="white-space:pre-wrap;">${text}</p><button onclick="this.parentElement.remove()" style="position:absolute;top:10px;right:10px;border:none;background:none;font-size:20px;cursor:pointer;">×</button>`;
                document.body.appendChild(modal);
            }
        }
        """
    )
    
    gb.configure_column(
        'Research Summary',
        width=120,
        cellRenderer="""
        function(params) {
            return params.value ? 
                '<div class="expand-trigger" title="Click to view research summary">📚 View Research</div>' : 
                '';
        }
        """,
        cellStyle={'cursor': 'pointer'},
        onCellClicked="""
        function(params) {
            const text = params.value;
            if (text) {
                const modal = document.createElement('div');
                modal.style = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;max-width:80%;max-height:80%;overflow:auto;z-index:1000;border-radius:8px;box-shadow:0 0 15px rgba(0,0,0,0.2);';
                modal.innerHTML = `<h3>Research Summary</h3><p style="white-space:pre-wrap;">${text}</p><button onclick="this.parentElement.remove()" style="position:absolute;top:10px;right:10px;border:none;background:none;font-size:20px;cursor:pointer;">×</button>`;
                document.body.appendChild(modal);
            }
        }
        """
    )
    
    gb.configure_column(
        'Key Points',
        width=120,
        cellRenderer="""
        function(params) {
            return params.value ? 
                '<div class="expand-trigger" title="Click to view key points">🔑 View Points</div>' : 
                '';
        }
        """,
        cellStyle={'cursor': 'pointer'},
        onCellClicked="""
        function(params) {
            const text = params.value;
            if (text) {
                const modal = document.createElement('div');
                modal.style = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;max-width:80%;max-height:80%;overflow:auto;z-index:1000;border-radius:8px;box-shadow:0 0 15px rgba(0,0,0,0.2);';
                modal.innerHTML = `<h3>Key Points</h3><p style="white-space:pre-wrap;">${text}</p><button onclick="this.parentElement.remove()" style="position:absolute;top:10px;right:10px;border:none;background:none;font-size:20px;cursor:pointer;">×</button>`;
                document.body.appendChild(modal);
            }
        }
        """
    )
    
    gb.configure_column('News Count', width=100)
    
    # Enable sorting and filtering
    gb.configure_default_column(
        sorteable=True,
        filterable=True,
        resizable=True
    )
    
    grid_options = gb.build()
    
    return AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        custom_css={
            ".expand-trigger:hover": {
                "text-decoration": "underline",
                "color": "#1f77b4"
            }
        },
        height=500,
        theme='streamlit'
    )
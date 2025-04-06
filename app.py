import streamlit as st
import os
import json
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

from log_parser import parse_log_to_json
from visualization import (
    create_grid_visualization, 
    display_event_details,
    display_metrics
)
from utils import (
    get_log_files,
    extract_bot_id_from_filename,
    get_min_max_coordinates,
    get_unique_bot_ids,
    get_events_by_bot_id,
    save_uploaded_file
)

# Page configuration
st.set_page_config(
    page_title="Warehouse Robot Path Visualization",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# App title and description
st.title("Warehouse Robot Path Visualization")
st.markdown(
    """
    This application visualizes the path planning and navigation of warehouse robots.
    Upload a log file or select a sample file to begin exploring robot path planning data.
    """
)

# Sidebar for file selection and controls
st.sidebar.header("Data Selection")

# File upload option
uploaded_file = st.sidebar.file_uploader("Upload a robot path log file", type=['log'])

# sample log file if file not uploaded
st.sidebar.markdown("---")
st.sidebar.subheader("Or use sample data:")

sample_data_path = "log_files"
sample_files = []

if os.path.exists(sample_data_path):
    sample_files = [f for f in os.listdir(sample_data_path) if f.endswith('.log')]

selected_sample = st.sidebar.selectbox(
    "Select a sample log file:",
    [""] + sample_files,
    index=0
)

# Initializing session state for animation control
if 'play_animation' not in st.session_state:
    st.session_state.play_animation = False
if 'current_step' not in st.session_state:
    st.session_state.current_step = 0
if 'parsed_events' not in st.session_state:
    st.session_state.parsed_events = []
if 'bot_id_filter' not in st.session_state:
    st.session_state.bot_id_filter = None
if 'path_filter' not in st.session_state:
    st.session_state.path_filter = None
if 'speed' not in st.session_state:
    st.session_state.speed = 1.0                     
  
log_file_path = None

if uploaded_file:
    log_file_path = save_uploaded_file(uploaded_file)
    st.sidebar.success(f"File uploaded: {uploaded_file.name}")
elif selected_sample:
    log_file_path = os.path.join(sample_data_path, selected_sample)
    st.sidebar.success(f"Using sample file: {selected_sample}")

if log_file_path:
    # Extracting bot_id from filename 
    bot_id = extract_bot_id_from_filename(os.path.basename(log_file_path))
    
    if not st.session_state.parsed_events or st.session_state.get('last_file') != log_file_path:
        with st.spinner("Parsing log file..."):
            parsed_events = parse_log_to_json(log_file_path)
            st.session_state.parsed_events = parsed_events
            st.session_state.last_file = log_file_path
            st.session_state.current_step = 0
            st.session_state.play_animation = False
    
    bot_ids = get_unique_bot_ids(st.session_state.parsed_events)
    
    # Bot ID filter in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filter Options")
    
    selected_bot = st.sidebar.selectbox(
        "Select Bot ID:",
        ["All"] + bot_ids,
        index=0 if "All" not in bot_ids else bot_ids.index(bot_id) + 1 if bot_id in bot_ids else 0
    )
    
    # bot ID filter
    filtered_events = st.session_state.parsed_events
    if selected_bot != "All":
        filtered_events = get_events_by_bot_id(filtered_events, selected_bot)
        st.session_state.bot_id_filter = selected_bot
    else:
        st.session_state.bot_id_filter = None
        
    # Path selection dropdown
    path_events = get_path_calculation_events(filtered_events)  
    
    if path_events:
        path_options = ["All Paths"] + [path['label'] for path in path_events]      
        selected_path = st.sidebar.selectbox(
            "Select Path to Visualize:",
            path_options,
            index=0
        )
        # Filtering events by selected path
        if selected_path != "All Paths":
            # Find the selected path event
            selected_path_event = next((p for p in path_events if p['label'] == selected_path), None)           

            if selected_path_event:
                # Filter events to show only those between start and end of the selected path
                filtered_events = filter_events_by_path(
                    filtered_events, 
                    selected_path_event['start_idx'], 
                    selected_path_event['end_idx']
                )
                st.session_state.path_filter = selected_path
                
                # Reset current step when path changes
                if st.session_state.get('last_path') != selected_path:
                    st.session_state.current_step = 0
                    st.session_state.last_path = selected_path
        else:
            st.session_state.path_filter = None
    
    # Animation controls in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Animation Controls")
    
    max_step = len(filtered_events) - 1
    if max_step >= 0:
        st.session_state.current_step = min(st.session_state.current_step, max_step)
    
    # Step slider
    step_slider = st.sidebar.slider(
        "Step",
        0, max(max_step, 0),
        min(st.session_state.current_step, max(max_step, 0)),
        key="step_slider"
    )
    
    # Updating current step if slider changed
    if step_slider != st.session_state.current_step:
        st.session_state.current_step = step_slider
        st.session_state.play_animation = False  # Stop animation when manually changing step

    # Jump to event ID
    st.sidebar.markdown("---")
    jump_col1, jump_col2 = st.sidebar.columns([3, 1])
    with jump_col1:
        event_id_input = st.number_input("Jump to Event ID", min_value=1, max_value=max(max_step+1, 1), step=1, value=1)
    with jump_col2:
        if st.button("Jump"):
            # Find the index of the event with the specified event_id
            for i, event in enumerate(filtered_events):
                if event.get('event_id') == event_id_input:
                    st.session_state.current_step = i
                    st.session_state.play_animation = False  # Stop animation when jumping
                    break
    
    # Play/Pause button
    play_text = "⏸️ Pause" if st.session_state.play_animation else "▶️ Play"
    if st.sidebar.button(play_text):
        st.session_state.play_animation = not st.session_state.play_animation
    
    # Step buttons
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("⏮️ First"):
            st.session_state.current_step = 0
            st.session_state.play_animation = False
    
    with col2:
        if st.button("⏪ Previous"):
            st.session_state.current_step = max(0, st.session_state.current_step - 1)
            st.session_state.play_animation = False
    
    with col3:
        if st.button("⏩ Next"):
            st.session_state.current_step = min(max_step, st.session_state.current_step + 1)
            st.session_state.play_animation = False
    
    # Speed control
    st.session_state.speed = st.sidebar.slider(
        "Animation Speed",
        min_value=0.1,
        max_value=5.0,
        value=st.session_state.speed,
        step=0.1
    )
    
    # Displaying filter information
    filter_info = []
    if st.session_state.bot_id_filter:
        filter_info.append(f"Bot ID: {st.session_state.bot_id_filter}")
    if st.session_state.path_filter:
        filter_info.append(f"Path: {st.session_state.path_filter}")
    if filter_info:
        st.info(f"Filtered to show: {' | '.join(filter_info)}")                    
  
    # grid boundaries
    min_x, min_y, max_x, max_y = get_min_max_coordinates(filtered_events)
    
    # grid visualization and event details
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if filtered_events:
            grid_fig = create_grid_visualization(
                filtered_events, 
                st.session_state.current_step,
                min_x, min_y, max_x, max_y
            )
            st.plotly_chart(grid_fig, use_container_width=True)
        else:
            st.warning("No events to visualize. Try selecting a different file or bot ID.")
    
    with col2:
        if 0 <= st.session_state.current_step < len(filtered_events):
            current_event = filtered_events[st.session_state.current_step]
            display_event_details(current_event)
        else:
            st.warning("No event data available for the current step.")
    
    # Metrics and statistics
    st.markdown("---")
    st.subheader("Path Planning Metrics")
    display_metrics(filtered_events)
    
    # Event table 
    st.markdown("---")
    with st.expander("View Event Data Table"):
        if filtered_events:
            # Convert to DataFrame for display
            df = pd.DataFrame(filtered_events)
            
            # Format coordinate columns for better readability
            if 'coordinate' in df.columns:
                df['coordinate'] = df['coordinate'].apply(
                    lambda x: f"({x.get('x')}, {x.get('y')})" if isinstance(x, dict) and 'x' in x and 'y' in x else None
                )
            
            if 'from_coordinate' in df.columns:
                df['from_coordinate'] = df['from_coordinate'].apply(
                    lambda x: f"({x.get('x')}, {x.get('y')})" if isinstance(x, dict) and 'x' in x and 'y' in x else None
                )
            
            # Drop unnecesary columns for display
            cols_to_drop = [col for col in df.columns if isinstance(df[col].iloc[0] if not df.empty else None, (dict, list))]
            display_df = df.drop(columns=cols_to_drop, errors='ignore')
            
            st.dataframe(display_df)
            
            # Download button for CSV
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"robot_path_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No event data available.")
    
    # JSON preview 
    st.markdown("---")
    with st.expander("View JSON Data Preview"):
        if filtered_events:
            preview_limit = min(5, len(filtered_events))
            preview_events = filtered_events[:preview_limit]
            
            if len(filtered_events) > preview_limit:
                preview_note = f"\n\n// Showing first {preview_limit} of {len(filtered_events)} events"
                preview_json = json.dumps(preview_events, indent=2) + preview_note
            else:
                preview_json = json.dumps(preview_events, indent=2)
            
            st.code(preview_json, language="json")
            
            # Download button for full JSON
            full_json_str = json.dumps(filtered_events, indent=2)
            st.download_button(
                label="Download Full JSON",
                data=full_json_str,
                file_name=f"robot_path_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.warning("No JSON data available.")
    
    # Auto-advance animation if playing
    if st.session_state.play_animation and st.session_state.current_step < max_step:
        time.sleep(0.2 / st.session_state.speed)  # Adjust speed based on slider
        st.session_state.current_step += 1
        st.rerun()

else:
    # No file selected yet
    st.info("Please upload a log file or select a sample file to begin.")

# Footer
st.markdown("---")
st.caption("Warehouse Robot Path Visualization Tool")

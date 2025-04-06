import os
import json
import pandas as pd
import streamlit as st
import tempfile

def get_log_files(directory="."):
    """Get list of log files in the directory."""
    log_files = []
    for file in os.listdir(directory):
        if file.endswith(".log"):
            log_files.append(file)
    return log_files

def extract_bot_id_from_filename(filename):
    """Extract bot ID from a log filename."""
    import re
    match = re.search(r'bot_(\d+)\.log', filename)
    if match:
        return match.group(1)
    return None

def events_to_dataframe(events):
    """Convert parsed events to a pandas DataFrame."""
    return pd.DataFrame(events)

def get_min_max_coordinates(events):
    """Get the minimum and maximum x,y coordinates from events."""
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for event in events:
        if 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
        
        if 'from_coordinate' in event:
            x, y = event['from_coordinate'].get('x'), event['from_coordinate'].get('y')
            if x is not None and y is not None:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                
        if 'src' in event and 'coordinate' in event['src']:
            x, y = event['src']['coordinate'].get('x'), event['src']['coordinate'].get('y')
            if x is not None and y is not None:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                
        if 'dest' in event and 'coordinate' in event['dest']:
            x, y = event['dest']['coordinate'].get('x'), event['dest']['coordinate'].get('y')
            if x is not None and y is not None:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    
    # small buffer around the coordinates for safety
    buffer = 5
    return (
        max(0, min_x - buffer),
        max(0, min_y - buffer),
        max_x + buffer,
        max_y + buffer
    )

def get_unique_bot_ids(events):
    """Get a list of unique bot IDs from events."""
    bot_ids = set()
    for event in events:
        if 'bot_id' in event and event['bot_id']:
            bot_ids.add(event['bot_id'])
    return sorted(list(bot_ids))

def get_events_by_bot_id(events, bot_id):
    """Filter events by bot ID."""
    return [event for event in events if event.get('bot_id') == bot_id]

def get_path_calculation_events(events):
    """Get all path calculation start events with their source and destination."""
    path_events = []
    for i, event in enumerate(events):
        if event.get('event') == 'path_calculation_started':
            # Find the corresponding end event if it exists
            end_idx = None
            for j in range(i+1, len(events)):
                if events[j].get('event') == 'path_calculation_ended' and events[j].get('bot_id') == event.get('bot_id'):
                    end_idx = j
                    break
            
            # Create a descriptive label for the dropdown
            src_coord = event.get('src', {}).get('coordinate', {})
            dest_coord = event.get('dest', {}).get('coordinate', {})
            src_str = f"({src_coord.get('x')},{src_coord.get('y')})" if src_coord else "(?,?)"
            dest_str = f"({dest_coord.get('x')},{dest_coord.get('y')})" if dest_coord else "(?,?)"
            
            path_events.append({
                'event_id': event.get('event_id'),
                'bot_id': event.get('bot_id'),
                'start_idx': i,
                'end_idx': end_idx,
                'src': src_str,
                'dest': dest_str,
                'label': f"Path {event.get('event_id')}: {src_str} → {dest_str}"
            })
    
    return path_events

def filter_events_by_path(events, start_idx, end_idx):
    """Filter events to show only those between start_idx and end_idx."""
    if end_idx is None:
        # If no end event found, include all events after start_idx
        return events[start_idx:]
    else:
        # Include events between start and end (inclusive)
        return events[start_idx:end_idx+1]

def calculate_path_metrics(events):
    """Calculate metrics about the path planning process."""
    if not events:
        return {}
    
    # Counting event types
    event_counts = {}
    for event in events:
        event_type = event.get('event')
        if event_type:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    # Calculate time taken (if timestamps available)
    start_time = None
    end_time = None
    for event in events:
        if 'timestamp' in event:
            timestamp = event['timestamp']
            if start_time is None or timestamp < start_time:
                start_time = timestamp
            if end_time is None or timestamp > end_time:
                end_time = timestamp
    
    time_taken = None
    if start_time and end_time:
        from datetime import datetime
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
        end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S.%f')
        time_taken = (end_dt - start_dt).total_seconds()
    
    path_coords = []
    conflicts = 0
    
    for event in events:
        if event.get('event') == 'chosen_node':
            if 'coordinate' in event:
                coord = event['coordinate']
                path_coords.append((coord.get('x'), coord.get('y')))
        
        if event.get('event') == 'conflict_check' and event.get('conflict_found'):
            conflicts += 1
    
    # Calculate path distance (Manhattan distance)
    path_distance = 0
    if len(path_coords) > 1:
        for i in range(1, len(path_coords)):
            x1, y1 = path_coords[i-1]
            x2, y2 = path_coords[i]
            path_distance += abs(x2 - x1) + abs(y2 - y1)
    
    return {
        'events_total': len(events),
        'event_counts': event_counts,
        'time_taken': time_taken,
        'path_length': len(path_coords),
        'path_distance': path_distance,
        'conflicts_detected': conflicts
    }

def save_uploaded_file(uploaded_file):
    """Save an uploaded file to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

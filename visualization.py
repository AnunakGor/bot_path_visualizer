import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

def create_grid_visualization(events, current_step_idx, min_x, min_y, max_x, max_y):
    current_events = events[:current_step_idx+1] if current_step_idx < len(events) else events
    
    chosen_nodes = []
    exploring_nodes = []
    processing_nodes = []
    conflict_nodes = []
    pause_nodes = []
    cannot_revisit_nodes = []
    
    src_coord = None
    dest_coord = None
    
    for event in current_events:
        event_type = event.get('event')
        
        if event_type == 'path_calculation_started':
            if 'src' in event and 'coordinate' in event['src']:
                src_coord = (event['src']['coordinate'].get('x'), event['src']['coordinate'].get('y'))
            if 'dest' in event and 'coordinate' in event['dest']:
                dest_coord = (event['dest']['coordinate'].get('x'), event['dest']['coordinate'].get('y'))
                
        elif event_type == 'chosen_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                chosen_nodes.append((x, y))
                
        elif event_type == 'exploring_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            status = event.get('status')
            if x is not None and y is not None and status == 'accepted':
                exploring_nodes.append((x, y))
                
        elif event_type == 'processing_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                processing_nodes.append((x, y))
                
        elif event_type == 'conflict_check' and 'anchor_coordinate' in event:
            x, y = event['anchor_coordinate'].get('x'), event['anchor_coordinate'].get('y')
            conflict = event.get('conflict_found')
            if x is not None and y is not None and conflict:
                conflict_nodes.append((x, y))
                
        elif event_type == 'pause_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                pause_nodes.append((x, y))
                
        elif event_type == 'cannot_revisit_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                cannot_revisit_nodes.append((x, y))
    
    fig = go.Figure()
    
    grid_width = max_x - min_x + 1
    grid_height = max_y - min_y + 1
    
    for x in range(int(min_x), int(max_x) + 1):
        fig.add_trace(go.Scatter(
            x=[x, x], 
            y=[min_y, max_y],
            mode='lines',
            line=dict(color='lightgray', width=1),
            hoverinfo='none',
            showlegend=False
        ))
    
    for y in range(int(min_y), int(max_y) + 1):
        fig.add_trace(go.Scatter(
            x=[min_x, max_x],
            y=[y, y],
            mode='lines',
            line=dict(color='lightgray', width=1),
            hoverinfo='none',
            showlegend=False
        ))
    
    if exploring_nodes:
        x_vals = [coord[0] for coord in exploring_nodes]
        y_vals = [coord[1] for coord in exploring_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='lightblue', size=12, symbol='square'),
            name='Explored Nodes'
        ))
    
    if processing_nodes:
        x_vals = [coord[0] for coord in processing_nodes]
        y_vals = [coord[1] for coord in processing_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='yellow', size=12, symbol='square'),
            name='Processing Nodes'
        ))
    
    if conflict_nodes:
        x_vals = [coord[0] for coord in conflict_nodes]
        y_vals = [coord[1] for coord in conflict_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='red', size=12, symbol='square'),
            name='Conflict Nodes'
        ))
        
    if pause_nodes:
        x_vals = [coord[0] for coord in pause_nodes]
        y_vals = [coord[1] for coord in pause_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='orange', size=12, symbol='square'),
            name='Pause Nodes'
        ))
        
    if cannot_revisit_nodes:
        x_vals = [coord[0] for coord in cannot_revisit_nodes]
        y_vals = [coord[1] for coord in cannot_revisit_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='magenta', size=12, symbol='square'),
            name='Cannot Revisit Nodes'
        ))
    
    if chosen_nodes:
        x_vals = [coord[0] for coord in chosen_nodes]
        y_vals = [coord[1] for coord in chosen_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            marker=dict(color='green', size=12, symbol='square'),
            line=dict(color='green', width=3),
            name='Chosen Path'
        ))
    
    if src_coord:
        fig.add_trace(go.Scatter(
            x=[src_coord[0]],
            y=[src_coord[1]],
            mode='markers',
            marker=dict(color='blue', size=20, symbol='circle'),
            name='Source'
        ))
    
    if dest_coord:
        fig.add_trace(go.Scatter(
            x=[dest_coord[0]],
            y=[dest_coord[1]],
            mode='markers',
            marker=dict(color='purple', size=20, symbol='circle'),
            name='Destination'
        ))
    
    current_event = events[current_step_idx] if current_step_idx < len(events) else None
    if current_event:
        event_type = current_event.get('event')
        coord = None
        direction = None
        
        if 'coordinate' in current_event:
            coord = (current_event['coordinate'].get('x'), current_event['coordinate'].get('y'))
        
        if 'bot_direction' in current_event:
            direction = current_event['bot_direction']
        elif 'src' in current_event and 'bot_direction' in current_event['src']:
            direction = current_event['src']['bot_direction']
        
        if coord and direction:
            fig.add_trace(go.Scatter(
                x=[coord[0]],
                y=[coord[1]],
                mode='markers',
                marker=dict(color='black', size=15, symbol='diamond'),
                name='Current Position'
            ))
            
            dx, dy = 0, 0
            if direction == 'north':
                dx, dy = 0, 0.5
            elif direction == 'south':
                dx, dy = 0, -0.5
            elif direction == 'east':
                dx, dy = 0.5, 0
            elif direction == 'west':
                dx, dy = -0.5, 0
            
            fig.add_trace(go.Scatter(
                x=[coord[0], coord[0] + dx],
                y=[coord[1], coord[1] + dy],
                mode='lines',
                line=dict(color='black', width=3),
                showlegend=False
            ))
    
    fig.update_layout(
        title='Warehouse Robot Path Planning',
        xaxis=dict(
            title='X Coordinate',
            tickmode='linear',
            tick0=min_x,
            dtick=1,
            range=[min_x - 1, max_x + 1]
        ),
        yaxis=dict(
            title='Y Coordinate',
            tickmode='linear',
            tick0=min_y,
            dtick=1,
            range=[min_y - 1, max_y + 1],
            scaleanchor='x',
            scaleratio=1
        ),
        hovermode='closest',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig

def display_event_details(event):
    if not event:
        return
    
    event_type = event.get('event')
    
    st.subheader(f"Event: {event_type}")
    
    st.write(f"Event ID: {event.get('event_id')}")
    st.write(f"Timestamp: {event.get('timestamp')}")
    st.write(f"Bot ID: {event.get('bot_id')}")
    
    if event_type == 'path_calculation_started':
        if 'src' in event and 'coordinate' in event['src']:
            src_coord = event['src']['coordinate']
            st.write(f"Source: ({src_coord.get('x')}, {src_coord.get('y')})")
            st.write(f"Direction: {event['src'].get('bot_direction')}")
        
        if 'dest' in event and 'coordinate' in event['dest']:
            dest_coord = event['dest']['coordinate']
            st.write(f"Destination: ({dest_coord.get('x')}, {dest_coord.get('y')})")
    
    elif event_type == 'chosen_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        
        if 'GCost' in event and 'HCost' in event and 'FScore' in event:
            st.write(f"G Cost: {event.get('GCost')}")
            st.write(f"H Cost: {event.get('HCost')}")
            st.write(f"F Score: {event.get('FScore')}")
    
    elif event_type == 'neighbour_nodes':
        st.write(f"Neighbors: {event.get('neighbors_raw')}")
    
    elif event_type == 'exploring_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        
        st.write(f"Bot Direction: {event.get('bot_direction')}")
        st.write(f"Physical Direction: {event.get('physical_direction')}")
        st.write(f"Rack Direction: {event.get('rack_direction')}")
        st.write(f"Status: {event.get('status')}")
    
    elif event_type == 'processing_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        
        if 'from_coordinate' in event:
            from_coord = event['from_coordinate']
            st.write(f"From Coordinate: ({from_coord.get('x')}, {from_coord.get('y')})")
    
    elif event_type == 'conflict_check':
        if 'anchor_coordinate' in event:
            anchor_coord = event['anchor_coordinate']
            st.write(f"Anchor Coordinate: ({anchor_coord.get('x')}, {anchor_coord.get('y')})")
        
        st.write(f"Conflict Found: {event.get('conflict_found')}")
        
        if 'span_coords' in event:
            spans = event.get('span_coords')
            span_display = spans[:5]
            if len(spans) > 5:
                span_display.append('...')
            st.write(f"Span Coordinates: {span_display}")
    
    elif event_type == 'added_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        
        if 'from_coordinate' in event:
            from_coord = event['from_coordinate']
            st.write(f"From Coordinate: ({from_coord.get('x')}, {from_coord.get('y')})")
        
        st.write(f"Turn Tag: {event.get('turn_tag')}")
        st.write(f"Moving Status: {event.get('moving_status')}")
        st.write(f"Bot Direction: {event.get('bot_direction')}")
        st.write(f"Physical Direction: {event.get('physical_direction')}")
        st.write(f"Rack Direction: {event.get('rack_direction')}")
        
        if 'GCost' in event and 'HCost' in event and 'FScore' in event:
            st.write(f"G Cost: {event.get('GCost')}")
            st.write(f"H Cost: {event.get('HCost')}")
            st.write(f"F Score: {event.get('FScore')}")
        
        st.write(f"Pause Time: {event.get('pause_time')}")
        
    elif event_type == 'pause_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
            
        st.write(f"Bot Direction: {event.get('bot_direction')}")
        st.write(f"Rack Direction: {event.get('rack_direction')}")
        st.write(f"Pause Time: {event.get('pause_time')}")
        st.write(f"Reason: {event.get('reason')}")
        
    elif event_type == 'cannot_revisit_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
            
        if 'from_coordinate' in event:
            from_coord = event['from_coordinate']
            st.write(f"From Coordinate: ({from_coord.get('x')}, {from_coord.get('y')})")
            
        st.write(f"Turn Tag: {event.get('turn_tag')}")
        st.write(f"Moving Status: {event.get('moving_status')}")
        st.write(f"Bot Direction: {event.get('bot_direction')}")
        st.write(f"Rack Direction: {event.get('rack_direction')}")
        st.write(f"Reason: {event.get('reason')}")

def display_metrics(events):
    metrics = calculate_path_metrics(events)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total Events", value=metrics.get('events_total', 0))
        st.metric(label="Path Length", value=metrics.get('path_length', 0))
    
    with col2:
        time_taken = metrics.get('time_taken')
        if time_taken is not None:
            st.metric(label="Time Taken", value=f"{time_taken:.3f} sec")
        
        st.metric(label="Path Distance", value=metrics.get('path_distance', 0))
    
    with col3:
        st.metric(label="Conflicts Detected", value=metrics.get('conflicts_detected', 0))
        
        event_counts = metrics.get('event_counts', {})
        chosen_count = event_counts.get('chosen_node', 0)
        st.metric(label="Nodes Chosen", value=chosen_count)
    
    event_counts = metrics.get('event_counts', {})
    if event_counts:
        st.subheader("Event Type Breakdown")
        
        event_types = list(event_counts.keys())
        counts = list(event_counts.values())
        
        fig = go.Figure(go.Bar(
            x=counts,
            y=event_types,
            orientation='h'
        ))
        
        fig.update_layout(
            title="Event Counts",
            xaxis_title="Count",
            yaxis_title="Event Type",
            height=300,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)

def calculate_path_metrics(events):
    if not events:
        return {}
    
    event_counts = {}
    for event in events:
        event_type = event.get('event')
        if event_type:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
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

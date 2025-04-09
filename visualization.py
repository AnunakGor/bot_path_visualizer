import streamlit as st                    
  
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

from collections import defaultdict

def track_priority_queue(events, current_step_idx):
    """Track the state of the priority queue up to the current step.
    The priority queue is updated based on added_node and chosen_node events:
    - added_node: A node is added to the priority queue
    - chosen_node: A node is removed from the priority queue (popped)
    Returns a list of nodes currently in the priority queue, sorted by F-score.
    """
    
    priority_queue = []                    

    for i, event in enumerate(events[:current_step_idx+1]):
        event_type = event.get('event')
        if event_type == 'added_node':
            # Adding node to priority queue
            if all(k in event for k in ['coordinate', 'GCost', 'HCost', 'FScore']):
                node = {
                    'coordinate': event['coordinate'],
                    'from_coordinate': event.get('from_coordinate'),
                    'GCost': event['GCost'],
                    'HCost': event['HCost'], 
                    'FScore': event['FScore'],
                    'bot_direction': event.get('bot_direction'),
                    'physical_direction': event.get('physical_direction'),
                    'rack_direction': event.get('rack_direction'),
                    'turn_tag': event.get('turn_tag'),
                    'moving_status': event.get('moving_status'),
                    'pause_time': event.get('pause_time', 0)
                }
                # Checking if this node is already in the queue
                existing_idx = None
                for idx, q_node in enumerate(priority_queue):
                    if (q_node['coordinate'].get('x') == node['coordinate'].get('x') and 
                        q_node['coordinate'].get('y') == node['coordinate'].get('y')):
                        existing_idx = idx
                        break
                if existing_idx is not None:
                    # Update existing node if it has a better score
                    if node['FScore'] < priority_queue[existing_idx]['FScore']:
                        priority_queue[existing_idx] = node
                else:
                    # Add new node
                    priority_queue.append(node)
                    
        elif event_type == 'chosen_node':
            # Remove node from priority queue
            if 'coordinate' in event:
                x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
                # Find and remove the node with matching coordinates
                for idx, node in enumerate(priority_queue):
                    if (node['coordinate'].get('x') == x and 
                        node['coordinate'].get('y') == y):
                        priority_queue.pop(idx)
                        break            

    # Ascending sort by FScore
    priority_queue.sort(key=lambda x: (x['FScore'], x['HCost']))
    return priority_queue

def create_grid_visualization(events, current_step_idx, min_x, min_y, max_x, max_y):
    current_events = events[:current_step_idx+1] if current_step_idx < len(events) else events
    
    chosen_nodes = []
    exploring_nodes = []
    processing_nodes = []
    conflict_nodes = []
    pause_nodes = []
    cannot_revisit_nodes = []
    neighbour_nodes = []
    
    src_coord = None
    dest_coord = None
    all_coords = [] # To determine relevant area on the plot/grid                                                                               

    for event in current_events:
        event_type = event.get('event')
        
        if event_type == 'path_calculation_started':
            if 'src' in event and 'coordinate' in event['src']:
                src_coord = (event['src']['coordinate'].get('x'), event['src']['coordinate'].get('y'))
                if src_coord[0] is not None and src_coord[1] is not None:
                    all_coords.append(src_coord)
            if 'dest' in event and 'coordinate' in event['dest']:
                dest_coord = (event['dest']['coordinate'].get('x'), event['dest']['coordinate'].get('y'))
                if dest_coord[0] is not None and dest_coord[1] is not None:
                    all_coords.append(dest_coord)
                
        elif event_type == 'chosen_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                chosen_nodes.append((x, y))
                all_coords.append((x, y))
                
        elif event_type == 'exploring_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            status = event.get('status')
            if x is not None and y is not None and status == 'accepted':
                exploring_nodes.append((x, y))
                all_coords.append((x, y))
                
        elif event_type == 'processing_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                processing_nodes.append((x, y))
                all_coords.append((x, y))
                
        elif event_type == 'conflict_check' and 'anchor_coordinate' in event:
            x, y = event['anchor_coordinate'].get('x'), event['anchor_coordinate'].get('y')
            conflict = event.get('conflict_found')
            if x is not None and y is not None and conflict:
                conflict_nodes.append((x, y))
                all_coords.append((x, y))
                
        elif event_type == 'pause_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                pause_nodes.append((x, y))
                all_coords.append((x, y))
                
        elif event_type == 'cannot_revisit_node' and 'coordinate' in event:
            x, y = event['coordinate'].get('x'), event['coordinate'].get('y')
            if x is not None and y is not None:
                cannot_revisit_nodes.append((x, y))
                all_coords.append((x, y))
              
          # Extracting neighbouring nodes if the current event is neighbour_nodes
        if event_type == 'neighbour_nodes' and event == events[current_step_idx] and 'parsed_neighbors' in event:
            for neighbor in event['parsed_neighbors']:
                if 'coordinate' in neighbor:
                    x, y = neighbor['coordinate'].get('x'), neighbor['coordinate'].get('y')
                    if x is not None and y is not None:
                        neighbour_nodes.append((x, y))
                        all_coords.append((x, y))
    
    fig = go.Figure()


    # Determine the visible area based on the nodes we need to display
    # Add a small buffer around the area
    buffer = 2
    if all_coords:
        visible_min_x = max(min_x, min(coord[0] for coord in all_coords) - buffer)
        visible_max_x = min(max_x, max(coord[0] for coord in all_coords) + buffer)
        visible_min_y = max(min_y, min(coord[1] for coord in all_coords) - buffer)
        visible_max_y = min(max_y, max(coord[1] for coord in all_coords) + buffer)
    else:
        visible_min_x, visible_max_x = min_x, max_x
        visible_min_y, visible_max_y = min_y, max_y  
        
    for x in range(int(visible_min_x), int(visible_max_x) + 1):                    
        fig.add_trace(go.Scatter(
            x=[x, x], 
            y=[visible_min_y, visible_max_y],
            mode='lines',
            line=dict(color='lightgray', width=1),
            hoverinfo='none',
            showlegend=False
        ))
    for y in range(int(visible_min_y), int(visible_max_y) + 1):                    
        fig.add_trace(go.Scatter(
            x=[visible_min_x, visible_max_x],
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
      
    if neighbour_nodes:
        x_vals = [coord[0] for coord in neighbour_nodes]
        y_vals = [coord[1] for coord in neighbour_nodes]
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color='blue', size=12, symbol='diamond-open'),
            name='Neighbouring Nodes'
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
            tick0=visible_min_x,
            dtick=1,
            range=[visible_min_x - 1, visible_max_x + 1]                    
        ),
        yaxis=dict(
            title='Y Coordinate',
            tickmode='linear',
            tick0=visible_min_y,                    
            dtick=1,
            range=[visible_min_y - 1, visible_max_y + 1],
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
          
        if 'from_coordinate' in event:
            from_coord = event['from_coordinate']
            st.write(f"From Coordinate: ({from_coord.get('x')}, {from_coord.get('y')})")
        
        if 'bot_direction' in event:
            st.write(f"Bot Direction: {event.get('bot_direction')}")
            
        if 'physical_direction' in event:
            st.write(f"Physical Direction: {event.get('physical_direction')}")
            
        if 'rack_direction' in event:
            st.write(f"Rack Direction: {event.get('rack_direction')}")
        
        if 'GCost' in event and 'HCost' in event and 'FScore' in event:
            st.write(f"G Cost: {event.get('GCost')}")
            st.write(f"H Cost: {event.get('HCost')}")
            st.write(f"F Score: {event.get('FScore')}")
    
    elif event_type == 'neighbour_nodes':
        st.write(f"Neighbours Raw: {event.get('neighbors_raw')}")
        
        if 'parsed_neighbors' in event and event['parsed_neighbors']:
            st.subheader("Parsed Neighbours:")
            for i, neighbor in enumerate(event['parsed_neighbors']):
                with st.expander(f"Neighbour {i+1}"):
                    if 'coordinate' in neighbor:
                        st.write(f"Coordinate: ({neighbor['coordinate'].get('x')}, {neighbor['coordinate'].get('y')})")
                    st.write(f"Bot Direction: {neighbor.get('bot_direction')}")
                    st.write(f"Rack Direction: {neighbor.get('rack_direction')}")
                    st.write(f"Turn Tag: {neighbor.get('turn_tag')}")
                    st.write(f"Moving Status: {neighbor.get('moving_status')}")
    
    elif event_type == 'exploring_node':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        
        st.write(f"Bot Direction: {event.get('bot_direction')}")
        st.write(f"Physical Direction: {event.get('physical_direction')}")
        st.write(f"Rack Direction: {event.get('rack_direction')}")
        st.write(f"Status: {event.get('status')}")


        # Highlighting rejection reason if the node was rejected
        if event.get('status') == 'rejected' and 'rejection_reason' in event:
            st.markdown("<div style='background-color: #ffcccc; padding: 10px; border-radius: 5px; margin-top: 10px;'>"
                      f"<strong>Rejection Reason:</strong> {event.get('rejection_reason')}"
                      "</div>", unsafe_allow_html=True)
            
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

        # Highlighting conflict reason if conflict was found
        if event.get('conflict_found') and 'conflict_reason' in event:
            st.markdown("<div style='background-color: #ffcccc; padding: 10px; border-radius: 5px; margin-top: 10px;'>"
                      f"<strong>Conflict Reason:</strong> {event.get('conflict_reason')}"
                      "</div>", unsafe_allow_html=True)

    elif event_type == 'conflict_detected':
        if 'coordinate' in event:
            coord = event['coordinate']
            st.write(f"Coordinate: ({coord.get('x')}, {coord.get('y')})")
        st.write(f"Conflict Found: {event.get('conflict_found')}")
        
        # Highlighting conflict reason
        if 'conflict_reason' in event:
            st.markdown("<div style='background-color: #ffcccc; padding: 10px; border-radius: 5px; margin-top: 10px;'>"
                      f"<strong>Conflict Reason:</strong> {event.get('conflict_reason')}"
                      "</div>", unsafe_allow_html=True)
    
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

def display_priority_queue(events, current_step_idx):
    """Display the current state of the priority queue."""
    priority_queue = track_priority_queue(events, current_step_idx)
    if not priority_queue:
        st.info("Priority queue is empty.")
        return
    st.subheader(f"Priority Queue ({len(priority_queue)} nodes)")
    st.caption("Nodes are sorted by F-Score (lowest first) as in the A* algorithm")
    # Creating a DataFrame                    
    queue_data = []
    for node in priority_queue:
        coord = node['coordinate']
        from_coord = node.get('from_coordinate', {})
        queue_data.append({
            'Coordinate': f"({coord.get('x')}, {coord.get('y')})",
            'From': f"({from_coord.get('x')}, {from_coord.get('y')})" if from_coord else "-",
            'G Cost': node.get('GCost'),
            'H Cost': node.get('HCost'),
            'F Score': node.get('FScore'),
            'Direction': node.get('bot_direction'),
            'Turn Tag': node.get('turn_tag'),
            'Moving Status': node.get('moving_status'),
            'Pause Time': node.get('pause_time', 0)
        })
        
    # Tabular display
    st.dataframe(queue_data, use_container_width=True)
    
    # Visualize the priority queue nodes on a small grid
    if priority_queue:
        st.caption("Priority Queue Nodes Visualization")
        
        coords = [(node['coordinate'].get('x'), node['coordinate'].get('y')) 
                 for node in priority_queue if 'coordinate' in node]
        if coords:
            
            # Determine grid boundaries
            min_x = min(coord[0] for coord in coords) - 1
            max_x = max(coord[0] for coord in coords) + 1
            min_y = min(coord[1] for coord in coords) - 1
            max_y = max(coord[1] for coord in coords) + 1
            
            # simple grid visualization
            fig = go.Figure()
            # Add grid lines
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
            
            # Add nodes with their F-scores 
            x_vals = []
            y_vals = []
            text_vals = []
            hover_texts = []
            for node in priority_queue:
                x = node['coordinate'].get('x')
                y = node['coordinate'].get('y')
                f_score = node.get('FScore')
                g_cost = node.get('GCost')
                h_cost = node.get('HCost')

                x_vals.append(x)
                y_vals.append(y)
                text_vals.append(str(f_score))
                hover_texts.append(f"Coord: ({x}, {y})<br>F: {f_score}<br>G: {g_cost}<br>H: {h_cost}")
                
            # Add nodes
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='markers+text',
                marker=dict(color='orange', size=15, symbol='square'),
                text=text_vals,
                textposition='middle center',
                hovertext=hover_texts,
                hoverinfo='text',
                name='Queue Nodes'
            ))

            

            fig.update_layout(
                title='Priority Queue Nodes',
                xaxis=dict(
                    title='X Coordinate',
                    tickmode='linear',
                    tick0=min_x,
                    dtick=1,
                    range=[min_x - 0.5, max_x + 0.5]
                ),
                yaxis=dict(
                    title='Y Coordinate',
                    tickmode='linear',
                    tick0=min_y,
                    dtick=1,
                    range=[min_y - 0.5, max_y + 0.5],
                    scaleanchor='x',
                    scaleratio=1
                ),
                height=400,
                hovermode='closest',
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

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

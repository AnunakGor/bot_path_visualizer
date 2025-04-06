import json
import re
from datetime import datetime
import os

class PathLogParser:
    """
    Parser for warehouse robot path calculation logs.
    Extracts structured data for visualization.
    """
    
    def __init__(self):
        self.events = []
        self.event_id = 1
        
    def parse_log_file(self, log_file_path):
        """Parse the log file and extract relevant information for visualization."""
        self.events = []
        self.event_id = 1
        
        try:
            with open(log_file_path, 'r') as file:
                lines = file.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Looking for the start of path calculation using 
                # path_calculation_started
                if "#path_calculation_started" in line:
                    self._parse_path_calculation_started(line)
                
                # Parse chosen node events
                elif "#chosen_node" in line:
                    self._parse_chosen_node(line)
                
                # Parse neighbour nodes
                elif "#neighbour_nodes" in line:
                    self._parse_neighbour_nodes(line)
                
                # Parse exploring node
                elif "#exploring_node" in line:
                    # Checking if it is tagged as "not included" in later lines in log file
                    if i + 1 < len(lines) and "not included" in lines[i+1]:
                        # rejected node
                        self._parse_rejected_exploring_node(line, lines[i+1:i+3])
                    else:
                        # accepted node
                        self._parse_exploring_node(line, "accepted")
                
                # Parse processing node
                elif "#processing_node" in line:
                    self._parse_processing_node(line)
                
                # Parse pause node
                elif "#pause_node" in line:
                    self._parse_pause_node(line)
                
                # Parse cannot revisit node
                elif "#cannot_revisit_node" in line:
                    self._parse_cannot_revisit_node(line)
                
                # Parse conflict check
                elif "#conflict_check" in line:
                    # Here multiple line data is collected for conflict_check to get more context
                    conflict_lines = [line]
                    j = i + 1
                    while j < len(lines) and j < i + 10: #Till next 10 lines
                        next_line = lines[j].strip()
                        if "#conflict_check" in next_line or "[Check End]" in next_line:
                            conflict_lines.append(next_line)
                        if "[Check End]" in next_line:
                            break
                        j += 1
                    
                    self._parse_conflict_check(conflict_lines)
                    
                # to handle time conflict lines that don't follow the standard pattern
                elif "not included" in line and "TIME CONFLICT" in line.upper():
                    self._parse_time_conflict(line)
                
                # handling parsing of added node using different formats
                elif "\"#added_node\"" in line or "#added_node" in line:
                    self._parse_added_node(line)

                # Parse path calculation ended
                elif "#path_calculation_ended" in line or "path calculation ended" in line.lower():

                    self._parse_path_calculation_ended(line)
                
                i += 1
            
            return self.events
        
        except Exception as e:
            print(f"Error parsing log file: {str(e)}")
            return []
    
    def save_to_json(self, output_file_path):
        """Save the parsed events to a JSON file."""
        try:
            with open(output_file_path, 'w') as file:
                json.dump(self.events, file, indent=2)
            return True
        except Exception as e:
            print(f"Error saving to JSON: {str(e)}")
            return False
    
    def _extract_timestamp(self, line):
        """Extract timestamp from the log line"""
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_bot_id(self, line):
        """Extract bot ID from the log line."""
        match = re.search(r'butler_id=(\d+)', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_coordinate(self, coord_str):
        """Extract X,Y coordinates from a coordinate string."""
        match = re.search(r'\{(\d+),(\d+)\}', coord_str)
        if match:
            return {
                "x": int(match.group(1)),
                "y": int(match.group(2))
            }
        return None
    
    def _extract_direction(self, dir_str):
        """Extract direction from a direction string."""
        dir_match = re.search(r'(north|south|east|west)', dir_str)
        if dir_match:
            return dir_match.group(1)
        return None
    
    def _parse_path_calculation_started(self, line):
        """Parse the path calculation started event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # source information
        src_match = re.search(r'SRC = \{\{(\d+),(\d+)\},(.*?)\}', line)
        if src_match:
            src_x, src_y = int(src_match.group(1)), int(src_match.group(2))
            directions = src_match.group(3).split(',')
            bot_direction = directions[0].strip() if len(directions) > 0 else None
            
            src_data = {
                "coordinate": {"x": src_x, "y": src_y},
                "bot_direction": bot_direction
            }
        else:
            src_data = {}
        
        # destination information
        dest_match = re.search(r'DEST = \{\{(\d+),(\d+)\}', line)
        if dest_match:
            dest_x, dest_y = int(dest_match.group(1)), int(dest_match.group(2))
            dest_data = {
                "coordinate": {"x": dest_x, "y": dest_y}
            }
        else:
            dest_data = {}
        
        event = {
            "event_id": self.event_id,
            "event": "path_calculation_started",
            "timestamp": timestamp,
            "bot_id": bot_id,
            "src": src_data,
            "dest": dest_data
        }
        
        self.events.append(event)
        self.event_id += 1
    
    def _parse_chosen_node(self, line):
        """Parse the chosen node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Format: #chosen_node = {{442,20}, {444,20}, rest, butler_moving, east, east, south, no_turn_rotate}
        # Extracting coordinate information
        coord_match = re.search(r'\{\{(\d+),(\d+)\}, \{(\d+),(\d+)\}', line)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            
            # Extracting costs (gcost, hcost, fscore)
            gcost_match = re.search(r'GCost = (\d+)', line)
            hcost_match = re.search(r'HCost = (\d+)', line)
            fscore_match = re.search(r'FScore = (\d+)', line)
            
            gcost = int(gcost_match.group(1)) if gcost_match else None
            hcost = int(hcost_match.group(1)) if hcost_match else None
            fscore = int(fscore_match.group(1)) if fscore_match else None

            directions_match = re.search(r'\}, ([^,]+), ([^,]+), ([^,]+), ([^,]+), ([^,]+)', line)
            
            bot_direction = None
            physical_direction = None
            rack_direction = None
            
            if directions_match:
                # In the format, the 3rd, 4th, and 5th groups are the directions
                bot_direction = directions_match.group(3)
                physical_direction = directions_match.group(4)
                rack_direction = directions_match.group(5)
            
            event = {
                "event_id": self.event_id,
                "event": "chosen_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "from_coordinate": {"x": from_x, "y": from_y},
                "GCost": gcost,
                "HCost": hcost,
                "FScore": fscore,
                "bot_direction": bot_direction,
                "physical_direction": physical_direction,
                "rack_direction": rack_direction
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_neighbour_nodes(self, line):
        """Parse the neighbor nodes event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # extracting raw neighbor nodes information
        neighbors_match = re.search(r'#neighbour_nodes = \[(.*?)\]', line)
        if neighbors_match:
            neighbors_raw = neighbors_match.group(1)
            
            event = {
                "event_id": self.event_id,
                "event": "neighbour_nodes",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "neighbors_raw": neighbors_raw
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_exploring_node(self, line, status):
        """Parse the exploring node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Parse coordinates and directions
        # Format: #exploring_node = {{442,20}, east, east, south}
        node_match = re.search(r'#exploring_node = \{\{(\d+),(\d+)\}, ([\w]+), ([\w]+), ([\w]+)\}', line)
        
        if node_match:
            x, y = int(node_match.group(1)), int(node_match.group(2))
            bot_direction = node_match.group(3)
            physical_direction = node_match.group(4)
            rack_direction = node_match.group(5)
            
            event = {
                "event_id": self.event_id,
                "event": "exploring_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "bot_direction": bot_direction,
                "physical_direction": physical_direction,
                "rack_direction": rack_direction,
                "status": status
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_rejected_exploring_node(self, line, next_lines):
        """Parse the exploring node that was rejected."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Parsing coordinates and directions
        # Format: #exploring_node = {{442,20}, east, east, south}
        node_match = re.search(r'#exploring_node = \{\{(\d+),(\d+)\}, ([\w]+), ([\w]+), ([\w]+)\}', line)
        
        if node_match:
            x, y = int(node_match.group(1)), int(node_match.group(2))
            bot_direction = node_match.group(3)
            physical_direction = node_match.group(4)
            rack_direction = node_match.group(5)
            
            # Get rejection reason from the next line of log file
            rejection_reason = "Unknown reason"
            if len(next_lines) > 0 and "reason =" in next_lines[0]:
                reason_match = re.search(r'reason\s*=\s*(.+)$', next_lines[0])
                if reason_match:
                    rejection_reason = reason_match.group(1).strip()
            
            event = {
                "event_id": self.event_id,
                "event": "exploring_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "bot_direction": bot_direction,
                "physical_direction": physical_direction,
                "rack_direction": rack_direction,
                "status": "rejected",
                "rejection_reason": rejection_reason
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_processing_node(self, line):
        """Parse the processing node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Parse coordinates
        # Format: #processing_node = {{442,20}, {444,20}, rest, butler_moving, south, south, south}
        node_match = re.search(r'#processing_node = \{\{(\d+),(\d+)\}, \{(\d+),(\d+)\}', line)
        
        if node_match:
            x, y = int(node_match.group(1)), int(node_match.group(2))
            from_x, from_y = int(node_match.group(3)), int(node_match.group(4))
            
            event = {
                "event_id": self.event_id,
                "event": "processing_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "from_coordinate": {"x": from_x, "y": from_y}
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_conflict_check(self, conflict_lines):
        """Parse the conflict check event with multiple lines for context."""
        if not conflict_lines:
            return
            
        line = conflict_lines[0]  # First line with AnchorCoord
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Extracting anchor coordinate
        anchor_match = re.search(r'AnchorCoord = \{(\d+),(\d+)\}', line)
        if anchor_match:
            anchor_x, anchor_y = int(anchor_match.group(1)), int(anchor_match.group(2))
            
            # Extracting span coordinates from all related lines to get complete information
            span_coords = []
            
            # First check the initial line for span coordinates
            initial_span_match = re.search(r'SpanCoords = \[(.*?)\]', line)
            if initial_span_match:
                spans_str = initial_span_match.group(1)
                
                for span in spans_str.split(','):
                    span = span.strip()
                    if span:
                        span_coords.append(span)
            
            for cl in conflict_lines:
                # Looking for span coordinates in multiple formats to prevent errors
                span_match1 = re.search(r'span coordinate = \{(\d+),(\d+)\}', cl)
                span_match2 = re.search(r'coordinate = \{(\d+),(\d+)\}', cl)
                span_match3 = re.search(r'SpanCoord = \{(\d+),(\d+)\}', cl)
                
                if span_match1:
                    x, y = span_match1.group(1), span_match1.group(2)
                    span_entry = f"{{{x},{y}}}"
                    if span_entry not in span_coords:
                        span_coords.append(span_entry)
                
                elif span_match2:
                    x, y = span_match2.group(1), span_match2.group(2)
                    span_entry = f"{{{x},{y}}}"
                    if span_entry not in span_coords:
                        span_coords.append(span_entry)
                
                elif span_match3:
                    x, y = span_match3.group(1), span_match3.group(2)
                    span_entry = f"{{{x},{y}}}"
                    if span_entry not in span_coords:
                        span_coords.append(span_entry)
                
                # Also checking for span coordinates in SpanCoords format
                additional_span_match = re.search(r'SpanCoords = \[(.*?)\]', cl)
                if additional_span_match and cl != line:  # Avoid duplicate from the first line
                    spans_str = additional_span_match.group(1)
                    for span in spans_str.split(','):
                        span = span.strip()
                        if span and span not in span_coords:
                            span_coords.append(span)
            
            conflict_found = None
            conflict_reason = None
            
            for cl in conflict_lines:
                # Checking for conflicts
                if "TIME CONFLICT" in cl.upper():
                    conflict_found = True
                    conflict_reason = "TIME CONFLICT"
                    
                elif "Idle reservation on span" in cl:
                    conflict_found = True
                    conflict_reason = "Idle reservation on span"
                    
                elif "has idle conflict" in cl:
                    conflict_found = True
                    conflict_reason = "Idle conflict"
                    
                elif "Reservation Conflict List = []" in cl:
                    if conflict_found is None:  # Only set if not already determined
                        conflict_found = False
                        
                elif "MovableIdleBots = []" in cl:
                    if conflict_found is None:  # Only set if not already determined
                        conflict_found = False
                        
                elif "Reservation Conflict List =" in cl and "[" in cl and "]" in cl:
                    # Check if list is empty or not
                    list_content = re.search(r'Reservation Conflict List = \[(.*?)\]', cl)
                    if list_content and list_content.group(1).strip():
                        conflict_found = True
                        conflict_reason = f"Reservation conflict: {list_content.group(1).strip()}"
                    elif conflict_found is None:
                        conflict_found = False
                
                # checking for conflict details in the last line of Check End
                if "[Check End]" in cl and "Reservation Conflict List =" in cl:
                    conflict_list_match = re.search(r'Reservation Conflict List = (.*?) MovableIdleBots', cl)
                    if conflict_list_match:
                        conflict_list = conflict_list_match.group(1).strip()
                        if conflict_list and conflict_list != "[]":
                            conflict_found = True
                            conflict_reason = f"Reservation conflict in check end: {conflict_list}"
            
            event = {
                "event_id": self.event_id,
                "event": "conflict_check",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "anchor_coordinate": {"x": anchor_x, "y": anchor_y},
                "span_coords": span_coords,
                "conflict_found": conflict_found
            }
            
            # reason for conflict
            if conflict_found and conflict_reason:
                event["conflict_reason"] = conflict_reason
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_time_conflict(self, line):
        """Parse a direct time conflict line."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match = re.search(r'\{\{(\d+),(\d+)\}', line)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            
            # Extract reason
            reason = "TIME CONFLICT"
            reason_match = re.search(r'reason\s*=\s*(.+?)(?:,|$)', line)
            if reason_match:
                reason = reason_match.group(1).strip()
            
            event = {
                "event_id": self.event_id,
                "event": "conflict_detected",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "conflict_found": True,
                "conflict_reason": reason
            }
            
            self.events.append(event)
            self.event_id += 1
            
    def _parse_path_calculation_ended(self, line):
        """Parse the path calculation ended event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Try to extract success/failure status if available
        status = "completed"
        if "failed" in line.lower() or "failure" in line.lower():
            status = "failed"
        elif "success" in line.lower():
            status = "success"
        
        # Try to extract path length if available
        path_length = None
        path_length_match = re.search(r'path length[\s=:]+(\d+\.?\d*)', line, re.IGNORECASE)
        if path_length_match:
            try:
                path_length = float(path_length_match.group(1))
            except ValueError:
                pass
        
        event = {
            "event_id": self.event_id,
            "event": "path_calculation_ended",
            "timestamp": timestamp,
            "bot_id": bot_id,
            "status": status,
            "path_length": path_length
        }
        
        self.events.append(event)
        self.event_id += 1
    
    def _parse_added_node(self, line):
        """Parse the added node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Try different formats for coordinates for added_node
        # Format 1: Coor = {441,20}, FromCoor = {442,20}
        coord_match1 = re.search(r'Coor = \{(\d+),(\d+)\}, FromCoor = \{(\d+),(\d+)\}', line)
        # Format 2: "#added_node", Coor = {444,20}, FromCoor = {444,20}
        coord_match2 = re.search(r'"#added_node".*?Coor = \{(\d+),(\d+)\}, FromCoor = \{(\d+),(\d+)\}', line)
        # Format 3: #added_node: {{442,20}, {444,20}, ...}
        coord_match3 = re.search(r'#added_node.*?\{\{(\d+),(\d+)\},\s*\{(\d+),(\d+)\}', line)
        
        coord_match = coord_match1 or coord_match2 or coord_match3
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            
            # Extract turn tag

            # turn_match = re.search(r'TurnTag = ([^,]+)', line) or re.search(r'turn_tag[=:]\s*([^,]+)', line, re.IGNORECASE)
            turn_match = re.search(r'TurnTag = (\{[^}]+\}|[^,]+),', line)
            turn_tag = turn_match.group(1) if turn_match else None
            
            # Extract moving status
            status_match = re.search(r'MovingStatus = ([^,]+)', line) or re.search(r'moving_status[=:]\s*([^,]+)', line, re.IGNORECASE)
            moving_status = status_match.group(1) if status_match else None
            
            # Extract directions (trying different formats)
            dir_match = re.search(r'BDir = ([^,]+), PhyBDir = ([^,]+), RDir = ([^,]+)', line)
            if not dir_match:
                dir_match = re.search(r'bot_direction[=:]\s*([^,]+).*?physical_direction[=:]\s*([^,]+).*?rack_direction[=:]\s*([^,]+)', line, re.IGNORECASE)
            
            bot_dir = dir_match.group(1) if dir_match else None
            phys_dir = dir_match.group(2) if dir_match else None
            rack_dir = dir_match.group(3) if dir_match else None
            
            # Extract costs
            gcost_match = re.search(r'GCost = (\d+)', line) or re.search(r'g_cost[=:]\s*(\d+)', line, re.IGNORECASE)
            hcost_match = re.search(r'HCost = (\d+)', line) or re.search(r'h_cost[=:]\s*(\d+)', line, re.IGNORECASE)
            fscore_match = re.search(r'FScore = (\d+)', line) or re.search(r'f_score[=:]\s*(\d+)', line, re.IGNORECASE)
            pause_match = re.search(r'PauseTime = (\d+)', line) or re.search(r'pause_time[=:]\s*(\d+)', line, re.IGNORECASE)
            
            gcost = int(gcost_match.group(1)) if gcost_match else None
            hcost = int(hcost_match.group(1)) if hcost_match else None
            fscore = int(fscore_match.group(1)) if fscore_match else None
            pause_time = int(pause_match.group(1)) if pause_match else 0
            
            event = {
                "event_id": self.event_id,
                "event": "added_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "from_coordinate": {"x": from_x, "y": from_y},
                "turn_tag": turn_tag,
                "moving_status": moving_status,
                "bot_direction": bot_dir,
                "physical_direction": phys_dir,
                "rack_direction": rack_dir,
                "GCost": gcost,
                "HCost": hcost,
                "FScore": fscore,
                "pause_time": pause_time
            }
            
            self.events.append(event)
            self.event_id += 1

    def _parse_pause_node(self, line):
        """Parse pause node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Format in log: #pause_node = {{442,20}, south, south}, PauseTime = 16449
        coord_match = re.search(r'#pause_node\s*=\s*\{\{(\d+),(\d+)\},\s*([\w]+),\s*([\w]+)\}', line)
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            bot_direction = coord_match.group(3)
            rack_direction = coord_match.group(4)
            
            # Extract pause time 
            pause_time_match = re.search(r'PauseTime\s*=\s*(\d+)', line)
            pause_time = int(pause_time_match.group(1)) if pause_time_match else 0
            
            # Extract reason if available
            reason_match = re.search(r'reason\s*=\s*(.+?)(?:,|$)', line, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "Automatic pause"
            
            event = {
                "event_id": self.event_id,
                "event": "pause_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "bot_direction": bot_direction,
                "rack_direction": rack_direction,
                "pause_time": pause_time,
                "reason": reason
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_cannot_revisit_node(self, line):
        """Parse cannot revisit node event."""
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        # Format in log: #cannot_revisit_node {{436,18}, {435,20}, rest, butler_moving, north, south}
        coord_match = re.search(r'#cannot_revisit_node\s*\{\{(\d+),(\d+)\},\s*\{(\d+),(\d+)\},\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+)\}', line)
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            turn_tag = coord_match.group(5)
            moving_status = coord_match.group(6)
            bot_direction = coord_match.group(7)
            rack_direction = coord_match.group(8)
            
            # Extract reason if available
            reason_match = re.search(r'reason\s*=\s*(.+?)(?:,|$)', line, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "Node already visited"
            
            event = {
                "event_id": self.event_id,
                "event": "cannot_revisit_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "from_coordinate": {"x": from_x, "y": from_y},
                "turn_tag": turn_tag,
                "moving_status": moving_status,
                "bot_direction": bot_direction,
                "rack_direction": rack_direction,
                "reason": reason
            }
            
            self.events.append(event)
            self.event_id += 1

def parse_log_to_json(log_file_path, output_file_path=None):
    """
    Parse a path calculation log file and convert to JSON.
    Arguments:
        log_file_path: Path to the log file
        output_file_path: Optional output path for JSON file
    Returns:
        List of parsed events
    """
    parser = PathLogParser()
    events = parser.parse_log_file(log_file_path)
    
    if output_file_path:
        parser.save_to_json(output_file_path)
    
    return events

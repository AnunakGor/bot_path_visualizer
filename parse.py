import json
import re
from datetime import datetime
import os

class PathLogParser:
    
    def __init__(self):
        self.events = []
        self.event_id = 1
        
    def parse_log_file(self, log_file_path):
        self.events = []
        self.event_id = 1
        
        try:
            with open(log_file_path, 'r') as file:
                lines = file.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if "#path_calculation_started" in line:
                    self._parse_path_calculation_started(line)
                
                elif "#chosen_node" in line:
                    self._parse_chosen_node(line)
                
                elif "#neighbour_nodes" in line:
                    self._parse_neighbour_nodes(line)
                
                elif "#exploring_node" in line:
                    if i + 1 < len(lines) and "not included" in lines[i+1]:
                        self._parse_rejected_exploring_node(line, lines[i+1:i+3])
                    else:
                        self._parse_exploring_node(line, "accepted")
                
                elif "#processing_node" in line:
                    self._parse_processing_node(line)
                
                elif "#pause_node" in line:
                    self._parse_pause_node(line)
                
                elif "#cannot_revisit_node" in line:
                    self._parse_cannot_revisit_node(line)
                
                elif "#conflict_check" in line:
                    conflict_lines = [line]
                    j = i + 1
                    while j < len(lines) and j < i + 10:
                        next_line = lines[j].strip()
                        if "#conflict_check" in next_line or "[Check End]" in next_line:
                            conflict_lines.append(next_line)
                        if "[Check End]" in next_line:
                            break
                        j += 1
                    
                    self._parse_conflict_check(conflict_lines)
                    
                elif "not included" in line and "TIME CONFLICT" in line.upper():
                    self._parse_time_conflict(line)
                
                elif "\"#added_node\"" in line or "#added_node" in line:
                    self._parse_added_node(line)
                
                i += 1
            
            return self.events
        
        except Exception as e:
            print(f"Error parsing log file: {str(e)}")
            return []
    
    def save_to_json(self, output_file_path):
        try:
            with open(output_file_path, 'w') as file:
                json.dump(self.events, file, indent=2)
            return True
        except Exception as e:
            print(f"Error saving to JSON: {str(e)}")
            return False
    
    def _extract_timestamp(self, line):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_bot_id(self, line):
        match = re.search(r'butler_id=(\d+)', line)
        if match:
            return match.group(1)
        return None
    
    def _extract_coordinate(self, coord_str):
        match = re.search(r'\{(\d+),(\d+)\}', coord_str)
        if match:
            return {
                "x": int(match.group(1)),
                "y": int(match.group(2))
            }
        return None
    
    def _extract_direction(self, dir_str):
        dir_match = re.search(r'(north|south|east|west)', dir_str)
        if dir_match:
            return dir_match.group(1)
        return None
    
    def _parse_path_calculation_started(self, line):
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
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
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match = re.search(r'\{\{(\d+),(\d+)\}, \{(\d+),(\d+)\}', line)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            
            gcost_match = re.search(r'GCost = (\d+)', line)
            hcost_match = re.search(r'HCost = (\d+)', line)
            fscore_match = re.search(r'FScore = (\d+)', line)
            
            gcost = int(gcost_match.group(1)) if gcost_match else None
            hcost = int(hcost_match.group(1)) if hcost_match else None
            fscore = int(fscore_match.group(1)) if fscore_match else None
            
            event = {
                "event_id": self.event_id,
                "event": "chosen_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "from_coordinate": {"x": from_x, "y": from_y},
                "GCost": gcost,
                "HCost": hcost,
                "FScore": fscore
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_neighbour_nodes(self, line):
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
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
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
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
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        node_match = re.search(r'#exploring_node = \{\{(\d+),(\d+)\}, ([\w]+), ([\w]+), ([\w]+)\}', line)
        
        if node_match:
            x, y = int(node_match.group(1)), int(node_match.group(2))
            bot_direction = node_match.group(3)
            physical_direction = node_match.group(4)
            rack_direction = node_match.group(5)
            
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
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
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
        if not conflict_lines:
            return
            
        line = conflict_lines[0]
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        anchor_match = re.search(r'AnchorCoord = \{(\d+),(\d+)\}', line)
        if anchor_match:
            anchor_x, anchor_y = int(anchor_match.group(1)), int(anchor_match.group(2))
            
            span_coords = []
            
            initial_span_match = re.search(r'SpanCoords = \[(.*?)\]', line)
            if initial_span_match:
                spans_str = initial_span_match.group(1)
                for span in spans_str.split(','):
                    span = span.strip()
                    if span:
                        span_coords.append(span)
            
            for cl in conflict_lines:
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
                
                additional_span_match = re.search(r'SpanCoords = \[(.*?)\]', cl)
                if additional_span_match and cl != line:
                    spans_str = additional_span_match.group(1)
                    for span in spans_str.split(','):
                        span = span.strip()
                        if span and span not in span_coords:
                            span_coords.append(span)
            
            conflict_found = None
            conflict_reason = None
            
            for cl in conflict_lines:
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
                    if conflict_found is None:
                        conflict_found = False
                        
                elif "MovableIdleBots = []" in cl:
                    if conflict_found is None:
                        conflict_found = False
                        
                elif "Reservation Conflict List =" in cl and "[" in cl and "]" in cl:
                    list_content = re.search(r'Reservation Conflict List = \[(.*?)\]', cl)
                    if list_content and list_content.group(1).strip():
                        conflict_found = True
                        conflict_reason = f"Reservation conflict: {list_content.group(1).strip()}"
                    elif conflict_found is None:
                        conflict_found = False
                
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
            
            if conflict_found and conflict_reason:
                event["conflict_reason"] = conflict_reason
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_time_conflict(self, line):
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match = re.search(r'\{\{(\d+),(\d+)\}', line)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            
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
    
    def _parse_added_node(self, line):
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match1 = re.search(r'Coor = \{(\d+),(\d+)\}, FromCoor = \{(\d+),(\d+)\}', line)
        coord_match2 = re.search(r'"#added_node".*?Coor = \{(\d+),(\d+)\}, FromCoor = \{(\d+),(\d+)\}', line)
        coord_match3 = re.search(r'#added_node.*?\{\{(\d+),(\d+)\},\s*\{(\d+),(\d+)\}', line)
        
        coord_match = coord_match1 or coord_match2 or coord_match3
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            
            turn_match = re.search(r'TurnTag = ([^,]+)', line) or re.search(r'turn_tag[=:]\s*([^,]+)', line, re.IGNORECASE)
            turn_tag = turn_match.group(1) if turn_match else None
            
            status_match = re.search(r'MovingStatus = ([^,]+)', line) or re.search(r'moving_status[=:]\s*([^,]+)', line, re.IGNORECASE)
            moving_status = status_match.group(1) if status_match else None
            
            dir_match = re.search(r'BDir = ([^,]+), PhyBDir = ([^,]+), RDir = ([^,]+)', line)
            if not dir_match:
                dir_match = re.search(r'bot_direction[=:]\s*([^,]+).*?physical_direction[=:]\s*([^,]+).*?rack_direction[=:]\s*([^,]+)', line, re.IGNORECASE)
            
            bot_dir = dir_match.group(1) if dir_match else None
            phys_dir = dir_match.group(2) if dir_match else None
            rack_dir = dir_match.group(3) if dir_match else None
            
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
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match = re.search(r'#pause_node\s*=\s*\{\{(\d+),(\d+)\},\s*([\w]+),\s*([\w]+)\}', line)
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            bot_direction = coord_match.group(3)
            rack_direction = coord_match.group(4)
            
            pause_time_match = re.search(r'PauseTime\s*=\s*(\d+)', line)
            pause_time = int(pause_time_match.group(1)) if pause_time_match else 0
            
            
            event = {
                "event_id": self.event_id,
                "event": "pause_node",
                "timestamp": timestamp,
                "bot_id": bot_id,
                "coordinate": {"x": x, "y": y},
                "bot_direction": bot_direction,
                "rack_direction": rack_direction,
                "pause_time": pause_time
            }
            
            self.events.append(event)
            self.event_id += 1
    
    def _parse_cannot_revisit_node(self, line):
        timestamp = self._extract_timestamp(line)
        bot_id = self._extract_bot_id(line)
        
        coord_match = re.search(r'#cannot_revisit_node\s*\{\{(\d+),(\d+)\},\s*\{(\d+),(\d+)\},\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+)\}', line)
        
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            from_x, from_y = int(coord_match.group(3)), int(coord_match.group(4))
            turn_tag = coord_match.group(5)
            moving_status = coord_match.group(6)
            bot_direction = coord_match.group(7)
            rack_direction = coord_match.group(8)
            
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
    parser = PathLogParser()
    events = parser.parse_log_file(log_file_path)
    
    if output_file_path:
        parser.save_to_json(output_file_path)
    
    return events

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <log_file> [output_file]")
        sys.exit(1)
    
    log_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    events = parse_log_to_json(log_file, output_file)
    
    if not output_file:
        print(json.dumps(events, indent=2))

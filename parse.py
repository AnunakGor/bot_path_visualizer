import re
import json

pattern_started = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#path_calculation_started\s+SRC = \{\{(?P<src_x>\d+),(?P<src_y>\d+)\},(?P<src_dir>\w+),\w+\},\s+DEST = \{\{(?P<dest_x>\d+),(?P<dest_y>\d+)\},\w+\}'
)

pattern_added_node = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#added_node,?\s+Coor = \{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s+FromCoor = \{(?P<from_x>\d+),(?P<from_y>\d+)\}.*GCost = (?P<GCost>\d+),\s+HCost = (?P<HCost>\d+),\s+FScore = (?P<FScore>\d+)'
)

pattern_chosen_node = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#chosen_node\s+\{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*\{(?P<from_x>\d+),(?P<from_y>\d+)\}.*GCost = (?P<GCost>\d+),\s+HCost = (?P<HCost>\d+),\s+FScore = (?P<FScore>\d+)'
)

pattern_neighbour_nodes = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#neighbour_nodes\s+=\s+\[(?P<neighbors>.+)\]'
)

pattern_exploring_node = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#exploring_node\s+=\s+\{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*(?P<bot_dir>\w+),\s*(?P<phys_dir>\w+),\s*(?P<rack_dir>\w+)\}'
)

pattern_exploring_node_rejected = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*Node = \{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*(?P<bot_dir>\w+),(?P<rack_dir>\w+)\}\s+not included, reason\s+=\s+(?P<reason>.+)$'
)

pattern_processing_node = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#processing_node\s+=\s+\{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*\{(?P<from_x>\d+),(?P<from_y>\d+)\}.*'
)

pattern_conflict_check = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#conflict_check:.*AnchorCoord\s+=\s+\{(?P<anchor_x>\d+),(?P<anchor_y>\d+)\}.*, Span Coords\s+=\s+\[(?P<span_coords>.+?)\].*$'
)

pattern_conflict_check_rejected = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#conflict_check.*Node = \{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*(?P<bot_dir>\w+),(?P<rack_dir>\w+)\}\s+not included, reason\s+=\s+(?P<reason>.+)$'
)

parsed_events = []

def parse_line(line):
    match = pattern_started.match(line)
    if match:
        return {
            "event": "path_calculation_started",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "src": {
                "coordinate": {"x": int(match.group("src_x")), "y": int(match.group("src_y"))},
                "bot_direction": match.group("src_dir")
            },
            "dest": {
                "coordinate": {"x": int(match.group("dest_x")), "y": int(match.group("dest_y"))}
            }
        }
    
    match = pattern_added_node.match(line)
    if match:
        return {
            "event": "added_node",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "from_coordinate": {"x": int(match.group("from_x")), "y": int(match.group("from_y"))},
            "GCost": int(match.group("GCost")),
            "HCost": int(match.group("HCost")),
            "FScore": int(match.group("FScore"))
        }
    
    match = pattern_chosen_node.match(line)
    if match:
        return {
            "event": "chosen_node",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "from_coordinate": {"x": int(match.group("from_x")), "y": int(match.group("from_y"))},
            "GCost": int(match.group("GCost")),
            "HCost": int(match.group("HCost")),
            "FScore": int(match.group("FScore"))
        }
    
    match = pattern_neighbour_nodes.match(line)
    if match:
        return {
            "event": "neighbour_nodes",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "neighbors_raw": match.group("neighbors").strip()
        }
    
    match = pattern_exploring_node.match(line)
    if match:
        return {
            "event": "exploring_node",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "bot_direction": match.group("bot_dir"),
            "physical_direction": match.group("phys_dir"),
            "rack_direction": match.group("rack_dir"),
            "status": "accepted"
        }
    
    match = pattern_exploring_node_rejected.match(line)
    if match:
        return {
            "event": "exploring_node",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "bot_direction": match.group("bot_dir"),
            "rack_direction": match.group("rack_dir"),
            "status": "rejected",
            "reason": match.group("reason").strip()
        }
    
    match = pattern_processing_node.match(line)
    if match:
        return {
            "event": "processing_node",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "from_coordinate": {"x": int(match.group("from_x")), "y": int(match.group("from_y"))}
        }
    
    match = pattern_conflict_check.match(line)
    if match:
        span_coords_raw = match.group("span_coords")
        span_coords = [sc.strip() for sc in span_coords_raw.split('},') if sc]
        return {
            "event": "conflict_check",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "anchor_coordinate": {"x": int(match.group("anchor_x")), "y": int(match.group("anchor_y"))},
            "span_coords": span_coords,
            "status": "accepted"
        }
    
    match = pattern_conflict_check_rejected.match(line)
    if match:
        return {
            "event": "conflict_check",
            "timestamp": match.group("timestamp"),
            "bot_id": match.group("bot_id"),
            "coordinate": {"x": int(match.group("coord_x")), "y": int(match.group("coord_y"))},
            "bot_direction": match.group("bot_dir"),
            "rack_direction": match.group("rack_dir"),
            "status": "rejected",
            "reason": match.group("reason").strip()
        }
    
    return None

log_file_path = 'path_calc_bot_11468.log'
with open(log_file_path, 'r') as f:
    for line in f:
        parsed = parse_line(line)
        if parsed:
            parsed_events.append(parsed)

with open('parsed_log.json', 'w') as outfile:
    json.dump(parsed_events, outfile, indent=2)

print("Parsed events:", len(parsed_events))

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
    r'^.*Node = \{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*(?P<bot_dir>\w+),(?P<rack_dir>\w+)\}\s+not included, reason\s+=\s+(?P<reason>.+)$'
)

pattern_processing_node = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#processing_node\s+=\s+\{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*\{(?P<from_x>\d+),(?P<from_y>\d+)\}.*'
)

pattern_conflict_check = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*#conflict_check:.*AnchorCoord\s+=\s+\{(?P<anchor_x>\d+),(?P<anchor_y>\d+)\}.*, Span Coords\s+=\s+\[(?P<span_coords>.+?)\].*$'
)

pattern_conflict_check_rejected = re.compile(
    r'^(?P<timestamp>\S+ \S+).*butler_id=(?P<bot_id>\d+).*(?:#conflict_check|#ButlerId_\d+):\s+Node = \{\{(?P<coord_x>\d+),(?P<coord_y>\d+)\},\s*(?P<bot_dir>\w+),(?P<rack_dir>\w+)\}\s+not included, reason\s+=\s+(?P<reason>.+)$'
)

parsed_events = []

def parse_lines(lines):
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        parsed = None

        m = pattern_started.match(line)
        if m:
            parsed = {
                "event": "path_calculation_started",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "src": {
                    "coordinate": {"x": int(m.group("src_x")), "y": int(m.group("src_y"))},
                    "bot_direction": m.group("src_dir")
                },
                "dest": {
                    "coordinate": {"x": int(m.group("dest_x")), "y": int(m.group("dest_y"))}
                }
            }
            parsed_events.append(parsed)
            i += 1
            continue

        m = pattern_added_node.match(line)
        if m:
            parsed = {
                "event": "added_node",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "coordinate": {"x": int(m.group("coord_x")), "y": int(m.group("coord_y"))},
                "from_coordinate": {"x": int(m.group("from_x")), "y": int(m.group("from_y"))},
                "GCost": int(m.group("GCost")),
                "HCost": int(m.group("HCost")),
                "FScore": int(m.group("FScore"))
            }
            parsed_events.append(parsed)
            i += 1
            continue

        m = pattern_chosen_node.match(line)
        if m:
            parsed = {
                "event": "chosen_node",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "coordinate": {"x": int(m.group("coord_x")), "y": int(m.group("coord_y"))},
                "from_coordinate": {"x": int(m.group("from_x")), "y": int(m.group("from_y"))},
                "GCost": int(m.group("GCost")),
                "HCost": int(m.group("HCost")),
                "FScore": int(m.group("FScore"))
            }
            parsed_events.append(parsed)
            i += 1
            continue

        m = pattern_neighbour_nodes.match(line)
        if m:
            parsed = {
                "event": "neighbour_nodes",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "neighbors_raw": m.group("neighbors").strip()
            }
            parsed_events.append(parsed)
            i += 1
            continue

        m = pattern_exploring_node.match(line)
        if m:
            exploring = {
                "event": "exploring_node",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "coordinate": {"x": int(m.group("coord_x")), "y": int(m.group("coord_y"))},
                "bot_direction": m.group("bot_dir"),
                "physical_direction": m.group("phys_dir"),
                "rack_direction": m.group("rack_dir"),
                "status": "accepted"
            }
            reasons = []
            look_ahead = 1
            while i + look_ahead < len(lines):
                next_line = lines[i + look_ahead].strip()
                m_reject = pattern_exploring_node_rejected.match(next_line)
                if m_reject:
                    reasons.append(m_reject.group("reason").strip())
                    look_ahead += 1
                else:
                    break
            if reasons:
                exploring["status"] = "rejected"
                exploring["rejection_reasons"] = reasons
            parsed_events.append(exploring)
            i += look_ahead
            continue

        m = pattern_processing_node.match(line)
        if m:
            parsed = {
                "event": "processing_node",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "coordinate": {"x": int(m.group("coord_x")), "y": int(m.group("coord_y"))},
                "from_coordinate": {"x": int(m.group("from_x")), "y": int(m.group("from_y"))}
            }
            parsed_events.append(parsed)
            i += 1
            continue

        m = pattern_conflict_check.match(line)
        if m:
            span_coords_raw = m.group("span_coords")
            spans = [sc.strip() + "}" if not sc.strip().endswith("}") else sc.strip() for sc in span_coords_raw.split("},") if sc.strip()]
            conflict = {
                "event": "conflict_check",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "anchor_coordinate": {"x": int(m.group("anchor_x")), "y": int(m.group("anchor_y"))},
                "span_coords": spans,
                "conflict_found": None
            }
            look_ahead = 1
            rejection_reasons = []
            while i + look_ahead < len(lines):
                next_line = lines[i + look_ahead].strip()
                m_reject = pattern_conflict_check_rejected.match(next_line)
                if m_reject:
                    rejection_reasons.append(m_reject.group("reason").strip())
                    look_ahead += 1
                else:
                    break
            if rejection_reasons:
                conflict["conflict_found"] = " ".join(rejection_reasons)
            parsed_events.append(conflict)
            i += look_ahead
            continue

        m = pattern_conflict_check_rejected.match(line)
        if m:
            parsed = {
                "event": "conflict_check",
                "timestamp": m.group("timestamp"),
                "bot_id": m.group("bot_id"),
                "coordinate": {"x": int(m.group("coord_x")), "y": int(m.group("coord_y"))},
                "bot_direction": m.group("bot_dir"),
                "rack_direction": m.group("rack_dir"),
                "conflict_found": m.group("reason").strip()
            }
            parsed_events.append(parsed)
            i += 1
            continue

        i += 1

log_file_path = 'path_calc_bot_11468.log'
with open(log_file_path, 'r') as f:
    lines = f.readlines()

parse_lines(lines)

with open('parsed_log.json', 'w') as outfile:
    json.dump(parsed_events, outfile, indent=2)

print("Parsed events:", len(parsed_events))

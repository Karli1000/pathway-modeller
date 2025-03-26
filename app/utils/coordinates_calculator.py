EventWidth = 36
EventHeight = 36
TaskWidth = 100
TaskHeight = 80
XSpacing = 55
YSpacing = 150

def calculate_diagram_coordinates(json_bpmn):
    x = 200
    y = 100

    def calculate_node_coordinates(node, x, y):
        node['width'] = TaskWidth if node['type'] == 'task' else EventWidth
        node['height'] = TaskHeight if node['type'] == 'task' else EventHeight
        node['x'] = x
        node['y'] = y - (node['height'] / 2)

        next_x = x
        max_y = y

        if 'branches' in node:
            branch_y = max_y
            branch_x = next_x + node['width'] + XSpacing
            branch_max_y = max_y

            for branch_node in node['branches']:
                node_x = branch_x
                branch_height = 0
                is_first_node = True

                for sub_node in branch_node['branch']:
                    if is_first_node:
                        extra_spacing = (max(len(branch_node.get('label', '')), 15) * 5) if branch_node.get('label') else 0
                        node_x += max(extra_spacing - XSpacing, 55)
                        is_first_node = False
                    sub_node_result = calculate_node_coordinates(sub_node, node_x, branch_y)
                    node_x = sub_node_result['next_x']
                    branch_height = max(branch_height, sub_node_result['next_y'] - branch_y)
                next_x = max(next_x, node_x)
                branch_max_y = max(branch_max_y, branch_y + branch_height)
                branch_y += branch_height + YSpacing
            max_y = branch_max_y
        else:
            next_x = x + node['width'] + XSpacing
        return {'next_x': next_x, 'next_y': max_y}

    x = calculate_node_coordinates(json_bpmn['startEvent'], x, y)['next_x']
    for node in json_bpmn['process']:
        x = calculate_node_coordinates(node, x, y)['next_x']
    calculate_node_coordinates(json_bpmn['endEvent'], x, y)
    return json_bpmn

def calculate_waypoints(point1, point2):
    point3 = None
    if point1['y'] != point2['y']:
        if point1['y'] < point2['y']:
            point1['x'] -= 18
            point1['y'] += 18
            x = min(point1['x'], point2['x'])
            y = max(point1['y'], point2['y'])
        else:
            point2['x'] += 18
            point2['y'] += 18
            x = max(point1['x'], point2['x'])
            y = max(point1['y'], point2['y'])
        point3 = {'x': x, 'y': y}
    return {'point1': point1, 'point2': point2, 'point3': point3}

def calculate_sequence_flow_points(json_bpmn):
    for flow in json_bpmn['sequenceFlows']:
        from_node = flow['from']
        to_node = flow['to']
        if from_node and to_node:
            start_point = {
                'x': from_node['x'] + from_node['width'],
                'y': from_node['y'] + from_node['height'] / 2
            }
            end_point = {
                'x': to_node['x'],
                'y': to_node['y'] + to_node['height'] / 2
            }
            waypoints = calculate_waypoints(start_point, end_point)
            flow['point1'] = waypoints['point1']
            flow['point2'] = waypoints['point2']
            flow['point3'] = waypoints.get('point3')
            flow['labelX'] = flow['point1']['x'] + 15
            flow['labelY'] = flow['point2']['y'] - 15
        else:
            print(f"Node with id {flow['from']['id']} or {flow['to']['id']} not found.")
        if flow.get('middle') and flow['from']['y'] != flow['middle']['y']:
            flow['point1']['x'] -= 18
            flow['point1']['y'] += 18
            flow['point2']['x'] += 18
            flow['point2']['y'] += 18
            flow['point3'] = {'x': flow['point1']['x'], 'y': flow['middle']['y']}
            flow['point4'] = {'x': flow['point2']['x'], 'y': flow['middle']['y']}
            flow['labelX'] = flow['point1']['x'] + 15
            flow['labelY'] = flow['middle']['y'] - 15
    return json_bpmn

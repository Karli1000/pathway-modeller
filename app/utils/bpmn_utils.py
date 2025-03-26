def add_joining_gateways(json_bpmn):
    def traverse_and_insert(node):
        # Handle branches
        if 'branches' in node:
            for branch_node in node['branches']:
                for i in reversed(range(len(branch_node['branch']))):
                    sub_node = branch_node['branch'][i]
                    if ('branches' in sub_node or sub_node.get('type') == 'loop') and not sub_node.get('inserted'):
                        insertion_index = i + 1
                        inserted_node = {'type': sub_node['type'], 'inserted': True}
                        if sub_node.get('type') == 'loop':
                            inserted_node['condition'] = sub_node['condition']
                            #del sub_node['condition'] <------------------------------------------------ gelöscht
                        branch_node['branch'].insert(insertion_index, inserted_node)
                    traverse_and_insert(sub_node)
        # Handle loop body
        if 'body' in node:
            for i in reversed(range(len(node['body']))):
                sub_node = node['body'][i]
                if ('branches' in sub_node or sub_node.get('type') == 'loop') and not sub_node.get('inserted'):
                    insertion_index = i + 1
                    inserted_node = {'type': sub_node['type'], 'inserted': True}
                    if sub_node.get('type') == 'loop':
                        inserted_node['condition'] = sub_node['condition']
                        #del sub_node['condition'] <------------------------------------------------ gelöscht
                    node['body'].insert(insertion_index, inserted_node)
                traverse_and_insert(sub_node)

    if 'process' in json_bpmn and isinstance(json_bpmn['process'], list):
        for i in reversed(range(len(json_bpmn['process']))):
            node = json_bpmn['process'][i]
            if ('branches' in node or node.get('type') == 'loop') and not node.get('inserted'):
                insertion_index = i + 1
                inserted_node = {'type': node['type'], 'inserted': True}
                if node.get('type') == 'loop':
                    inserted_node['condition'] = node['condition']
                    #del node['condition'] <------------------------------------------------ gelöscht
                json_bpmn['process'].insert(insertion_index, inserted_node)
            traverse_and_insert(node)
    return json_bpmn

def add_empty_branches(json_bpmn):
    def traverse_and_add_empty_branches(node):
        if 'branches' in node:
            for branch_node in node['branches']:
                if len(branch_node['branch']) == 0:
                    branch_node['branch'].append({'type': 'empty', 'width': 1, 'height': 1})
                for sub_node in branch_node['branch']:
                    traverse_and_add_empty_branches(sub_node)
        if 'body' in node:
            node['branches'] = [{'label': "", 'branch': node['body']}, {'label': node['condition'], 'branch': []}]
            del node['body']
            traverse_and_add_empty_branches(node)
    if 'process' in json_bpmn and isinstance(json_bpmn['process'], list):
        for node in json_bpmn['process']:
            traverse_and_add_empty_branches(node)
    return json_bpmn

def add_ids(json_bpmn):
    id_counter = 1
    def traverse(nodes):
        nonlocal id_counter
        for sub_node in nodes:
            if 'type' not in sub_node:
                print(f"Fehler: Knoten ohne 'type' gefunden: {sub_node}")
                continue  # Oder Sie können hier einen Fehler werfen
            sub_node['id'] = f"{sub_node['type']}_{id_counter}"
            id_counter += 1
            if 'branches' in sub_node:
                for branch_node in sub_node['branches']:
                    traverse(branch_node['branch'])
    if 'startEvent' in json_bpmn:
        json_bpmn['startEvent']['id'] = f"startEvent_{id_counter}"
        id_counter += 1
    else:
        print("Fehler: 'startEvent' nicht in json_bpmn")
    if 'process' in json_bpmn:
        traverse(json_bpmn['process'])
    else:
        print("Fehler: 'process' nicht in json_bpmn")
    if 'endEvent' in json_bpmn:
        json_bpmn['endEvent']['id'] = f"endEvent_{id_counter}"
    else:
        print("Fehler: 'endEvent' nicht in json_bpmn")
    return json_bpmn


def extract_properties(obj):
    keys = ['id', 'type', 'x', 'y', 'width', 'height']
    return {key: obj.get(key) for key in keys}

def add_sequence_flows(json_bpmn):
    sequence_flows = []
    process = json_bpmn['process']
    first_node = process[0]
    last_node = process[-1]

    sequence_flows.append({'from': extract_properties(json_bpmn['startEvent']), 'to': extract_properties(first_node)})

    add_process_sequence_flows(sequence_flows, process)

    sequence_flows.append({'from': extract_properties(last_node), 'to': extract_properties(json_bpmn['endEvent'])})

    json_bpmn['sequenceFlows'] = sequence_flows
    return json_bpmn

def add_process_sequence_flows(sequence_flows, process):
    if len(process) < 2:
        return
    for i in range(len(process) - 1):
        current_node = process[i]
        next_node = process[i + 1]
        if 'branches' in current_node:
            for branch_node in current_node['branches']:
                branch = branch_node['branch']
                if branch:
                    first_branch_node = branch[0]
                    last_branch_node = branch[-1]
                    if current_node and first_branch_node and first_branch_node.get('type') != 'empty':
                        sequence_flows.append({
                            'from': extract_properties(current_node),
                            'to': extract_properties(first_branch_node),
                            'name': branch_node.get('label')
                        })
                        add_process_sequence_flows(sequence_flows, branch)
                    elif first_branch_node and first_branch_node.get('type') == 'empty':
                        if current_node.get('type') == 'loop' and not current_node.get('inserted'):
                            sequence_flows.append({
                                'from': extract_properties(next_node),
                                'to': extract_properties(current_node),
                                'middle': first_branch_node
                            })
                        else:
                            sequence_flows.append({
                                'from': extract_properties(current_node),
                                'to': extract_properties(next_node),
                                'middle': first_branch_node,
                                'name': branch_node.get('label')
                            })
                    if last_branch_node and last_branch_node.get('type') != 'empty' and next_node:
                        sequence_flows.append({
                            'from': extract_properties(last_branch_node),
                            'to': extract_properties(next_node)
                        })
        else:
            sequence_flows.append({
                'from': extract_properties(current_node),
                'to': extract_properties(next_node)
            })

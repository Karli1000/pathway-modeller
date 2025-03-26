def generate_diagram_xml(path):
    diagram_xml = ''
    shapes_xml = ''

    for node in path:
        diagram_xml += generate_node_xml(node)
        shapes_xml += generate_shape_xml(node)

        if 'branches' in node:
            for branch_node in node['branches']:
                branch_xml, branch_shapes = generate_diagram_xml(branch_node['branch'])
                diagram_xml += branch_xml
                shapes_xml += branch_shapes

    return diagram_xml, shapes_xml

def generate_node_xml(node):
    node_type = node.get('type')
    if node_type == 'task':
        name = node.get('name', '')
        name = name[:50] + '...' if len(name) > 50 else name
        return f'<bpmn:task id="{node["id"]}" name="{name}" />\n'
    elif node_type == 'xor':
        condition = node.get('condition')
        condition_attr = f'name="{condition}"' if condition else ''
        return f'<bpmn:exclusiveGateway id="{node["id"]}" {condition_attr} />\n'
    elif node_type == 'inclusive':
        condition = node.get('condition')
        condition_attr = f'name="{condition}"' if condition else ''
        return f'<bpmn:inclusiveGateway id="{node["id"]}" {condition_attr} />\n'
    elif node_type == 'parallel':
        return f'<bpmn:parallelGateway id="{node["id"]}" />\n'
    elif node_type == 'loop':
        condition = node.get('condition')
        condition_attr = f'name="{condition}"' if condition else ''
        return f'<bpmn:exclusiveGateway id="{node["id"]}" {condition_attr} />\n'
    else:
        return ''

def generate_shape_xml(node):
    marker_visible_attr = 'isMarkerVisible="true"' if node.get('type') in ['xor', 'loop'] else ''
    return f'''<bpmndi:BPMNShape id="Shape_{node['id']}" bpmnElement="{node['id']}" {marker_visible_attr}>
    <dc:Bounds x="{node['x']}" y="{node['y']}" width="{node['width']}" height="{node['height']}" />
</bpmndi:BPMNShape>\n'''

def generate_sequence_flows_bpmn(sequence_flows):
    sequence_flows_xml = ''
    bpmn_edges_xml = ''

    for flow in sequence_flows:
        name_attr = f' name="{flow["name"]}"' if flow.get('name') else ''
        sequence_flow_xml = f'<bpmn:sequenceFlow id="Flow_{flow["from"]["id"]}_{flow["to"]["id"]}" sourceRef="{flow["from"]["id"]}" targetRef="{flow["to"]["id"]}"{name_attr} />\n'
        sequence_flows_xml += sequence_flow_xml

        waypoints_xml = ''
        waypoints_xml += f'<di:waypoint x="{flow["point1"]["x"]}" y="{flow["point1"]["y"]}" />'
        if flow.get('point3'):
            waypoints_xml += f'<di:waypoint x="{flow["point3"]["x"]}" y="{flow["point3"]["y"]}" />'
        if flow.get('point4'):
            waypoints_xml += f'<di:waypoint x="{flow["point4"]["x"]}" y="{flow["point4"]["y"]}" />'
        waypoints_xml += f'<di:waypoint x="{flow["point2"]["x"]}" y="{flow["point2"]["y"]}" />'

        bpmn_edge_xml = f'''
<bpmndi:BPMNEdge id="Flow_{flow["from"]["id"]}_{flow["to"]["id"]}_di" bpmnElement="Flow_{flow["from"]["id"]}_{flow["to"]["id"]}">
    {waypoints_xml}
    <bpmndi:BPMNLabel>
        <dc:Bounds x="{flow["labelX"]}" y="{flow["labelY"]}" width="40" height="15" />
    </bpmndi:BPMNLabel>
</bpmndi:BPMNEdge>\n'''
        bpmn_edges_xml += bpmn_edge_xml

    return sequence_flows_xml, bpmn_edges_xml

def convert_json_to_bpmn(json_data):
    start_event_xml = f'<bpmn:startEvent id="{json_data["startEvent"]["id"]}" name="{json_data["startEvent"]["name"]}"></bpmn:startEvent>\n'
    end_event_xml = f'<bpmn:endEvent id="{json_data["endEvent"]["id"]}" name="{json_data["endEvent"]["name"]}"></bpmn:endEvent>\n'

    start_event_shape_xml = f'''
<bpmndi:BPMNShape id="_BPMNShape_{json_data["startEvent"]["id"]}" bpmnElement="{json_data["startEvent"]["id"]}">
    <dc:Bounds x="{json_data["startEvent"]["x"]}" y="{json_data["startEvent"]["y"]}" width="{json_data["startEvent"]["width"]}" height="{json_data["startEvent"]["height"]}" />
    <bpmndi:BPMNLabel></bpmndi:BPMNLabel>
</bpmndi:BPMNShape>\n'''

    end_event_shape_xml = f'''
<bpmndi:BPMNShape id="_BPMNShape_{json_data["endEvent"]["id"]}" bpmnElement="{json_data["endEvent"]["id"]}">
    <dc:Bounds x="{json_data["endEvent"]["x"]}" y="{json_data["endEvent"]["y"]}" width="{json_data["endEvent"]["width"]}" height="{json_data["endEvent"]["height"]}" />
    <bpmndi:BPMNLabel></bpmndi:BPMNLabel>
</bpmndi:BPMNShape>\n'''

    diagram_xml, shapes_xml = generate_diagram_xml(json_data['process'])
    sequence_flows_xml, bpmn_edges_xml = generate_sequence_flows_bpmn(json_data['sequenceFlows'])

    bpmn_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
    xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
    xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
    xmlns:modeler="http://camunda.org/schema/modeler/1.0"
    id="Definitions_1q4o25e"
    targetNamespace="http://bpmn.io/schema/bpmn"
    exporter="Camunda Modeler"
    exporterVersion="5.20.0"
    modeler:executionPlatform="Camunda Cloud"
    modeler:executionPlatformVersion="8.4.0">
  <bpmn:process id="Process_1">
    {start_event_xml}
    {diagram_xml}
    {end_event_xml}
    {sequence_flows_xml}
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
    {start_event_shape_xml}
    {shapes_xml}
    {end_event_shape_xml}
    {bpmn_edges_xml}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>'''

    return bpmn_xml

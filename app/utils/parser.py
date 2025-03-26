import copy
import json
from .bpmn_utils import add_joining_gateways, add_empty_branches, add_ids, add_sequence_flows
from .coordinates_calculator import calculate_diagram_coordinates, calculate_sequence_flow_points
from .json_bpmn_converter import convert_json_to_bpmn

def parser_to_bpmn(json_data):
    try:
        json_bpmn = copy.deepcopy(json_data)
        
        # Prepare JSON data
        add_joining_gateways(json_bpmn)
        add_empty_branches(json_bpmn)
        add_ids(json_bpmn)
        calculate_diagram_coordinates(json_bpmn)
        add_sequence_flows(json_bpmn)
        calculate_sequence_flow_points(json_bpmn)

        # Convert JSON to BPMN XML
        bpmn_xml = convert_json_to_bpmn(json_bpmn)

        # Return the BPMN XML
        return bpmn_xml
    except Exception as error:
        print('Error generating BPMN XML:', error)
        import traceback
        traceback.print_exc()
        return None

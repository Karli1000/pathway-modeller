import os
import sys
import json
from flask import Flask, request, jsonify, render_template, session
from flask_session import Session
import xml.etree.ElementTree as ET
import atexit

from utils.parser import parser_to_bpmn
from utils.api_openai_assistant import (
    create_thread,
    append_user_message,
    run_thread,
    create_bpmn_assistant,
    upload_pdf_to_file_search
)

app = Flask(__name__)

app.config["SECRET_KEY"] = "beliebiges_geheimes_passwort"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROMPTS_FUNCTIONS_DIR = os.path.join(BASE_DIR, 'prompts_functions')

system_prompt_file = os.path.join(PROMPTS_FUNCTIONS_DIR, 'system_prompt_openai_assistant.txt')
modify_prompt_file = os.path.join(PROMPTS_FUNCTIONS_DIR, 'modify_prompt_openai_assistant.txt')
function_definition_file = os.path.join(PROMPTS_FUNCTIONS_DIR, 'function_definition_openai_assistant.json')

assistant_id = None 
thread_id = None
vector_store_id = None

def shrink_bpmn_xml(xml_str: str) -> str:
    if not xml_str.strip():
        return xml_str

    # remove <?xml ...?> declaration
    lines = xml_str.splitlines()
    lines_without_xml_decl = [
        ln for ln in lines if not ln.strip().startswith('<?xml')
    ]
    cleaned_input = "\n".join(lines_without_xml_decl).strip()

    try:
        root = ET.fromstring(cleaned_input)

        process_node = root.find(".//{*}process")
        if process_node is None:
            return cleaned_input

        # only serialize <bpmn:process>
        minimal_xml_bytes = ET.tostring(
            process_node, 
            encoding='utf-8', 
            method='xml', 
            short_empty_elements=False
        )
        print(minimal_xml_bytes.decode('utf-8'))
        return minimal_xml_bytes.decode('utf-8')

    except ET.ParseError:
        return xml_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # payload is json with following parameter:
    # thread_id: threadId
    # message: userMessage
    # currentBpmnXml
    global thread_id, assistant_id

    if 'api_key' not in session:
        return jsonify({"error": "API-Key fehlt!"}), 400
    
    if not assistant_id:
        return jsonify({"error": "Assistant noch nicht initialisiert!"}), 400
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    current_bpmn_xml = data.get('currentBpmnXml', '')

    if not thread_id:
        thread_id = create_thread(user_message)
    else:
        with open(modify_prompt_file, 'r', encoding='utf-8') as f:
            modify_prompt_text = f.read()
        combined_user_message = f"{modify_prompt_text}\n\n{user_message}"
        append_user_message(thread_id, combined_user_message, shrink_bpmn_xml(current_bpmn_xml))

    json_response, message = run_thread(thread_id, assistant_id)
    bpmn_xml = parser_to_bpmn(json_response)

    return jsonify({
        "thread_id": thread_id,
        "bpmn_xml": bpmn_xml if bpmn_xml else "",
        "message": message
    })

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    global vector_store_id, assistant_id

    if 'api_key' not in session:
        return jsonify({"error": "API-Key fehlt!"}), 400
    
    if not assistant_id:
        return jsonify({"error": "Assistant noch nicht initialisiert!"}), 400
    
    uploaded_file = request.files.get('pdfFile')
    if not uploaded_file:
        return jsonify({"error": "No file uploaded."}), 400

    try:
        vector_store_id = upload_pdf_to_file_search(uploaded_file, assistant_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "PDF added to storage."})

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    data = request.get_json()
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({"error": "API-Key fehlt!"}), 400

    session['api_key'] = api_key
    return jsonify({"message": "API-Key gesetzt."}), 200

@app.route('/initialize_assistant', methods=['POST'])
def initialize_assistant():
    global assistant_id
    
    if 'api_key' not in session:
        return jsonify({"error": "API-Key fehlt!"}), 400

    with open(system_prompt_file, 'r', encoding='utf-8') as f:
        system_prompt_openai = f.read()

    with open(function_definition_file, 'r', encoding='utf-8') as f:
        function_definition_openai = json.load(f)

    assistant_id = create_bpmn_assistant(system_prompt_openai, function_definition_openai)

    return jsonify({"message": "Assistant initialisiert!"}), 200

@app.route('/reset_session', methods=['POST'])
def reset_session():
    global thread_id, vector_store_id, assistant_id
    import openai
    
    if 'api_key' not in session:
        return jsonify({"error": "API-Key fehlt!"}), 400

    openai.api_key = session['api_key']

    if thread_id:
        try:
            openai.beta.threads.delete(thread_id)
            print(f"Thread {thread_id} gelöscht.")
        except Exception as e:
            print(f"Thread {thread_id} konnte nicht gelöscht werden: {e}")
        thread_id = None

    if vector_store_id:
        try:
            openai.beta.vector_stores.delete(vector_store_id)
            print(f"Vector Store {vector_store_id} gelöscht.")
        except Exception as e:
            print(f"Vector Store {vector_store_id} konnte nicht gelöscht werden: {e}")
        vector_store_id = None

    if assistant_id:
        try:
            openai.beta.assistants.delete(assistant_id)
            print(f"Assistant {assistant_id} gelöscht.")
        except Exception as e:
            print(f"Assistant {assistant_id} konnte nicht gelöscht werden: {e}")
        assistant_id = None

    with open(system_prompt_file, 'r', encoding='utf-8') as f:
        system_prompt_openai = f.read()

    with open(function_definition_file, 'r', encoding='utf-8') as f:
        function_definition_openai = json.load(f)

    assistant_id = create_bpmn_assistant(system_prompt_openai, function_definition_openai)

    return jsonify({"message": "Session vollständig zurückgesetzt."}), 200

def cleanup():
    import openai
    
    if vector_store_id:
        try:
            openai.beta.vector_stores.delete(vector_store_id)
            print(f"Deleted vector store {vector_store_id}")
        except Exception as e:
            print(f"Could not delete vector store {vector_store_id}: {e}")
    
    if thread_id:
        try:
            openai.beta.threads.delete(thread_id)
            print(f"Deleted thread {thread_id}")
        except Exception as e:
            print(f"Could not delete thread {thread_id}: {e}")

    if assistant_id:
        try:
            openai.beta.assistants.delete(assistant_id)
            print(f"Deleted assistant {assistant_id}")
        except Exception as e:
            print(f"Could not delete assistant {assistant_id}: {e}")

atexit.register(cleanup)

if __name__ == '__main__':

    with open(system_prompt_file, 'r', encoding='utf-8') as f:
        system_prompt_openai = f.read()
    
    with open(modify_prompt_file, 'r', encoding='utf-8') as f:
        modify_prompt_text = f.read()

    with open(function_definition_file, 'r', encoding='utf-8') as f:
        function_definition_openai = json.load(f)

    app.run(debug=False)
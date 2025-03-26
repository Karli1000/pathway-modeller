import openai
import json
import io
from flask import session

def get_openai_client():
    api_key = session.get('api_key')
    if not api_key:
        raise Exception("Kein API-Key gesetzt!")
    openai.api_key = api_key
    return openai

def create_bpmn_assistant(system_prompt, function_definition):

    tools = [
        function_definition,
    ]

    #tools = [
    #    function_definition,
    #    {"type": "file_search"}
    #]

    client = get_openai_client()

    assistant = openai.beta.assistants.create(
        name="BPMN Assistant",
        model="gpt-4o", # gpt-4o, o1, o3-mini
        instructions=system_prompt,
        tools=tools
    )

    return assistant.id

def upload_pdf_to_file_search(pdf_file, assistant_id):

    file_stream = io.BytesIO(pdf_file.read())
    file_stream.name = pdf_file.filename or "clinical_practice_guideline.pdf"

    vector_store = openai.beta.vector_stores.create(name="clinical practice guideline store")

    file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id,
        files=[file_stream]
    )

    # add vector store to assistant
    openai.beta.assistants.update(
        assistant_id=assistant_id,
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id]
            }
        }
    )
    print("Assistant updated to use vector store:", vector_store.id)
    return vector_store.id


def create_thread(initial_user_message: str):
    thread = openai.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": initial_user_message
            }
        ]
    )
    return thread.id

def handle_requires_action(thread_id, run_id, run_state):

    tool_call = run_state.required_action.submit_tool_outputs.tool_calls[0]
    name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    print("Waiting for custom Function:", name)
    print("Function arguments:")
    print(arguments)

    # inform assistant that function has been executed and he can answer
    openai.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run_id,
        tool_outputs=[{
            "tool_call_id": tool_call.id,
            "output": "done"
        }]
    )

    return arguments


def run_thread(thread_id, assistant_id):

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    run_id = run.id

    while True:
        run_state = openai.beta.threads.runs.retrieve(thread_id=thread_id,run_id=run_id)
        status = run_state.status
        print("Current run status:", status)

        if status == "requires_action":
            json = handle_requires_action(thread_id, run_id, run_state)
            continue

        if status in ["completed"]:
            print("completed")
            break

        if status in ["failed", "incomplete", "cancelled"]:
            print("failed, incomplete or cancelled")
            print("Run state details:", run_state)
            break
        
        import time
        time.sleep(5)
        
    thread_messages = openai.beta.threads.messages.list(thread_id)
    #print(thread_messages.data)
    # first message in thread data is the latest one
    message = next(
        m.content[0].text.value
        for m in thread_messages.data
        if m.role == 'assistant'
    )
    print(json)
    print(message)
    return json, message



def append_user_message(thread_id, user_message: str, bpmn_xml: str = None):

    msg_obj = {
        "role": "user",
        "content": user_message
    }

    if bpmn_xml:
        msg_obj["content"] += f"\n\nAktuelles BPMN:\n{bpmn_xml}"

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        **msg_obj
    )






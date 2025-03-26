/*******************************************
 * global variables and dom elements
 *******************************************/

const bpmnModeler = new BpmnJS({ container: '#canvas' });

const apiKeyField = document.getElementById('api-key-field');
const saveApiKeyButton = document.getElementById('save-api-key-button');

let threadId = null;

let chatHistory = [];

let currentBpmnXml = "";

const elements = {
  chatMessages:   document.getElementById('chat-messages'),
  chatInputField: document.getElementById('chat-input-field'),
  sendButton:     document.getElementById('send-button'),
  loadPdfButton:  document.getElementById('loadPdfButton'),
  clearButton:    document.getElementById('clearButton'),
  importButton:   document.getElementById('importButton'),
  exportButton:   document.getElementById('exportButton'),
  bpmnImportFile: document.getElementById('bpmnImportFile')
};

/*******************************************
 * functions
 *******************************************/

/**
 * add new message to chat and scroll down.
 * @param {string} text - message text
 * @param {('user'|'system')} from - sender of the message
 */
function addChatMessage(text, from = 'user') {
  chatHistory.push({ from, text });

  const msgDiv = document.createElement('div');
  msgDiv.classList.add('chat-message');

  const senderLabel = (from === 'user') ? 'Du' : 'BPMN-Assistent';
  msgDiv.innerHTML = `<strong>${senderLabel}:</strong> ${text}`;

  elements.chatMessages.appendChild(msgDiv);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

/**
 * load a BPMN diagram into the modeler and save the XML.
 * @param {string} xml - BPMN XML String
 */
async function loadBpmnXml(xml) {
  try {
    await bpmnModeler.importXML(xml);
    currentBpmnXml = xml;
  } catch (err) {
    console.error('Fehler beim Laden des BPMN XML:', err);
    addChatMessage('Fehler beim Laden des BPMN XML!', 'system');
  }
}

async function diffAndHighlightBpmn(oldXml, newXml) {
  const moddle = new BpmnModdle();

  const { rootElement: definitionsOld } = await moddle.fromXML(oldXml);

  const { rootElement: definitionsNew } = await moddle.fromXML(newXml);

  const changes = BpmnJsDiffer.diff(definitionsOld, definitionsNew);

  // changes._changed, changes._added, changes._removed, changes._layoutChanged
  // console.log(changes);

  await bpmnModeler.importXML(newXml);
  currentBpmnXml = newXml;

  const elementRegistry = bpmnModeler.get('elementRegistry');
  const modeling = bpmnModeler.get('modeling');

  const changedIds = Object.keys(changes._changed || {});
  const addedIds = Object.keys(changes._added || {});

  const highlightIds = [...changedIds, ...addedIds];

  highlightIds.forEach(id => {
    const shape = elementRegistry.get(id);
    if (shape) {
      // setze Farbe
      modeling.setColor(shape, {
        stroke: 'orange',
        fill: 'yellow'
      });
    }
  });

  // b) remove elements (`changes._removed`)
  const removedIds = Object.keys(changes._removed || {});
  if (removedIds.length) {
    console.log("Removed: ", removedIds.join(", "));
  }
}

saveApiKeyButton.addEventListener('click', async () => {
    const apiKey = apiKeyField.value.trim();
    if (!apiKey) {
      alert('Bitte gib einen API-Key ein.');
      return;
    }
    
    const response = await fetch('/set_api_key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });
  
    if (response.ok) {
      const initResponse = await fetch('/initialize_assistant', { method: 'POST' });
      if (initResponse.ok) {
        alert('API-Key gespeichert und Assistant initialisiert!');
      } else {
        alert('Fehler bei der Initialisierung des Assistants.');
      }
    } else {
      alert('Fehler beim Speichern des API-Keys.');
    }
  });
  

/*******************************************
 * Event-Listener
 *******************************************/

// initial Message
document.addEventListener('DOMContentLoaded', () => {
  const initialMessage = 
    "Ich bin ein Assistent für die Modellierung medizinischer Leitlinien.\n" +
    "Du kannst die Modellierung über folgende Möglichkeiten beginnen:\n" +
    "1. Über Load PDF kannst du die Leitlinie direkt aus der PDF laden.\n" +
    "2. Über Import kannst du eine bpmn Datei laden, an der du weiterarbeiten möchtest.\n" +
    "3. Du kannst mir auch im Chat beschreiben, was du modelliert haben möchtest.\n" +
    "4. Du kannst auch erst etwas händisch modellieren und mich später befragen oder Änderungswünsche formulieren.";

  addChatMessage(initialMessage, 'system');
});

// by pressing Enter button click
elements.chatInputField.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    elements.sendButton.click();
  }
});

// click send
elements.sendButton.addEventListener('click', async () => {
  const userMessage = elements.chatInputField.value.trim();
  if (!userMessage) return;

  // show message in chat
  addChatMessage(userMessage, 'user');
  elements.chatInputField.value = '';

  try {
    // Request-Payload
    const payload = {
      thread_id: threadId,
      message: userMessage,
      currentBpmnXml
    };

    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json();
      addChatMessage(`Fehler: ${errorData.error || 'Unbekannter Fehler'}`, 'system');
      return;
    }

    const data = await response.json();
    const { thread_id, bpmn_xml, message } = data;

    // thread_id acutalize
    if (thread_id) {
      threadId = thread_id;
    }
    addChatMessage(message, 'system');
    addChatMessage('Wird gerendert...', 'system');

    // if bpmn_xml is available
    if (bpmn_xml) {
      const oldXml = currentBpmnXml || '<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions><bpmn:process id="empty"/></bpmn:definitions>';
      await diffAndHighlightBpmn(oldXml, bpmn_xml);
    }
  } catch (err) {
    console.error(err);
    addChatMessage('Netzwerkfehler oder Server nicht erreichbar!', 'system');
  }
});

// load pdf
elements.loadPdfButton.addEventListener("click", () => {
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = ".pdf";
  fileInput.onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append("pdfFile", file);

      const response = await fetch("/upload_pdf", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        addChatMessage(`Fehler beim PDF-Upload: ${errData.error}`, "system");
        return;
      }
      const data = await response.json();
      addChatMessage(data.message, "system");
    } catch (err) {
      console.error(err);
      addChatMessage("Fehler beim Upload der PDF-Datei!", "system");
    }
  };
  fileInput.click();
});


// clear button
elements.clearButton.addEventListener('click', async () => {
    elements.chatMessages.innerHTML = '';
    chatHistory = [];
    currentBpmnXml = '';
  
    // backend call to reset thread and vector store
    const response = await fetch('/reset_session', { method: 'POST' });
    if (response.ok) {
      addChatMessage('Session vollständig zurückgesetzt.', 'system');
    } else {
      addChatMessage('Fehler beim Zurücksetzen der Session!', 'system');
    }
  
    // create empty diagram
    await bpmnModeler.createDiagram();
  });

// click import
elements.importButton.addEventListener('click', () => {
  elements.bpmnImportFile.click();
});

// load files from file selection field (BPMN)
elements.bpmnImportFile.addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const xmlString = e.target.result;
    await loadBpmnXml(xmlString);
    addChatMessage('BPMN-Datei erfolgreich importiert.', 'system');
  };
  reader.readAsText(file);

  // Reset
  event.target.value = '';
});

// click export
elements.exportButton.addEventListener('click', async () => {
  try {
    const { xml } = await bpmnModeler.saveXML({ format: true });
    const blob = new Blob([xml], { type: 'text/xml' });
    const url = URL.createObjectURL(blob);

    const downloadLink = document.createElement('a');
    downloadLink.href = url;
    downloadLink.download = 'diagram.bpmn';
    document.body.appendChild(downloadLink);
    downloadLink.click();

    document.body.removeChild(downloadLink);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Fehler beim Exportieren des BPMN-Diagramms:', err);
    addChatMessage('Fehler beim Exportieren des BPMN-Diagramms!', 'system');
  }
});

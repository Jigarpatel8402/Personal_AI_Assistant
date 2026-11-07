const app = document.getElementById("app");
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const send = document.getElementById("send");
const mic = document.getElementById("mic");

let started = false;
let queue = [];
let busy = false;
let micActive = false
let micTimer = null;

// add a message to the chat
function addMessage(text, sender) {
  if (!started) {
    started = true;
    app.classList.add("started");
  }
  const msg = document.createElement("div");
  msg.className = `msg ${sender}`;
  msg.textContent = text;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

// take text to add in chat
function pollTextPython()
{
  window.pywebview.api.print_text().then(
      data => {
        for (const msg of data.messages)
        {
          addMessage(msg.text, msg.source);
        }
      }
  );
}

document.addEventListener("DOMContentLoaded", () => {
  setInterval(pollTextPython, 50);
});

// queue for the query send to the AI
async function processQueue()
{
  if (busy || queue.length === 0)
    return;

  busy = true;
  const text =  queue.shift()
  await window.pywebview.api.receive_text(text);
  busy = false;
  processQueue();
}

// Handle send query
function handleSend()
{
  const text = input.value.trim();
  if (!text) return;

  if (!started) {
    started = true;
    app.classList.add("started");
  }

  addMessage(text, "user");
  queue.push(text);
  processQueue();
  input.value = "";
}

// send button behavior able/disable
if (!input.value.trim()) {
  send.classList.add("disabled");
} else {
  send.classList.remove("disabled");
}

// on click send
send.onclick = handleSend;

// enter press event
input.addEventListener("keydown", e => {
  if (e.key === "Enter") handleSend();
});

mic.addEventListener("mousedown", async () => {
  if (micActive) return;
  micActive = true;

  mic.classList.add("listening");

  try {
    await window.pywebview.api.mic_start()
  }
  catch (e) {
    addMessage("Mic Error", 'warning');
    return;
  }

  micTimer = setTimeout(() => {
    if (micActive) {
      addMessage("Listening...", "mic")
    }
  }, 500);
});

mic.addEventListener("mouseup", async () => {
  if (!micActive) return;
  micActive = false;

  mic.classList.remove("listening");

  try {
    const text = await window.pywebview.api.mic_stop();

    if (text && text.trim()) {
      addMessage(text, "user");
      queue.push(text);
      processQueue();
    }
  }
  catch (e) {
    addMessage("Mic Error", 'warning');
  }
});

mic.addEventListener("mouseleave", () => {
  if (micActive) mic.dispatchEvent(new MouseEvent("mouseup"));
});

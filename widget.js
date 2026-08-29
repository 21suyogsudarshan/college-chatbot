(function() {
  const styles = `
    #cb-bubble { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: #004085; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.25); z-index: 9999; font-size: 26px; }
    #cb-window { position: fixed; bottom: 90px; right: 20px; width: 380px; height: 530px; background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; overflow: hidden; z-index: 9999; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; border: 1px solid #e2e8f0; }
    #cb-header { background: #004085; color: #fff; padding: 14px 18px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; }
    #cb-header span { font-size: 11px; background: #2563eb; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
    #cb-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background: #f8fafc; }
    .cb-msg { padding: 10px 14px; border-radius: 12px; max-width: 85%; line-height: 1.5; word-wrap: break-word; }
    .cb-msg p { margin: 0 0 8px 0; }
    .cb-msg p:last-child { margin-bottom: 0; }
    .cb-msg ul { margin: 4px 0 8px 18px; padding: 0; }
    .cb-msg li { margin-bottom: 4px; }
    .cb-user { background: #004085; color: #fff; align-self: flex-end; border-bottom-right-radius: 3px; }
    .cb-bot { background: #fff; color: #1e293b; align-self: flex-start; border-bottom-left-radius: 3px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border: 1px solid #edf2f7; }
    #cb-input-area { display: flex; border-top: 1px solid #e2e8f0; background: #fff; padding: 10px; }
    #cb-input { flex: 1; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; outline: none; font-size: 14px; }
    #cb-input:focus { border-color: #004085; }
    #cb-send { background: #004085; color: #fff; border: none; border-radius: 8px; padding: 0 18px; margin-left: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
  `;
  const styleSheet = document.createElement("style");
  styleSheet.innerText = styles;
  document.head.appendChild(styleSheet);

  const container = document.createElement("div");
  container.innerHTML = `
    <div id="cb-bubble">💬</div>
    <div id="cb-window">
      <div id="cb-header">
        ABV-IIITM Assistant
        <span>Official Support</span>
      </div>
      <div id="cb-messages">
        <div class="cb-msg cb-bot">Hello! How can I help you with admissions, course details, fees, or campus guidelines?</div>
      </div>
      <div id="cb-input-area">
        <input type="text" id="cb-input" placeholder="Ask a question..." />
        <button id="cb-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  const bubble = document.getElementById("cb-bubble");
  const win = document.getElementById("cb-window");
  const input = document.getElementById("cb-input");
  const sendBtn = document.getElementById("cb-send");
  const messages = document.getElementById("cb-messages");

  bubble.onclick = () => {
    win.style.display = win.style.display === "flex" ? "none" : "flex";
    if (win.style.display === "flex") input.focus();
  };

  function formatText(text) {
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^\s*\*\s+(.*)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
      .replace(/\n\n+/g, '</p><p>')
      .replace(/\n/g, '<br/>');
    return `<p>${formatted}</p>`;
  }

  async function handleSend() {
    const text = input.value.trim();
    if (!text) return;

    messages.innerHTML += `<div class="cb-msg cb-user">${text}</div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    const loadingId = "bot-loading-" + Date.now();
    messages.innerHTML += `<div id="${loadingId}" class="cb-msg cb-bot" style="color: #64748b;">Thinking...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text })
      });
      const data = await res.json();
      const loadingElem = document.getElementById(loadingId);
      if (loadingElem) loadingElem.outerHTML = `<div class="cb-msg cb-bot">${formatText(data.reply)}</div>`;
    } catch (err) {
      const loadingElem = document.getElementById(loadingId);
      if (loadingElem) loadingElem.outerHTML = `<div class="cb-msg cb-bot" style="color:#dc2626;">Could not connect to the campus server.</div>`;
    }
    messages.scrollTop = messages.scrollHeight;
  }

  sendBtn.onclick = handleSend;
  input.onkeypress = (e) => { if (e.key === "Enter") handleSend(); };
})();

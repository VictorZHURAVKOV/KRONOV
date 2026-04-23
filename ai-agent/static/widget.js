/**
 * КРОНОВЪ Chat Widget
 * Подключение на сайте:
 *   <script src="https://agent.kronov.by/widget.js" data-api="https://agent.kronov.by"></script>
 *
 * Одиночный IIFE, внедряет shadow-DOM чтобы не конфликтовать со стилями сайта.
 */
(function () {
  'use strict';

  const script = document.currentScript;
  const API = (script && script.dataset.api) || window.location.origin;
  const STORAGE_KEY = 'kronov_chat_session';

  // === Корневой host, Shadow DOM ===
  const host = document.createElement('div');
  host.id = 'kronov-chat-root';
  host.style.cssText = 'position:fixed;bottom:0;right:0;z-index:10050;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;';
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: 'open' });

  // === Стили ===
  const style = document.createElement('style');
  style.textContent = `
    :host { all: initial; }
    * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

    .launcher {
      position: fixed; right: 24px; bottom: 24px;
      width: 62px; height: 62px; border-radius: 50%;
      background: #7A2E38; color: #F2EBE0;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; border: none;
      box-shadow: 0 8px 24px rgba(30,20,16,.35);
      transition: transform .2s ease, box-shadow .2s ease;
      z-index: 10050;
    }
    .launcher:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(30,20,16,.45); }
    .launcher svg { width: 28px; height: 28px; }
    .launcher .unread {
      position: absolute; top: -4px; right: -4px;
      background: #B8965A; color: #1E1410;
      font-size: 11px; font-weight: 700;
      min-width: 20px; height: 20px; border-radius: 10px;
      padding: 0 6px; display: flex; align-items: center; justify-content: center;
    }

    .panel {
      position: fixed; right: 24px; bottom: 24px;
      width: 380px; max-width: calc(100vw - 32px);
      height: 620px; max-height: calc(100vh - 40px);
      background: #F2EBE0; border-radius: 14px;
      box-shadow: 0 16px 48px rgba(30,20,16,.35);
      display: none; flex-direction: column; overflow: hidden;
      border: 1px solid rgba(184, 150, 90, .25);
    }
    .panel.open { display: flex; }

    .header {
      background: #1E1410; color: #D4B896;
      padding: 16px 18px; display: flex; align-items: center; gap: 12px;
      border-bottom: 1px solid rgba(184, 150, 90, .3);
    }
    .avatar {
      width: 44px; height: 44px; border-radius: 50%;
      background: linear-gradient(135deg, #7A2E38, #B8965A);
      display: flex; align-items: center; justify-content: center;
      color: #F2EBE0; font-weight: 700; font-size: 18px;
      font-family: "Playfair Display", Georgia, serif;
    }
    .header-text { flex: 1; }
    .header-name {
      font-family: "Playfair Display", Georgia, serif;
      font-size: 17px; font-weight: 600; letter-spacing: .5px;
    }
    .header-sub { font-size: 11px; color: #8B6040; text-transform: uppercase; letter-spacing: 1.2px; margin-top: 2px; }
    .header-status {
      display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: #6BCB7A; margin-right: 6px;
      box-shadow: 0 0 6px rgba(107, 203, 122, .8);
    }
    .close-btn {
      background: transparent; border: 0; color: #D4B896;
      cursor: pointer; padding: 6px; border-radius: 6px;
    }
    .close-btn:hover { background: rgba(212,184,150,.1); }

    .messages {
      flex: 1; overflow-y: auto; padding: 16px;
      background: #F2EBE0;
      display: flex; flex-direction: column; gap: 10px;
    }
    .messages::-webkit-scrollbar { width: 6px; }
    .messages::-webkit-scrollbar-thumb { background: rgba(92,58,40,.25); border-radius: 3px; }

    .msg {
      max-width: 82%; padding: 10px 14px; border-radius: 12px;
      font-size: 14px; line-height: 1.45; color: #2A1C0E;
      white-space: pre-wrap; word-wrap: break-word;
      animation: fadeIn .25s ease;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

    .msg.user {
      align-self: flex-end;
      background: #7A2E38; color: #F2EBE0;
      border-bottom-right-radius: 4px;
    }
    .msg.assistant {
      align-self: flex-start;
      background: #FFFFFF;
      border: 1px solid rgba(184,150,90,.25);
      border-bottom-left-radius: 4px;
    }
    .msg a { color: #7A2E38; font-weight: 600; }
    .msg.user a { color: #FFFFFF; text-decoration: underline; }

    .msg.system {
      align-self: center; font-size: 12px; color: #8B6040;
      padding: 4px 10px; background: rgba(212,184,150,.2);
      border-radius: 8px; font-style: italic;
    }

    .typing {
      align-self: flex-start;
      padding: 12px 16px; background: #FFFFFF;
      border: 1px solid rgba(184,150,90,.25);
      border-radius: 12px; border-bottom-left-radius: 4px;
      display: flex; gap: 4px;
    }
    .typing span {
      width: 7px; height: 7px; border-radius: 50%;
      background: #8B6040; opacity: .4;
      animation: typing 1.2s infinite ease-in-out;
    }
    .typing span:nth-child(2) { animation-delay: .15s; }
    .typing span:nth-child(3) { animation-delay: .3s; }
    @keyframes typing { 0%, 60%, 100% { transform: translateY(0); opacity: .4; } 30% { transform: translateY(-4px); opacity: 1; } }

    .input-bar {
      border-top: 1px solid rgba(184,150,90,.25);
      padding: 12px; background: #FFFFFF;
      display: flex; gap: 8px; align-items: flex-end;
    }
    textarea {
      flex: 1; resize: none; border: 1px solid rgba(184,150,90,.3);
      border-radius: 10px; padding: 10px 12px; font-size: 14px;
      font-family: inherit; color: #2A1C0E; background: #FFFCF6;
      min-height: 40px; max-height: 120px; outline: none;
      transition: border-color .15s;
    }
    textarea:focus { border-color: #7A2E38; }
    .send-btn {
      background: #7A2E38; color: #F2EBE0; border: 0;
      width: 40px; height: 40px; border-radius: 10px;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .send-btn:hover { background: #5C2229; }
    .send-btn:disabled { opacity: .4; cursor: not-allowed; }

    .footer-note {
      font-size: 10px; color: #8B6040; text-align: center;
      padding: 4px 12px 8px; background: #FFFFFF;
      letter-spacing: .5px;
    }

    @media (max-width: 480px) {
      .panel { right: 0; bottom: 0; width: 100vw; height: 100vh; max-height: 100vh; border-radius: 0; }
      .launcher { right: 16px; bottom: 92px; }
    }
  `;
  root.appendChild(style);

  // === Разметка ===
  const launcher = document.createElement('button');
  launcher.className = 'launcher';
  launcher.setAttribute('aria-label', 'Открыть чат');
  launcher.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
  `;
  root.appendChild(launcher);

  const panel = document.createElement('div');
  panel.className = 'panel';
  panel.innerHTML = `
    <div class="header">
      <div class="avatar">А</div>
      <div class="header-text">
        <div class="header-name">Алёна · КРОНОВЪ</div>
        <div class="header-sub"><span class="header-status"></span>менеджер · на связи</div>
      </div>
      <button class="close-btn" aria-label="Свернуть">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
    </div>
    <div class="messages"></div>
    <div class="input-bar">
      <textarea placeholder="Напишите сообщение..." rows="1"></textarea>
      <button class="send-btn" aria-label="Отправить">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
      </button>
    </div>
    <div class="footer-note">КРОНОВЪ · архитектурная мастерская</div>
  `;
  root.appendChild(panel);

  // === Элементы ===
  const messagesEl = panel.querySelector('.messages');
  const textarea = panel.querySelector('textarea');
  const sendBtn = panel.querySelector('.send-btn');
  const closeBtn = panel.querySelector('.close-btn');

  // === Состояние ===
  let sessionId = localStorage.getItem(STORAGE_KEY) || null;
  let sending = false;
  let firstOpen = true;

  // === Функции UI ===
  function renderMessage(role, text, options = {}) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    // Очень базовая поддержка ссылок
    const safe = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');
    div.innerHTML = safe;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    div.id = 'typing-indicator';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function hideTyping() {
    const t = messagesEl.querySelector('#typing-indicator');
    if (t) t.remove();
  }

  function openPanel() {
    panel.classList.add('open');
    launcher.style.display = 'none';
    if (firstOpen) {
      firstOpen = false;
      renderMessage('assistant', 'Здравствуйте. Меня зовут Алёна, я менеджер КРОНОВЪ. Помогу подобрать беседку, посчитать стоимость, оформить заказ. Напишите коротко, что вас интересует.');
    }
    setTimeout(() => textarea.focus(), 120);
  }
  function closePanel() {
    panel.classList.remove('open');
    launcher.style.display = 'flex';
  }

  launcher.addEventListener('click', openPanel);
  closeBtn.addEventListener('click', closePanel);

  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  });
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  sendBtn.addEventListener('click', send);

  // === Отправка ===
  async function send() {
    const text = textarea.value.trim();
    if (!text || sending) return;
    sending = true;
    sendBtn.disabled = true;

    renderMessage('user', text);
    textarea.value = '';
    textarea.style.height = 'auto';
    showTyping();

    try {
      const res = await fetch(API + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          channel: 'site',
          context: window.__KRONOV_CHAT_CONTEXT__ || null,
        }),
      });

      if (!res.ok || !res.body) throw new Error('Network error');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantMsgEl = null;
      let currentAssistantText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Разбор SSE: events разделены \n\n
        const events = buffer.split('\n\n');
        buffer = events.pop(); // хвост

        for (const evBlock of events) {
          if (!evBlock.trim()) continue;
          let eventType = 'message';
          let dataLine = '';
          for (const line of evBlock.split('\n')) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLine = line.slice(5).trim();
          }
          if (!dataLine) continue;
          let data;
          try { data = JSON.parse(dataLine); } catch { continue; }

          if (eventType === 'session') {
            sessionId = data.session_id;
            localStorage.setItem(STORAGE_KEY, sessionId);
          } else if (eventType === 'text_delta') {
            if (!assistantMsgEl) {
              hideTyping();
              assistantMsgEl = renderMessage('assistant', '');
            }
            currentAssistantText += data.text;
            assistantMsgEl.innerHTML = currentAssistantText
              .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
              .replace(/\n/g, '<br>');
            messagesEl.scrollTop = messagesEl.scrollHeight;
          } else if (eventType === 'tool_use') {
            // тихая отметка работы инструмента
            if (data.name === 'calculate_price') {
              if (!assistantMsgEl) showTyping();
            }
          } else if (eventType === 'done') {
            // ничего — текст уже отрендерен
          } else if (eventType === 'error') {
            hideTyping();
            renderMessage('system', 'Связь прервалась. Напишите ещё раз — я на месте.');
          }
        }
      }
      hideTyping();
    } catch (e) {
      hideTyping();
      renderMessage('system', 'Не получилось отправить. Проверьте интернет и напишите ещё раз.');
      console.error(e);
    } finally {
      sending = false;
      sendBtn.disabled = false;
      textarea.focus();
    }
  }

  // === Интеграция с формами сайта: при submit формы заявки — открываем чат с контекстом ===
  window.KronovChat = {
    open: openPanel,
    close: closePanel,
    send: (msg) => { textarea.value = msg; send(); },
    setContext: (ctx) => { window.__KRONOV_CHAT_CONTEXT__ = ctx; },
  };
})();

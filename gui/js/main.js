/* JARVIS AI UI. Works with (a) your current bridge.py (polling: print_text/receive_text),
   (b) a streaming backend (send_message + window.onEvent), (c) a built-in mock in a plain browser. */
const $ = s => document.querySelector(s);
const E = {app:$('#app'),main:$('#main'),thread:$('#thread'),chat:$('#chat'),input:$('#input'),send:$('#send'),
  mic:$('#mic'),listening:$('#listening'),history:$('#history'),title:$('#title'),jump:$('#jump'),health:$('#health'),toasts:$('#toasts')};
const S = {convs:[],active:null,gen:null,genConv:null,mic:'idle',pinned:true,release:false};
const nodes = new Map(), dead = new Set(), dirty = new Set();
const uid = () => Math.random().toString(36).slice(2, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ls = {get:k=>{try{return localStorage.getItem(k)}catch{return null}}, set:(k,v)=>{try{localStorage.setItem(k,v)}catch{}}};

/* ---------- Bridge ---------- */
const hasPy = () => !!(window.pywebview && window.pywebview.api);
const legacy = () => hasPy() && !window.pywebview.api.send_message;
function health(ok){ E.health.classList.toggle('down', !ok); }
async function call(name, ...args){
  try{
    if(!hasPy()) return await mock[name]?.(...args);
    const f = window.pywebview.api[name];
    return f ? await f(...args) : undefined;
  }catch(err){ health(false); throw err; }
}
const mock = {
  stopFlag:false,
  async load_conversations(){ return ls.get('jv_convs') || '[]'; },
  async save_conversations(j){ ls.set('jv_convs', j); },
  async stop_generation(){ mock.stopFlag = true; },
  async mic_start(){}, async mic_stop(){ await sleep(500); return "What's my battery level?"; },
  async send_message(p){
    mock.stopFlag = false;
    const text = ["Here is a **demo reply** streamed token by token.","","## What you get","- Markdown with lists and tables","- Safe HTML (sanitized)","","| Feature | Status |","|---|---|","| Streaming | Done |","| Code copy | Done |","","~~~python","def greet(name):","    return f'Hello, {name}'","~~~"].join("\n");
    (async()=>{
      window.onEvent({type:'message_start', id:p.id}); await sleep(700);
      for(let i=0;i<text.length && !mock.stopFlag;i+=4){ window.onEvent({type:'message_delta', id:p.id, text:text.slice(i,i+4)}); await sleep(18); }
      window.onEvent({type:'message_end', id:p.id});
    })();
  }
};

/* ---------- Helpers ---------- */
const conv = () => S.convs.find(c => c.id === S.active);
function findMsg(id){ for(const c of S.convs){ const m = c.messages.find(x => x.id === id); if(m) return {c, m}; } }
function toast(msg, err){
  const t = document.createElement('div'); t.className = 'toast' + (err ? ' err' : ''); t.textContent = msg;
  E.toasts.append(t); setTimeout(() => t.remove(), 3500);
}
let saveT; const persist = () => { clearTimeout(saveT); saveT = setTimeout(() => call('save_conversations', JSON.stringify(S.convs)).catch(()=>{}), 400); };
const toBottom = () => { E.chat.scrollTop = E.chat.scrollHeight; };

/* ---------- Rendering ---------- */
function enhance(body){
  body.querySelectorAll('pre').forEach(pre => {
    const lang = (pre.querySelector('code')?.className.match(/language-(\S+)/) || [])[1] || 'code';
    const w = document.createElement('div'); w.className = 'codeblock';
    w.innerHTML = '<div class="bar"><span></span><button type="button"><svg><use href="#i-copy"/></svg><b>Copy</b></button></div>';
    w.querySelector('span').textContent = lang;
    w.querySelector('button').onclick = async e => {
      try{ await navigator.clipboard.writeText(pre.textContent); }catch{}
      const b = e.currentTarget.querySelector('b'); b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 1500);
    };
    pre.replaceWith(w); w.append(pre);
  });
}
let raf = 0;
function paint(id){ dirty.add(id); raf = raf || requestAnimationFrame(flush); }
function flush(){
  raf = 0;
  for(const id of dirty){
    const n = nodes.get(id); if(!n) continue; const {m, body} = n;
    if(m.role === 'user') body.textContent = m.text;
    else if(m.error) body.textContent = m.text;
    else if(!m.text && S.gen === id) body.innerHTML = '<span class="dots"><i></i><i></i><i></i></span>';
    else { body.innerHTML = DOMPurify.sanitize(marked.parse(m.text || '')); enhance(body); }
    body.classList.toggle('cursor', S.gen === id && !!m.text);
  }
  dirty.clear(); if(S.pinned) toBottom();
}
function mkNode(m){
  const root = document.createElement('div'), body = document.createElement('div');
  root.className = 'msg ' + (m.role === 'user' ? 'user' : 'ai') + (m.error ? ' error' : ''); body.className = 'body';
  if(m.role === 'user') root.append(body);
  else { root.innerHTML = '<div class="avatar"><svg><use href="#i-hex"/></svg></div><div class="col"></div>'; root.querySelector('.col').append(body); }
  nodes.set(m.id, {root, body, m}); paint(m.id); return root;
}
function addNode(m){ E.thread.append(mkNode(m)); E.main.classList.remove('empty'); }
function refreshActions(){
  const c = conv(); if(!c) return;
  document.querySelectorAll('.actions').forEach(a => a.remove());
  const ais = c.messages.filter(m => m.role === 'ai' && S.gen !== m.id);
  ais.forEach((m, i) => {
    const col = nodes.get(m.id)?.root.querySelector('.col'); if(!col) return;
    const a = document.createElement('div'); a.className = 'actions';
    a.innerHTML = '<button class="icon-btn" aria-label="Copy" title="Copy"><svg><use href="#i-copy"/></svg></button>';
    a.firstChild.onclick = () => { navigator.clipboard?.writeText(m.text).catch(()=>{}); toast('Copied'); };
    if(m === c.messages[c.messages.length - 1]){
      const r = document.createElement('button'); r.className = 'icon-btn'; r.title = 'Regenerate'; r.setAttribute('aria-label','Regenerate');
      r.innerHTML = '<svg><use href="#i-redo"/></svg>'; r.onclick = regenerate; a.append(r);
    }
    col.append(a);
  });
}
function renderThread(){
  E.thread.innerHTML = ''; nodes.clear();
  const c = conv();
  E.main.classList.toggle('empty', !c || !c.messages.length);
  E.title.textContent = c ? c.title : 'New chat';
  c?.messages.forEach(m => E.thread.append(mkNode(m)));
  refreshActions(); S.pinned = true; requestAnimationFrame(toBottom);
}
function renderHistory(){
  E.history.innerHTML = '';
  for(const c of S.convs.slice().reverse()){
    const row = document.createElement('div'); row.className = 'h-item' + (c.id === S.active ? ' active' : '');
    const t = document.createElement('button'); t.className = 't'; t.textContent = c.title; t.onclick = () => select(c.id);
    const d = document.createElement('button'); d.className = 'del'; d.title = 'Delete chat'; d.setAttribute('aria-label','Delete chat');
    d.innerHTML = '<svg style="width:16px;height:16px"><use href="#i-trash"/></svg>';
    d.onclick = () => { S.convs = S.convs.filter(x => x.id !== c.id); if(S.active === c.id) S.active = null; persist(); renderHistory(); renderThread(); };
    row.append(t, d); E.history.append(row);
  }
}
function select(id){ S.active = id; renderThread(); renderHistory(); E.app.classList.remove('open'); }
function setBusy(){
  const g = !!S.gen;
  E.send.classList.toggle('stop', g);
  E.send.innerHTML = `<svg><use href="#i-${g ? 'stop' : 'send'}"/></svg>`;
  E.send.setAttribute('aria-label', g ? 'Stop generating' : 'Send message');
  E.send.disabled = !g && !E.input.value.trim();
}

/* ---------- Message lifecycle ---------- */
function ensureConv(){
  let c = conv();
  if(!c){ c = {id:uid(), title:'New chat', messages:[]}; S.convs.push(c); S.active = c.id; }
  return c;
}
function addUser(text){
  const c = ensureConv(); const m = {id:uid(), role:'user', text};
  c.messages.push(m); addNode(m);
  if(c.title === 'New chat'){ c.title = text.slice(0, 40); E.title.textContent = c.title; }
  renderHistory(); persist();
}
function startAI(id){
  const c = S.convs.find(x => x.id === S.genConv) || conv(); if(!c || findMsg(id)) return;
  const m = {id, role:'ai', text:''}; c.messages.push(m); S.gen = id;
  if(c.id === S.active) addNode(m); setBusy();
}
function delta(id, t){ const f = findMsg(id); if(!f || dead.has(id)) return; f.m.text += t; paint(id); }
function endAI(id){
  clearTimeout(S.timer);
  if(S.gen === id) S.gen = null;
  const f = findMsg(id);
  if(f && !f.m.text){ f.c.messages = f.c.messages.filter(x => x !== f.m); nodes.get(id)?.root.remove(); nodes.delete(id); }
  else paint(id);
  setBusy(); refreshActions(); persist();
  if(!conv()?.messages.length) E.main.classList.add('empty');
}
function fail(id, msg){ const f = findMsg(id); if(f){ f.m.error = true; f.m.text = msg; nodes.get(id)?.root.classList.add('error'); } toast(msg, true); endAI(id); }

window.onEvent = e => {
  if(e.type === 'message_start') startAI(e.id);
  else if(e.type === 'message_delta'){ if(!findMsg(e.id)) startAI(e.id); delta(e.id, e.text); }
  else if(e.type === 'message_end') endAI(e.id);
  else if(e.type === 'error') fail(e.id || S.gen, e.message);
  else if(e.type === 'user_message') addUser(e.text);
};
// Legacy path: complete messages from print_text() as {source, text}
function incoming(source, text){
  if(source === 'user') return addUser(text);
  let id = S.gen; const f = id && findMsg(id);
  if(!id || (f && f.m.text)){ id = uid(); startAI(id); }
  if(source === 'warning'){ findMsg(id).m.error = true; toast(text, true); }
  findMsg(id).m.text = text; paint(id); endAI(id);
}
let polling = false;
setInterval(async () => {
  if(!hasPy() || !legacy() || polling) return; polling = true;
  try{ const d = await window.pywebview.api.print_text(); health(true); (d?.messages || []).forEach(m => incoming(m.source, m.text)); }
  catch{ health(false); }
  polling = false;
}, 150);

async function submit(text){
  text = (text || '').trim(); if(!text || S.gen) return;
  addUser(text); E.input.value = ''; grow(); ls.set('jv_draft', '');
  S.genConv = S.active; S.pinned = true;
  const id = uid(); startAI(id);
  try{
    if(legacy()){
      await call('receive_text', text);
      S.timer = setTimeout(() => { if(S.gen === id){ endAI(id); toast('No reply yet. The assistant may be busy.', true); } }, 60000);
    } else await call('send_message', {id, text, conversation_id: S.genConv});
  }catch{ fail(id, 'Could not reach the assistant. Use Regenerate to retry.'); }
}
function stop(){
  const id = S.gen; if(!id) return;
  dead.add(id); call('stop_generation', {id}).catch(()=>{}); endAI(id);
}
function regenerate(){
  const c = conv(); if(!c || S.gen) return;
  const last = c.messages[c.messages.length - 1]; if(last?.role !== 'ai') return;
  const u = c.messages[c.messages.length - 2]; if(u?.role !== 'user') return;
  c.messages.splice(-2); renderThread(); submit(u.text);
}

/* ---------- Composer ---------- */
function grow(){ E.input.style.height = 'auto'; E.input.style.height = Math.min(E.input.scrollHeight, 156) + 'px'; }
E.input.addEventListener('input', () => { grow(); setBusy(); ls.set('jv_draft', E.input.value); });
E.input.addEventListener('keydown', e => {
  if(e.key === 'Enter' && !e.shiftKey && !e.isComposing){ e.preventDefault(); submit(E.input.value); }
});
E.send.onclick = () => S.gen ? stop() : submit(E.input.value);
document.querySelectorAll('.chip').forEach(c => c.onclick = () => submit(c.textContent));

/* ---------- Scroll ---------- */
E.chat.addEventListener('scroll', () => {
  S.pinned = E.chat.scrollHeight - E.chat.scrollTop - E.chat.clientHeight < 80;
  E.jump.classList.toggle('show', !S.pinned);
});
E.jump.onclick = () => { S.pinned = true; toBottom(); };

/* ---------- Voice (state machine: idle > starting > recording > transcribing) ---------- */
function micUI(){
  E.mic.classList.toggle('rec', S.mic === 'recording');
  E.mic.classList.toggle('busy', S.mic === 'starting' || S.mic === 'transcribing');
  E.listening.hidden = S.mic !== 'recording';
}
async function micStart(){
  if(S.mic !== 'idle') return; S.mic = 'starting'; S.release = false; micUI();
  try{ await call('mic_start'); }catch{ S.mic = 'idle'; micUI(); return toast('Microphone unavailable.', true); }
  S.mic = 'recording'; micUI();
  if(S.release) micStop();
}
async function micStop(){
  if(S.mic === 'starting'){ S.release = true; return; }
  if(S.mic !== 'recording') return;
  S.mic = 'transcribing'; micUI();
  try{
    const t = await call('mic_stop');
    if(typeof t === 'string') t.trim() ? submit(t) : toast("Didn't catch that. Try again.");
  }catch{ toast('Microphone error.', true); }
  S.mic = 'idle'; micUI();
}
E.mic.addEventListener('pointerdown', e => { e.preventDefault(); E.mic.setPointerCapture(e.pointerId); micStart(); });
['pointerup','pointercancel'].forEach(t => E.mic.addEventListener(t, micStop));
addEventListener('keydown', e => { if(e.ctrlKey && e.key.toLowerCase() === 'm' && !e.repeat){ e.preventDefault(); micStart(); } });
addEventListener('keyup', e => { if(e.key.toLowerCase() === 'm' || e.key === 'Control') micStop(); });

/* ---------- Sidebar, theme ---------- */
const narrow = () => matchMedia('(max-width:760px)').matches;
$('#menu').onclick = () => E.app.classList.toggle(narrow() ? 'open' : 'collapsed');
$('#scrim').onclick = () => E.app.classList.remove('open');
$('#new-chat').onclick = () => { S.active = null; renderThread(); renderHistory(); E.app.classList.remove('open'); E.input.focus(); };
function setTheme(t){ document.documentElement.dataset.theme = t; ls.set('jv_theme', t); }
$('#theme').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');

/* ---------- Boot ---------- */
async function init(){
  setTheme(ls.get('jv_theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
  try{ const j = await call('load_conversations'); S.convs = j ? JSON.parse(j) : []; }catch{ S.convs = []; }
  E.input.value = ls.get('jv_draft') || ''; grow(); setBusy();
  renderHistory(); renderThread(); E.input.focus();
}
if(hasPy()) init();
else { let done = false; const go = () => { if(!done){ done = true; init(); } };
  addEventListener('pywebviewready', go); setTimeout(go, 500); }

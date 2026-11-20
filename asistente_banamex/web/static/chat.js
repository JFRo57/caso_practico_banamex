const chat = document.querySelector('#chat');
const form = document.querySelector('#question-form');
const input = document.querySelector('#question');
const send = document.querySelector('#send');
const status = document.querySelector('#status');
const languageButtons = document.querySelectorAll('[data-locale]');
const labels = Array.from(document.querySelectorAll('[data-en]'), node => [node, node.textContent, node.dataset.en]);
const accessibleLabels = Array.from(document.querySelectorAll('[data-label-en]'), node => [
  node, node.getAttribute('aria-label'), node.dataset.labelEn
]);
const ui = {
  es: {
    title: 'Asistente de consulta · Prototipo', placeholder: 'Escribe tu pregunta',
    localSources: 'Consulta de fuentes locales', downloaded: 'Corpus actualizado el',
    hybrid: 'Interpretación opcional con Qwen3', local: 'Modo rápido: sin respaldo hacia un LLM', semantic: 'Búsqueda local con E5',
    adaptive: 'E5 con apoyo de Qwen3 cuando hace falta',
    submitted: 'Consulta enviada', loading: 'Consultando…',
    responseTime: 'Respuesta en', routes: { local: 'Ruta local', ollama: 'Qwen3', semantic: 'E5 sin Qwen3', semantic_ollama: 'E5 con apoyo de Qwen3', fallback: 'Respaldo local' },
    redacted: 'Consulta con datos omitidos', error: 'No pude enviar la consulta. Inténtalo de nuevo.'
  },
  en: {
    title: 'Information assistant · Prototype', placeholder: 'Type your question',
    localSources: 'Using local sources', downloaded: 'Corpus updated on',
    hybrid: 'Optional interpretation with Qwen3', local: 'Quick mode: no LLM fallback', semantic: 'Local E5 search',
    adaptive: 'E5 with Qwen3 assistance when needed',
    submitted: 'Question sent', loading: 'Looking up your question…',
    responseTime: 'Reply in', routes: { local: 'Local route', ollama: 'Qwen3', semantic: 'E5 without Qwen3', semantic_ollama: 'E5 with Qwen3 assistance', fallback: 'Local fallback' },
    redacted: 'Question with sensitive details hidden', error: 'I couldn’t send your question. Please try again.'
  }
};
let locale = 'es';
let responseLanguage = null;
let sourceStatus = null;
let pending = false;
let followup = null;

function updateStatus() {
  const copy = ui[locale];
  const mode = sourceStatus?.embeddings
    ? (sourceStatus?.model ? copy.adaptive : copy.semantic)
    : sourceStatus?.model ? copy.hybrid : copy.local;
  status.textContent = sourceStatus ? copy.downloaded + ' ' + sourceStatus.snapshot + ' · ' + mode : copy.localSources;
}

function selectLanguage(value) {
  locale = value;
  responseLanguage = value;
  const english = locale === 'en';
  document.documentElement.lang = locale;
  document.title = ui[locale].title;
  input.placeholder = ui[locale].placeholder;
  for (const [node, es, en] of labels) node.textContent = english ? en : es;
  for (const [node, es, en] of accessibleLabels) node.setAttribute('aria-label', english ? en : es);
  for (const button of languageButtons) button.setAttribute('aria-pressed', String(button.dataset.locale === locale));
  updateStatus();
}

function addMessage(text, role, lang = 'es') {
  const card = document.createElement('div');
  card.className = 'message ' + role;
  card.lang = lang;
  const reply = document.createElement('p');
  reply.className = 'reply';
  reply.textContent = text;
  card.append(reply);
  chat.append(card);
  chat.scrollTop = chat.scrollHeight;
  return card;
}

function appendSources(card, data) {
  if (!data.citations.length) return;
  const details = document.createElement('details');
  const title = document.createElement('summary');
  title.textContent = data.language === 'en' ? 'Official sources' : 'Fuentes oficiales';
  const list = document.createElement('ul');
  for (const source of data.citations) {
    const link = document.createElement('a');
    link.href = source.url;
    link.rel = 'noopener noreferrer';
    link.target = '_blank';
    link.textContent = source.title;
    const item = document.createElement('li');
    item.append(link, ' · ' + source.section + ' · ' + source.date);
    list.append(item);
  }
  details.append(title, list);
  card.append(details);
}

function appendResponseTime(card, data, startTime) {
  const seconds = (performance.now() - startTime) / 1000;
  const format = new Intl.NumberFormat(data.language, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const time = seconds < 0.01 ? '< ' + format.format(0.01) : format.format(seconds);
  const copy = ui[data.language];
  const route = copy.routes[data.route];
  const note = document.createElement('p');
  note.className = 'response-meta';
  note.textContent = copy.responseTime + ' ' + time + ' s' + (route ? ' · ' + route : '');
  card.append(note);
}

async function ask(question) {
  if (pending || !question.trim()) return;
  const startTime = performance.now();
  pending = true;
  send.disabled = true;
  input.value = '';
  const requestLocale = locale;
  const copy = ui[requestLocale];
  const user = addMessage(copy.submitted, 'user', requestLocale);
  const reply = addMessage(copy.loading, 'assistant', requestLocale);
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question, followup, response_language: responseLanguage})
    });
    if (!response.ok) throw new Error('chat unavailable');
    const data = await response.json();
    user.firstChild.textContent = data.redacted ? copy.redacted : question;
    reply.lang = data.language;
    reply.firstChild.textContent = data.text;
    appendSources(reply, data);
    appendResponseTime(reply, data, startTime);
    followup = data.followup ?? null;
  } catch {
    reply.firstChild.textContent = copy.error;
  } finally {
    pending = false;
    send.disabled = false;
    chat.scrollTop = chat.scrollHeight;
    input.focus();
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  ask(input.value);
});

input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

for (const button of document.querySelectorAll('[data-question]')) {
  button.addEventListener('click', () => ask(locale === 'en' ? button.dataset.questionEn : button.dataset.question));
}
for (const button of languageButtons) {
  button.addEventListener('click', () => selectLanguage(button.dataset.locale));
}

fetch('/api/status').then(response => response.json()).then(data => {
  sourceStatus = data;
  updateStatus();
}).catch(() => {});

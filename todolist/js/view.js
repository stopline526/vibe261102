import { MAX_TEXT_LENGTH } from './store.js';

const ICONS = {
  handle: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"/></svg>',
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4zM13 7l4 4"/></svg>',
  delete: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
};

const dateFormat = new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' });

const byId = (id) => document.getElementById(id);
const list = byId('list');
const items = new Map();

function iconButton(kind, className) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `icon-button ${className}`;
  button.dataset.action = kind;
  button.innerHTML = ICONS[kind];
  return button;
}

function createItem(id) {
  const li = document.createElement('li');
  li.className = 'item';
  li.dataset.id = id;

  const handle = iconButton('handle', 'handle');

  const checkWrap = document.createElement('label');
  checkWrap.className = 'check-wrap';
  const check = document.createElement('input');
  check.type = 'checkbox';
  check.className = 'check';
  checkWrap.append(check);

  const text = document.createElement('span');
  text.className = 'text';

  li.append(handle, checkWrap, text, iconButton('edit', 'edit-button'), iconButton('delete', 'delete'));
  return li;
}

function syncEditor(li, todo, isEditing) {
  const text = li.querySelector('.text');
  const buttons = li.querySelectorAll('.edit-button, .delete');
  let editor = li.querySelector('.edit');

  text.hidden = isEditing;
  buttons.forEach((button) => {
    button.hidden = isEditing;
  });

  if (isEditing && !editor) {
    editor = document.createElement('input');
    editor.type = 'text';
    editor.className = 'edit';
    editor.maxLength = MAX_TEXT_LENGTH;
    editor.value = todo.text;
    editor.setAttribute('aria-label', '할일 수정');
    text.after(editor);
    editor.focus();
    editor.select();
  } else if (!isEditing && editor) {
    editor.remove();
  }
}

function updateItem(li, todo, isEditing) {
  li.classList.toggle('completed', todo.completed);
  li.querySelector('.text').textContent = todo.text;

  const check = li.querySelector('.check');
  check.checked = todo.completed;
  check.setAttribute('aria-label', `${todo.text} 완료`);

  li.querySelector('.handle').setAttribute('aria-label', `${todo.text} 순서 변경, 위아래 화살표 키로 이동`);
  li.querySelector('.edit-button').setAttribute('aria-label', `${todo.text} 수정`);
  li.querySelector('.delete').setAttribute('aria-label', `${todo.text} 삭제`);

  syncEditor(li, todo, isEditing);
}

function renderList(visible, editingId) {
  const visibleIds = new Set(visible.map((todo) => todo.id));
  const focused = document.activeElement;
  const focusedItem = list.contains(focused) ? focused : null;

  for (const [id, li] of items) {
    if (!visibleIds.has(id)) {
      li.remove();
      items.delete(id);
    }
  }

  visible.forEach((todo, index) => {
    let li = items.get(todo.id);
    if (!li) {
      li = createItem(todo.id);
      items.set(todo.id, li);
    }
    if (list.children[index] !== li) {
      list.insertBefore(li, list.children[index] ?? null);
    }
    updateItem(li, todo, todo.id === editingId);
  });

  // DOM에서 위치를 옮기면 포커스가 풀리므로 복원한다.
  if (focusedItem?.isConnected && document.activeElement !== focusedItem) {
    focusedItem.focus();
  }
}

function renderHeader(today) {
  const total = today.length;
  const done = today.filter((todo) => todo.completed).length;
  const progress = byId('progress');

  byId('date').textContent = dateFormat.format(new Date());
  progress.hidden = total === 0;
  progress.setAttribute('aria-valuemax', String(total));
  progress.setAttribute('aria-valuenow', String(done));
  byId('progress-fill').style.width = total === 0 ? '0' : `${(done / total) * 100}%`;

  let status = `${done} / ${total} 완료`;
  if (total === 0) status = '오늘 할 일을 추가해 보세요';
  else if (done === total) status = `${status} · 오늘 할일을 모두 끝냈어요`;
  byId('status').textContent = status;
}

function matchesFilter(todo, filter) {
  if (filter === 'active') return !todo.completed;
  if (filter === 'completed') return todo.completed;
  return true;
}

export function render({ today, overdueCount, filter, editingId, storageOk }) {
  renderHeader(today);

  byId('storage-warning').hidden = storageOk;
  byId('overdue').hidden = overdueCount === 0;
  byId('overdue-text').textContent = `지난 할일 ${overdueCount}개가 남아 있어요`;

  document.querySelectorAll('.filter').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.filter === filter));
  });

  const visible = today.filter((todo) => matchesFilter(todo, filter));
  renderList(visible, editingId);
  byId('filter-empty').hidden = today.length === 0 || visible.length > 0;
}

export function showToast(message) {
  byId('toast-text').textContent = message;
  byId('toast').hidden = false;
}

export function hideToast() {
  byId('toast').hidden = true;
}

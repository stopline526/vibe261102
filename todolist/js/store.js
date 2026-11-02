const STORAGE_KEY = 'todolist:v1';
const BACKUP_KEY = 'todolist:backup';
const RETENTION_DAYS = 30;
export const MAX_TEXT_LENGTH = 200;

let todos = [];
let storageOk = true;

// UTC로 변환하면 한국 시간 오전 9시 이전에 전날이 되므로 현지 시간으로 계산한다.
export function toDateKey(date = new Date()) {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function isValidTodo(todo) {
  return (
    todo !== null &&
    typeof todo === 'object' &&
    typeof todo.id === 'string' &&
    typeof todo.text === 'string' &&
    typeof todo.completed === 'boolean' &&
    typeof todo.date === 'string' &&
    typeof todo.order === 'number'
  );
}

function parse(raw) {
  const data = JSON.parse(raw);
  if (!Array.isArray(data?.todos) || !data.todos.every(isValidTodo)) {
    throw new Error('잘못된 저장 데이터');
  }
  return data.todos;
}

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, todos }));
    storageOk = true;
  } catch {
    storageOk = false;
  }
}

function backup(raw) {
  try {
    localStorage.setItem(BACKUP_KEY, raw);
  } catch {
    storageOk = false;
  }
}

export function load() {
  let raw;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
    storageOk = true;
  } catch {
    storageOk = false;
    return;
  }
  if (raw === null) {
    todos = [];
    return;
  }
  try {
    todos = parse(raw);
  } catch {
    backup(raw);
    todos = [];
  }
}

export function purgeOldCompleted() {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - RETENTION_DAYS);
  const cutoffKey = toDateKey(cutoff);
  const kept = todos.filter((todo) => !(todo.completed && todo.date <= cutoffKey));
  if (kept.length !== todos.length) {
    todos = kept;
    save();
  }
}

export function isStorageOk() {
  return storageOk;
}

function findTodo(id) {
  return todos.find((todo) => todo.id === id);
}

function activeToday() {
  const today = toDateKey();
  return todos
    .filter((todo) => todo.date === today && !todo.completed)
    .sort((a, b) => a.order - b.order);
}

function nextOrder(date) {
  return todos
    .filter((todo) => todo.date === date)
    .reduce((max, todo) => Math.max(max, todo.order), 0) + 1;
}

export function getToday() {
  const today = toDateKey();
  const completed = todos
    .filter((todo) => todo.date === today && todo.completed)
    .sort((a, b) => (a.completedAt ?? '').localeCompare(b.completedAt ?? '') || a.order - b.order);
  return [...activeToday(), ...completed];
}

export function getOverdue() {
  const today = toDateKey();
  return todos
    .filter((todo) => todo.date < today && !todo.completed)
    .sort((a, b) => a.date.localeCompare(b.date) || a.order - b.order);
}

export function add(text) {
  const trimmed = text.trim().slice(0, MAX_TEXT_LENGTH);
  if (!trimmed) return false;
  const date = toDateKey();
  todos.push({
    id: crypto.randomUUID(),
    text: trimmed,
    completed: false,
    date,
    order: nextOrder(date),
    createdAt: new Date().toISOString(),
    completedAt: null,
  });
  save();
  return true;
}

export function setCompleted(id, completed) {
  const todo = findTodo(id);
  if (!todo) return;
  todo.completed = completed;
  todo.completedAt = completed ? new Date().toISOString() : null;
  save();
}

export function updateText(id, text) {
  const todo = findTodo(id);
  const trimmed = text.trim().slice(0, MAX_TEXT_LENGTH);
  if (!todo || !trimmed || trimmed === todo.text) return;
  todo.text = trimmed;
  save();
}

export function remove(id) {
  const todo = findTodo(id);
  if (!todo) return [];
  todos = todos.filter((item) => item !== todo);
  save();
  return [todo];
}

// order와 date를 그대로 되살리므로 원래 위치로 돌아간다.
export function restore(removed) {
  const missing = removed.filter((todo) => !findTodo(todo.id));
  if (missing.length === 0) return;
  todos.push(...missing);
  save();
}

export function importOverdue() {
  const today = toDateKey();
  let order = nextOrder(today);
  for (const todo of getOverdue()) {
    todo.date = today;
    todo.order = order++;
  }
  save();
}

export function discardOverdue() {
  const overdue = getOverdue();
  todos = todos.filter((todo) => !overdue.includes(todo));
  save();
  return overdue;
}

export function reorder(ids) {
  ids.forEach((id, index) => {
    const todo = findTodo(id);
    if (todo) todo.order = index + 1;
  });
  save();
}

export function move(id, delta) {
  const ids = activeToday().map((todo) => todo.id);
  const from = ids.indexOf(id);
  const to = from + delta;
  if (from === -1 || to < 0 || to >= ids.length) return;
  ids.splice(to, 0, ids.splice(from, 1)[0]);
  reorder(ids);
}

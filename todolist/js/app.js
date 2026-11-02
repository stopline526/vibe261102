import * as store from './store.js';
import { render, showToast, hideToast } from './view.js';

const TOAST_MS = 5000;

const byId = (id) => document.getElementById(id);
const list = byId('list');
const addInput = byId('add-input');
const hasFinePointer = window.matchMedia('(pointer: fine)').matches;

let filter = 'all';
let editingId = null;
let dragging = false;
let currentDay = store.toDateKey();
let undoAction = null;
let toastTimer = null;

function refresh() {
  const day = store.toDateKey();
  if (day !== currentDay) {
    currentDay = day;
    store.purgeOldCompleted();
  }
  render({
    today: store.getToday(),
    overdueCount: store.getOverdue().length,
    filter,
    editingId,
    storageOk: store.isStorageOk(),
  });
}

// 편집이나 드래그 중에는 다시 그리지 않고, 끝날 때 최신 상태로 그린다.
function refreshIfIdle() {
  if (editingId === null && !dragging) refresh();
}

function itemFor(id) {
  return list.querySelector(`[data-id="${CSS.escape(id)}"]`);
}

// 모바일에서는 가상 키보드가 화면을 가리므로 입력창에 포커스하지 않는다.
function focusAddInput() {
  if (hasFinePointer) addInput.focus();
}

/* 토스트 */
function clearToast() {
  clearTimeout(toastTimer);
  undoAction = null;
  hideToast();
}

function offerUndo(message, removed) {
  clearToast();
  undoAction = () => store.restore(removed);
  showToast(message);
  toastTimer = setTimeout(clearToast, TOAST_MS);
}

byId('toast-undo').addEventListener('click', () => {
  const undo = undoAction;
  clearToast();
  if (!undo) return;
  undo();
  refresh();
  focusAddInput();
});

/* 추가 */
byId('add-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (store.add(addInput.value)) {
    addInput.value = '';
    refresh();
  }
  addInput.focus();
});

/* 수정 */
function startEdit(id) {
  editingId = id;
  refresh();
}

function finishEdit({ save, refocus }) {
  if (editingId === null) return;
  const id = editingId;
  const value = itemFor(id)?.querySelector('.edit')?.value;
  editingId = null;
  if (save && value !== undefined) store.updateText(id, value);
  refresh();
  if (refocus) itemFor(id)?.querySelector('.edit-button')?.focus();
}

list.addEventListener('dblclick', (event) => {
  const item = event.target.closest('.text')?.closest('.item');
  if (item) startEdit(item.dataset.id);
});

list.addEventListener('focusout', (event) => {
  if (event.target.matches('.edit')) finishEdit({ save: true, refocus: false });
});

list.addEventListener('keydown', (event) => {
  if (event.target.matches('.edit')) {
    // 한글 조합 중의 Enter는 글자 확정용이므로 저장하지 않는다.
    // 기본 동작을 막지 않으면 같은 키 입력이 새로 포커스된 수정 버튼을 다시 누른다.
    if (event.key === 'Enter' && !event.isComposing) {
      event.preventDefault();
      finishEdit({ save: true, refocus: true });
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      finishEdit({ save: false, refocus: true });
    }
    return;
  }

  const handle = event.target.closest('.handle');
  if (handle && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
    event.preventDefault();
    store.move(handle.closest('.item').dataset.id, event.key === 'ArrowUp' ? -1 : 1);
    refresh();
  }
});

/* 완료 */
list.addEventListener('change', (event) => {
  if (!event.target.matches('.check')) return;
  store.setCompleted(event.target.closest('.item').dataset.id, event.target.checked);
  refresh();
});

/* 수정, 삭제 버튼 */
function deleteItem(item) {
  const next = item.nextElementSibling ?? item.previousElementSibling;
  const removed = store.remove(item.dataset.id);
  refresh();
  if (next) next.querySelector('.delete').focus();
  else focusAddInput();
  offerUndo('할일을 삭제했어요', removed);
}

list.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const item = button.closest('.item');
  if (button.dataset.action === 'edit') startEdit(item.dataset.id);
  if (button.dataset.action === 'delete') deleteItem(item);
});

/* 순서 변경 */
function activeSiblings() {
  return [...list.querySelectorAll('.item:not(.completed)')];
}

function middleY(element) {
  const rect = element.getBoundingClientRect();
  return rect.top + rect.height / 2;
}

list.addEventListener('pointerdown', (event) => {
  const handle = event.target.closest('.handle');
  if (!handle || event.button !== 0) return;
  event.preventDefault();
  handle.focus();

  const item = handle.closest('.item');
  dragging = true;
  item.classList.add('dragging');

  // 끌리는 항목 대신 이웃을 옮겨야 터치의 포인터 연결이 끊기지 않는다.
  // 빠르게 끌면 한 번의 이동 이벤트에 여러 칸을 지나므로 자리를 찾을 때까지 반복한다.
  const onMove = (moveEvent) => {
    for (;;) {
      const siblings = activeSiblings();
      const index = siblings.indexOf(item);
      const previous = siblings[index - 1];
      const next = siblings[index + 1];
      if (previous && moveEvent.clientY < middleY(previous)) item.after(previous);
      else if (next && moveEvent.clientY > middleY(next)) item.before(next);
      else break;
    }
  };

  const onEnd = (endEvent) => {
    document.removeEventListener('pointermove', onMove);
    document.removeEventListener('pointerup', onEnd);
    document.removeEventListener('pointercancel', onEnd);
    item.classList.remove('dragging');
    dragging = false;
    if (endEvent.type === 'pointerup') {
      store.reorder(activeSiblings().map((sibling) => sibling.dataset.id));
    }
    refresh();
  };

  document.addEventListener('pointermove', onMove);
  document.addEventListener('pointerup', onEnd);
  document.addEventListener('pointercancel', onEnd);
});

/* 필터 */
byId('filters').addEventListener('click', (event) => {
  const button = event.target.closest('[data-filter]');
  if (!button) return;
  filter = button.dataset.filter;
  refresh();
});

/* 지난 할일 */
byId('overdue-import').addEventListener('click', () => {
  store.importOverdue();
  refresh();
  focusAddInput();
});

byId('overdue-discard').addEventListener('click', () => {
  const removed = store.discardOverdue();
  refresh();
  focusAddInput();
  offerUndo(`지난 할일 ${removed.length}개를 버렸어요`, removed);
});

/* 다른 탭의 변경과 날짜 변경 */
window.addEventListener('storage', (event) => {
  if (event.key !== null && event.key !== 'todolist:v1') return;
  if (editingId !== null || dragging) return;
  store.load();
  refresh();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') refreshIfIdle();
});
window.addEventListener('focus', refreshIfIdle);

/* 시작 */
store.load();
store.purgeOldCompleted();
refresh();
focusAddInput();

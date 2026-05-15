// 추가/삭제/localStorage 영구 저장 3가지 기능만 담당하는 Todo 로직

const STORAGE_KEY = "todo-items";

const listEl = document.getElementById("list");
const emptyEl = document.getElementById("empty");
const inputEl = document.getElementById("input");
const addBtnEl = document.getElementById("addBtn");

// 메모리 상태를 단일 진실 원천으로 두고, 변경 시마다 localStorage와 DOM을 동기화
let items = loadItems();

function loadItems() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // 저장 데이터가 손상된 경우 빈 배열로 복구해서 앱이 멈추지 않게 함
    return [];
  }
}

function saveItems() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

// 시간 + 랜덤값 조합으로 외부 라이브러리 없이 충돌 가능성 거의 0인 ID 생성
function createId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function render() {
  listEl.innerHTML = "";

  if (items.length === 0) {
    emptyEl.classList.remove("hidden");
  } else {
    emptyEl.classList.add("hidden");
  }

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "item";
    li.dataset.id = item.id;

    const span = document.createElement("span");
    span.className = "item-text";
    span.textContent = item.text;

    const btn = document.createElement("button");
    btn.className = "delete-btn";
    btn.type = "button";
    btn.textContent = "×";
    btn.setAttribute("aria-label", `${item.text} 삭제`);

    li.appendChild(span);
    li.appendChild(btn);
    listEl.appendChild(li);
  }
}

function addItem() {
  // trim 결과가 빈 문자열이면 공백만 입력된 경우이므로 추가 차단
  const text = inputEl.value.trim();
  if (text === "") return;

  items.push({ id: createId(), text });
  saveItems();
  render();

  inputEl.value = "";
  inputEl.focus();
}

function deleteItem(id) {
  items = items.filter((item) => item.id !== id);
  saveItems();
  render();
}

addBtnEl.addEventListener("click", addItem);

// 한글 IME 조합 중 Enter는 글자 확정용이라 추가 동작이 일어나면 안 됨 (isComposing 체크)
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.isComposing) {
    e.preventDefault();
    addItem();
  }
});

// 항목이 동적으로 늘어나도 매번 리스너 다는 비용을 피하기 위해 ul에 이벤트 위임
listEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".delete-btn");
  if (!btn) return;
  const li = btn.closest(".item");
  if (!li) return;
  deleteItem(li.dataset.id);
});

render();
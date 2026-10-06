'use strict';

// 같은 폴더 상위의 완성본(study-02/app.js)과 file:// 저장소를 공유하므로 키를 분리
const STORAGE_KEY = 'assets-step';

// 상품 객체 형태:
// { id, category: 'deposit' | 'savings', name, bank, principal, monthlyAmount,
//   rate, startDate, maturityDate, terminationDate, memo }
let assets = loadAssets();

// ---------- 저장 ----------

function loadAssets() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

function saveAssets() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(assets));
  } catch (e) {
    alert('저장에 실패했습니다. 브라우저 저장소 설정을 확인해 주세요.');
  }
}

// ---------- 날짜 ----------

const DAY_MS = 86400000;

// 'YYYY-MM-DD'를 로컬 자정 기준 Date로 변환 (시간대 오차 방지)
function parseDate(str) {
  const [y, m, d] = str.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function daysBetween(from, to) {
  return Math.round((to - from) / DAY_MS);
}

// 말일 보정: 1/31 + 1개월 = 2/28(29)
function addMonths(date, months) {
  const target = date.getMonth() + months;
  const lastDay = new Date(date.getFullYear(), target + 1, 0).getDate();
  return new Date(date.getFullYear(), target, Math.min(date.getDate(), lastDay));
}

function monthsBetween(from, to) {
  let months = (to.getFullYear() - from.getFullYear()) * 12 + (to.getMonth() - from.getMonth());
  if (addMonths(from, months) > to) months -= 1;
  return months;
}

function toDateString(date) {
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${m}-${d}`;
}

function displayDate(str) {
  return str.replaceAll('-', '.');
}

// ---------- 계산 ----------
// 결과는 저장하지 않고 render() 때마다 오늘 기준으로 다시 계산한다.

// 적금 납입일: 신규일부터 매달 같은 날, 총 n회 (n = 신규일~만기일 개월 수, 최소 1)
function paymentDates(item) {
  const start = parseDate(item.startDate);
  const count = Math.max(1, monthsBetween(start, parseDate(item.maturityDate)));
  return Array.from({ length: count }, (_, i) => addMonths(start, i));
}

// 기준일까지 도래한 납입일 수
function dueCount(item, refDate) {
  return paymentDates(item).filter((pay) => pay <= refDate).length;
}

// 미납 회차: 오늘(해지·만기 시에는 그날)까지 도래한 회차 중 가장 최근 N회로 보고,
// 만기까지 미납으로 남는다고 가정해 원금·이자 계산에서 모두 뺀다
function missedDates(item, refDate) {
  const due = paymentDates(item).filter((pay) => pay <= refDate);
  const missed = Math.min(item.missedCount || 0, due.length);
  return due.slice(due.length - missed).map((pay) => pay.getTime());
}

// missed: missedDates()가 돌려준 미납 납입일(타임스탬프) 목록
function paidDates(item, refDate, missed) {
  return paymentDates(item).filter((pay) => pay <= refDate && !missed.includes(pay.getTime()));
}

function principalUntil(item, refDate, missed = []) {
  if (item.category === 'deposit') return item.principal;
  return paidDates(item, refDate, missed).length * item.monthlyAmount;
}

// 단리, 일할(365일), 세전, 원 미만 절사. 중도해지도 약정 이율 그대로 적용
function interestUntil(item, refDate, missed = []) {
  const rate = item.rate / 100;
  if (item.category === 'deposit') {
    const days = Math.max(0, daysBetween(parseDate(item.startDate), refDate));
    return Math.floor(item.principal * rate * days / 365);
  }
  let sum = 0;
  for (const pay of paidDates(item, refDate, missed)) {
    sum += item.monthlyAmount * rate * daysBetween(pay, refDate) / 365;
  }
  return Math.floor(sum);
}

// 일반과세 15.4% = 이자소득세 14% + 지방소득세(소득세의 10%), 각각 10원 미만 절사
function afterTax(interest) {
  const incomeTax = Math.floor(interest * 0.14 / 10) * 10;
  const localTax = Math.floor(incomeTax * 0.1 / 10) * 10;
  return interest - incomeTax - localTax;
}

function analyze(item, now) {
  const start = parseDate(item.startDate);
  const maturity = parseDate(item.maturityDate);
  const termination = item.terminationDate ? parseDate(item.terminationDate) : null;
  // 기준일은 만기일을, 중도해지일이 있으면 중도해지일을 넘지 않는다
  const end = termination || maturity;
  const ref = now < end ? now : end;

  let status = 'active';
  if (termination) status = 'terminated';
  else if (now >= maturity) status = 'matured';

  const elapsed = daysBetween(start, ref);
  const progress = Math.min(100, Math.max(0, elapsed / daysBetween(start, maturity) * 100));

  const missed = item.category === 'savings' ? missedDates(item, ref) : [];

  return {
    status,
    progress,
    missedCount: missed.length,
    dDay: daysBetween(now, maturity),
    principalNow: principalUntil(item, ref, missed),
    interestNow: interestUntil(item, ref, missed),
    principalMaturity: principalUntil(item, maturity, missed),
    interestMaturity: interestUntil(item, maturity, missed),
    interestMaturityNet: afterTax(interestUntil(item, maturity, missed)),
  };
}

// ---------- 화면 ----------

const CATEGORY_LABEL = { deposit: '예금', savings: '적금' };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function won(n) {
  return `${Math.round(n).toLocaleString('ko-KR')}원`;
}

function figure(label, value, sub) {
  const wrap = el('div');
  wrap.append(el('dt', '', label));
  const dd = el('dd', '', value);
  if (sub) dd.append(el('small', '', sub));
  wrap.append(dd);
  return wrap;
}

// 만기 → 진행 중 → 중도해지 순, 같은 상태 안에서는 만기일이 가까운 순
const STATUS_ORDER = { matured: 0, active: 1, terminated: 2 };
let currentFilter = 'all';

function render() {
  const now = today();
  document.getElementById('today').textContent = displayDate(toDateString(now));

  const rows = assets.map((item) => ({ item, calc: analyze(item, now) }));
  renderSummary(rows);

  const visible = rows
    .filter(({ item }) => currentFilter === 'all' || item.category === currentFilter)
    .sort((a, b) =>
      STATUS_ORDER[a.calc.status] - STATUS_ORDER[b.calc.status] ||
      a.item.maturityDate.localeCompare(b.item.maturityDate));

  const list = document.getElementById('list');
  const empty = visible.length === 0;
  document.getElementById('empty').hidden = !empty;

  // 전체 탭: 적금은 왼쪽, 예금은 오른쪽 열 / 예금·적금 탭: 한 줄에 한 상품씩
  const split = currentFilter === 'all' && !empty;
  list.classList.toggle('split', split);
  list.classList.toggle('single', !split);
  if (split) {
    list.replaceChildren(
      renderColumn('savings', visible.filter((r) => r.item.category === 'savings')),
      renderColumn('deposit', visible.filter((r) => r.item.category === 'deposit')));
  } else {
    list.replaceChildren(...visible.map(({ item, calc }) => renderCard(item, calc)));
  }
}

function renderColumn(category, rows) {
  const column = el('li', 'column');
  column.append(el('h2', 'column-title', `${CATEGORY_LABEL[category]} ${rows.length}건`));
  if (rows.length === 0) {
    column.append(el('p', 'column-empty', `등록된 ${CATEGORY_LABEL[category]}이 없습니다.`));
  } else {
    const ul = el('ul', 'column-list');
    ul.append(...rows.map(({ item, calc }) => renderCard(item, calc)));
    column.append(ul);
  }
  return column;
}

// 중도해지 상품은 합계에서 빼고, 건수와 해지 시 이자만 따로 보여준다
function renderSummary(rows) {
  const holding = rows.filter((r) => r.calc.status !== 'terminated');
  const terminated = rows.filter((r) => r.calc.status === 'terminated');
  const sum = (list, fn) => list.reduce((acc, r) => acc + fn(r.calc), 0);

  const principal = sum(holding, (c) => c.principalNow);
  const interest = sum(holding, (c) => c.interestNow);
  document.getElementById('sumValue').textContent = won(principal + interest);
  document.getElementById('sumPrincipal').textContent = won(principal);
  document.getElementById('sumInterest').textContent = won(interest);
  document.getElementById('sumMaturity').textContent =
    won(sum(holding, (c) => c.principalMaturity + c.interestMaturityNet));

  for (const category of ['deposit', 'savings']) {
    const group = holding.filter((r) => r.item.category === category);
    const id = category === 'deposit' ? 'subDeposit' : 'subSavings';
    document.getElementById(id).textContent =
      `${CATEGORY_LABEL[category]} ${group.length}건 · ${won(sum(group, (c) => c.principalNow + c.interestNow))}`;
  }

  document.getElementById('subTerminated').textContent = terminated.length
    ? `중도해지 ${terminated.length}건 · 해지 시 이자 ${won(sum(terminated, (c) => c.interestNow))}`
    : '';
}

function renderCard(item, calc) {
  const card = el('li', `card ${calc.status}`);

  // 머리: 카테고리, 상품명, 금융기관·이율, 상태 배지
  const head = el('div', 'card-head');
  const titleWrap = el('div', 'card-info');
  const title = el('h3', 'card-title');
  title.append(el('span', `badge ${item.category}`, CATEGORY_LABEL[item.category]), item.name);
  const sub = [item.bank, `연 ${item.rate}%`].filter(Boolean).join(' · ');
  titleWrap.append(title, el('div', 'card-sub', sub));

  let statusText = calc.dDay === 0 ? 'D-Day' : `D-${calc.dDay}`;
  if (calc.status === 'matured') statusText = '만기';
  if (calc.status === 'terminated') statusText = '중도해지';
  head.append(titleWrap, el('span', `badge status ${calc.status}`, statusText));

  // 기간
  let period = `${displayDate(item.startDate)} ~ ${displayDate(item.maturityDate)}`;
  if (item.terminationDate) period += ` · 해지 ${displayDate(item.terminationDate)}`;

  // 금액 3칸
  const figures = el('dl', 'figures');
  const principalLabel = item.category === 'deposit' ? '원금' : '납입 원금';
  const subParts = [];
  if (item.category === 'savings') {
    if (calc.status !== 'terminated') {
      subParts.push(`만기 ${won(calc.principalMaturity)}`, `월 ${won(item.monthlyAmount)}`);
    }
    if (calc.missedCount > 0) subParts.push(`미납 ${calc.missedCount}회`);
  }
  const principalSub = subParts.join(' · ');
  figures.append(figure(principalLabel, won(calc.principalNow), principalSub));
  if (calc.status === 'terminated') {
    figures.append(figure('해지 시 이자', won(calc.interestNow)));
    figures.append(figure('해지 시 수령액', won(calc.principalNow + calc.interestNow)));
  } else {
    figures.append(figure('현재 이자', won(calc.interestNow)));
    figures.append(figure('만기 예상 이자 (세후)', won(calc.interestMaturityNet), `세전 ${won(calc.interestMaturity)}`));
  }

  // 진행률
  const progress = el('div', 'progress');
  const track = el('div', 'progress-track');
  const bar = el('div', 'progress-bar');
  bar.style.width = `${calc.progress}%`;
  track.append(bar);
  progress.append(track, el('span', 'progress-text', `${calc.progress.toFixed(1)}%`));

  // 버튼
  const actions = el('div', 'card-actions');
  const editBtn = el('button', 'btn btn-small', '수정');
  editBtn.type = 'button';
  editBtn.addEventListener('click', () => openForm(item));
  const deleteBtn = el('button', 'btn btn-small btn-danger', '삭제');
  deleteBtn.type = 'button';
  deleteBtn.addEventListener('click', () => removeAsset(item));
  actions.append(editBtn, deleteBtn);

  card.append(head, el('div', 'card-dates', period), figures, progress);
  if (item.memo) card.append(el('p', 'card-memo', item.memo));
  card.append(actions);
  return card;
}

// ---------- 추가 / 수정 / 삭제 ----------

const dialog = document.getElementById('dialog');
const form = document.getElementById('form');
const formError = document.getElementById('formError');
let editingId = null;

function selectedCategory() {
  return form.elements.category.value;
}

// 구분에 따라 예치 원금 / 월 납입액 입력칸 전환
function syncCategoryFields() {
  const category = selectedCategory();
  form.querySelectorAll('[data-for]').forEach((field) => {
    field.hidden = field.dataset.for !== category;
  });
}

function openForm(item) {
  form.reset();
  formError.hidden = true;
  editingId = item ? item.id : null;
  document.getElementById('formTitle').textContent = item ? '상품 수정' : '상품 추가';

  if (item) {
    form.elements.category.value = item.category;
    for (const key of ['name', 'bank', 'principal', 'monthlyAmount', 'rate',
      'startDate', 'maturityDate', 'terminationDate', 'memo']) {
      form.elements[key].value = item[key] ?? '';
    }
    form.elements.missedCount.value = item.missedCount || 0;
  } else {
    form.elements.startDate.value = toDateString(today());
  }
  syncCategoryFields();
  dialog.showModal();
}

// 검증에 실패하면 { error }, 통과하면 { data } 반환
function readForm() {
  const f = form.elements;
  const category = selectedCategory();
  const amountKey = category === 'deposit' ? 'principal' : 'monthlyAmount';
  const amount = Number(f[amountKey].value);
  const rate = Number(f.rate.value);
  const name = f.name.value.trim();
  const startDate = f.startDate.value;
  const maturityDate = f.maturityDate.value;
  const terminationDate = f.terminationDate.value || null;

  if (!name) return { error: '상품명을 입력해 주세요.' };
  if (!f[amountKey].value || !(amount > 0)) {
    return { error: category === 'deposit' ? '예치 원금을 입력해 주세요.' : '월 납입액을 입력해 주세요.' };
  }
  if (f.rate.value === '' || !(rate >= 0)) return { error: '연 이율을 입력해 주세요.' };
  if (!startDate || !maturityDate) return { error: '신규일과 만기일을 입력해 주세요.' };
  if (maturityDate <= startDate) return { error: '만기일은 신규일보다 늦어야 합니다.' };
  if (terminationDate && (terminationDate < startDate || terminationDate >= maturityDate)) {
    return { error: '중도해지일은 신규일 이후, 만기일 이전이어야 합니다.' };
  }

  // 미납 회차: 0 이상 정수, 오늘(해지 시 해지일)까지 도래한 납입 회차를 넘을 수 없음
  let missedCount = 0;
  if (category === 'savings') {
    missedCount = Number(f.missedCount.value || 0);
    if (!Number.isInteger(missedCount) || missedCount < 0) {
      return { error: '미납 회차는 0 이상의 정수로 입력해 주세요.' };
    }
    const now = today();
    const termination = terminationDate ? parseDate(terminationDate) : null;
    const due = dueCount({ startDate, maturityDate }, termination && termination < now ? termination : now);
    if (missedCount > due) {
      return { error: `미납 회차는 지금까지 도래한 납입 회차(${due}회)를 넘을 수 없습니다.` };
    }
  }

  return {
    data: {
      category,
      name,
      bank: f.bank.value.trim(),
      principal: category === 'deposit' ? amount : null,
      monthlyAmount: category === 'savings' ? amount : null,
      rate,
      startDate,
      maturityDate,
      terminationDate,
      memo: f.memo.value.trim(),
      missedCount,
    },
  };
}

function removeAsset(item) {
  if (!confirm(`'${item.name}'을(를) 삭제할까요?`)) return;
  assets = assets.filter((a) => a.id !== item.id);
  saveAssets();
  render();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const { error, data } = readForm();
  if (error) {
    formError.textContent = error;
    formError.hidden = false;
    return;
  }
  if (editingId) {
    assets = assets.map((a) => (a.id === editingId ? { id: editingId, ...data } : a));
  } else {
    assets.push({ id: String(Date.now()), ...data });
  }
  saveAssets();
  dialog.close();
  render();
});

form.querySelectorAll('input[name="category"]').forEach((radio) => {
  radio.addEventListener('change', syncCategoryFields);
});
document.getElementById('cancelBtn').addEventListener('click', () => dialog.close());
document.getElementById('addBtn').addEventListener('click', () => openForm(null));

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    currentFilter = tab.dataset.filter;
    document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
    render();
  });
});

render();

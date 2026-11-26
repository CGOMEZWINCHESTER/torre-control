const moneyFormatter = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const TONES = { neutral: true, info: true, success: true, warn: true, danger: true };

const state = {
  profiles: [],
  me: null,
  selectedDept: null,
  pin: "",
  busy: false,
  screen: "login",
  boardCategory: "Todas",
  choreFilter: "all",
  financeTab: "expenses",
  neighborsTab: "directory",
  parkingFilter: "all",
  announcements: [],
  chores: [],
  expenses: [],
  contributions: [],
  residents: [],
  parking: [],
  summary: null,
  editing: {
    announcementId: null,
    choreId: null,
    expenseId: null,
    residentId: null,
    parkingId: null
  },
  confirmAction: null,
  toastTimer: null
};

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function money(value) {
  return moneyFormatter.format(Number(value) || 0);
}

function isAdmin() {
  return !!state.me && state.me.role === "admin";
}

function roleLabel(role) {
  return role === "admin" ? "Admin" : "Vecino";
}

function safeColor(value) {
  const color = String(value || "");
  return /^#[0-9a-fA-F]{6}$/.test(color) ? escapeHtml(color) : "#334155";
}

function safeImage(value) {
  const url = String(value || "");
  return /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(url) ? escapeHtml(url) : "";
}

function avatarHtml(user, extraClass) {
  if (!user) return '<span class="avatar" aria-hidden="true"></span>';
  const className = "avatar " + (extraClass || "");
  return '<span class="' + escapeHtml(className.trim()) + '" style="background:' + safeColor(user.avatar_color) + '">' + escapeHtml(user.avatar_icon || "-") + "</span>";
}

function imageHtml(url, alt) {
  const source = safeImage(url);
  if (!source) return "";
  return '<img class="thumb" src="' + source + '" alt="' + escapeHtml(alt) + '" loading="lazy" />';
}

function badge(label, tone) {
  const name = TONES[tone] ? tone : "neutral";
  return '<span class="badge badge--' + name + '">' + escapeHtml(label) + "</span>";
}

function parseDay(value) {
  const text = String(value || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null;
  const parts = text.split("-");
  const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return isNaN(date.getTime()) ? null : date;
}

function formatDay(value) {
  const date = parseDay(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short" }).format(date);
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function todayDate() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function daysUntil(value) {
  const date = parseDay(value);
  if (!date) return null;
  return Math.round((date.getTime() - todayDate().getTime()) / 86400000);
}

function localDate() {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return date.getFullYear() + "-" + month + "-" + day;
}

async function api(path, options) {
  const opts = options || {};
  const init = {
    method: opts.method || "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" }
  };
  if (state.me && state.me.dept_number != null) {
    init.headers["X-User-Id"] = String(state.me.dept_number);
  }
  if (opts.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }

  let response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    const offline = new Error("Sin conexión. Revisa tu red e intenta de nuevo.");
    offline.offline = true;
    throw offline;
  }

  if (response.status === 401 && !opts.skipAuthRedirect) {
    handleUnauthorized();
  }

  if (!response.ok) {
    let detail = "No se pudo completar la acción";
    try {
      const data = await response.json();
      if (data && data.detail) {
        detail = typeof data.detail === "string" ? data.detail : "No tienes permiso para esta acción";
      }
    } catch (error) {}
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error("Respuesta inesperada del servidor");
  }
}

async function safeApi(path, fallback) {
  try {
    return await api(path);
  } catch (error) {
    showToast(error.message);
    return fallback;
  }
}

function clearApiCache() {
  if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: "CLEAR_API_CACHE" });
  }
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(function () {
    toast.classList.remove("show");
  }, 2800);
}

function showScreen(name) {
  state.screen = name;
  document.querySelectorAll(".screen").forEach(function (screen) {
    screen.classList.toggle("active", screen.id === "screen-" + name);
  });
  document.getElementById("app-header").classList.toggle("hidden", name === "login");
  document.getElementById("bottom-nav").classList.toggle("hidden", name === "login");
  document.querySelectorAll(".nav-item").forEach(function (item) {
    item.classList.toggle("active", item.dataset.id === name);
  });
  updateActionButtons();
  window.scrollTo(0, 0);
}

function updateHeader() {
  document.getElementById("header-avatar").innerHTML = avatarHtml(state.me);
  document.getElementById("header-user").textContent = state.me
    ? "Depto " + state.me.dept_number + " · " + state.me.name
    : "";
  document.getElementById("header-badge").classList.toggle("hidden", !isAdmin());
}

function updateActionButtons() {
  const admin = isAdmin();
  document.getElementById("add-announcement").classList.remove("hidden");
  document.getElementById("pin-field").classList.toggle("hidden", !admin);
  document.getElementById("add-chore").classList.toggle("hidden", !admin);
  document.getElementById("add-expense").classList.toggle("hidden", !(admin && state.financeTab === "expenses"));
  document.getElementById("add-contribution").classList.toggle("hidden", state.financeTab !== "contributions");
  document.getElementById("add-parking").classList.toggle("hidden", !(admin && state.neighborsTab === "parking"));
  document.getElementById("add-resident").classList.toggle("hidden", !(admin && state.neighborsTab === "directory"));
}

function handleUnauthorized() {
  if (!state.me) return;
  state.me = null;
  updateHeader();
  showScreen("login");
  resetPinPanel();
  loadProfiles();
}

function openSheet(id) {
  document.getElementById(id).classList.add("open");
}

function closeSheet(id) {
  document.getElementById(id).classList.remove("open");
}

function closeAllSheets() {
  document.querySelectorAll(".sheet-backdrop.open").forEach(function (sheet) {
    sheet.classList.remove("open");
  });
}

function activateChip(containerId, action, value) {
  document.querySelectorAll("#" + containerId + " [data-action='" + action + "']").forEach(function (chip) {
    chip.classList.toggle("active", chip.dataset.id === value);
  });
}

function setLoading(listId, emptyId, count) {
  const list = document.getElementById(listId);
  const empty = document.getElementById(emptyId);
  empty.classList.add("hidden");
  list.classList.remove("hidden");
  const lines = ["skeleton-line skeleton-line--title", "skeleton-line", "skeleton-line skeleton-line--short"];
  let html = "";
  for (let index = 0; index < count; index += 1) {
    html += '<div class="skeleton-card">' +
      lines.map(function (line) { return '<div class="' + line + '"></div>'; }).join("") +
      "</div>";
  }
  list.innerHTML = html;
}

function renderItems(listId, emptyId, html, count) {
  const list = document.getElementById(listId);
  const empty = document.getElementById(emptyId);
  list.innerHTML = html;
  list.classList.toggle("hidden", count === 0);
  empty.classList.toggle("hidden", count > 0);
}

function renderProfiles() {
  const grid = document.getElementById("profile-grid");
  if (!state.profiles.length) {
    grid.innerHTML = '<p class="muted">No hay perfiles disponibles.</p>';
    return;
  }
  grid.innerHTML = state.profiles.map(function (profile) {
    return '<button class="dept-card" type="button" data-action="login-profile" data-id="' + escapeHtml(profile.dept_number) + '">' +
      avatarHtml(profile, "avatar--lg") +
      '<span class="dept-card__number">Depto ' + escapeHtml(profile.dept_number) + "</span>" +
      '<span class="dept-card__name">' + escapeHtml(profile.name) + "</span>" +
      "</button>";
  }).join("");
}

async function loadProfiles() {
  state.profiles = await safeApi("/api/auth/profiles", []);
  renderProfiles();
}

function renderPinDots() {
  const dots = document.getElementById("pin-dots");
  let html = "";
  for (let index = 0; index < 4; index += 1) {
    html += '<span class="dot' + (index < state.pin.length ? " filled" : "") + '"></span>';
  }
  dots.innerHTML = html;
}

function selectDepartment(dept) {
  const letter = String(dept).toUpperCase();
  const profile = state.profiles.find(function (item) {
    return String(item.dept_number).toUpperCase() === letter;
  });
  if (!profile) return;
  state.selectedDept = letter;
  state.pin = "";
  document.getElementById("profile-grid").classList.add("hidden");
  document.getElementById("pin-panel").classList.remove("hidden");
  document.getElementById("pin-greeting").textContent = "Depto " + profile.dept_number + " · " + profile.name;
  document.getElementById("pin-error").classList.add("hidden");
  renderPinDots();
}

function resetPinPanel() {
  state.selectedDept = null;
  state.pin = "";
  document.getElementById("pin-panel").classList.add("hidden");
  document.getElementById("profile-grid").classList.remove("hidden");
  document.getElementById("pin-error").classList.add("hidden");
  renderPinDots();
}

function pressKey(key) {
  if (state.busy) return;
  document.getElementById("pin-error").classList.add("hidden");
  if (key === "clear") {
    state.pin = "";
  } else if (key === "enter") {
    submitPin();
    return;
  } else if (/^\d$/.test(key) && state.pin.length < 4) {
    state.pin += key;
  }
  renderPinDots();
  if (state.pin.length === 4) submitPin();
}

async function submitPin() {
  if (state.busy || state.pin.length !== 4 || state.selectedDept === null) return;
  state.busy = true;
  try {
    const me = await api("/api/auth/login", {
      method: "POST",
      body: { dept_number: state.selectedDept, pin: state.pin },
      skipAuthRedirect: true
    });
    await afterLogin(me);
  } catch (error) {
    const errorBox = document.getElementById("pin-error");
    errorBox.textContent = "PIN incorrecto. Verifica el departamento e intenta de nuevo.";
    errorBox.classList.remove("hidden");
    state.pin = "";
    renderPinDots();
    showToast(error.message);
  } finally {
    state.busy = false;
  }
}

async function afterLogin(me) {
  state.me = me;
  clearApiCache();
  updateHeader();
  resetPinPanel();
  showScreen("board");
  await loadAllData();
}

async function loadAllData() {
  await Promise.all([
    loadAnnouncements(),
    loadChores(),
    loadFinance(),
    loadResidents(),
    loadParking()
  ]);
}

function categoryTone(category) {
  if (category === "Urgente") return "danger";
  if (category === "Mantenimiento") return "warn";
  if (category === "Acuerdos") return "success";
  return "info";
}

function readLabel(count) {
  return count === 1 ? "1 enterado" : count + " enterados";
}

function announcementCard(item) {
  const readers = Array.isArray(item.read_by) ? item.read_by : [];
  const read = readers.indexOf(state.me.id) !== -1;
  const comments = Array.isArray(item.comments) ? item.comments.slice(-3) : [];
  const author = item.creator ? item.creator.name : "Vecino";
  const commentHtml = comments.map(function (comment) {
    const commentAuthor = comment.author ? comment.author.name : "Vecino";
    const removable = isAdmin() || comment.resident_id === state.me.id;
    return '<div class="comment">' +
      '<div class="comment__head"><strong>' + escapeHtml(commentAuthor) + "</strong><span>" + escapeHtml(formatDateTime(comment.created_at)) + "</span></div>" +
      "<p>" + escapeHtml(comment.body) + "</p>" +
      (removable ? '<button class="comment-delete" type="button" data-action="delete-comment" data-id="' + escapeHtml(comment.id) + '" data-parent="' + escapeHtml(item.id) + '">Eliminar</button>' : "") +
      "</div>";
  }).join("");

  let adminActions = "";
  if (isAdmin()) {
    adminActions =
      '<button class="btn btn-small" type="button" data-action="edit-announcement" data-id="' + escapeHtml(item.id) + '">Editar</button>' +
      '<button class="btn btn-small" type="button" data-action="delete-announcement" data-id="' + escapeHtml(item.id) + '">Eliminar</button>';
  }

  return '<article class="card">' +
    '<div class="card__top"><div><h2 class="card__title">' + escapeHtml(item.title) + "</h2>" +
    '<p class="card__eyebrow">' + escapeHtml(author) + " · " + escapeHtml(formatDateTime(item.created_at)) + "</p></div>" +
    badge(item.category, categoryTone(item.category)) + "</div>" +
    '<p class="card__desc">' + escapeHtml(item.body) + "</p>" +
    '<div class="tag-row">' +
    (item.is_pinned ? '<span class="tag tag--warn">Fijado</span>' : "") +
    '<button class="btn btn-small' + (read ? " btn-success" : "") + '" type="button" data-action="toggle-read" data-id="' + escapeHtml(item.id) + '">Enterado</button>' +
    '<span class="meta-count">' + escapeHtml(readLabel(readers.length)) + "</span>" +
    "</div>" +
    (commentHtml ? '<div class="comment-list">' + commentHtml + "</div>" : "") +
    '<form class="comment-form" data-comment-for="' + escapeHtml(item.id) + '">' +
    '<input class="input" name="body" maxlength="2000" required placeholder="Escribe un comentario" aria-label="Comentario" />' +
    '<button class="btn btn-primary" type="submit">Enviar</button>' +
    "</form>" +
    (adminActions ? '<div class="card__actions">' + adminActions + "</div>" : "") +
    "</article>";
}

function renderAnnouncements() {
  const filtered = state.announcements.filter(function (item) {
    return state.boardCategory === "Todas" || item.category === state.boardCategory;
  }).sort(function (left, right) {
    return Number(!!right.is_pinned) - Number(!!left.is_pinned);
  });
  renderItems("announcement-list", "empty-announcements", filtered.map(announcementCard).join(""), filtered.length);
}

async function loadAnnouncements() {
  setLoading("announcement-list", "empty-announcements", 3);
  state.announcements = await safeApi("/api/announcements", []);
  renderAnnouncements();
}

function choreStatus(chore) {
  if (chore.is_completed) return { label: "Completada", tone: "success" };
  const days = daysUntil(chore.due_date);
  if (days === null) return { label: "Pendiente", tone: "neutral" };
  if (days < 0) return { label: "Atrasada", tone: "danger" };
  if (days <= 2) return { label: "Por vencer", tone: "warn" };
  return { label: "Pendiente", tone: "info" };
}

function canManageChore(chore) {
  return isAdmin() || chore.assigned_to === state.me.id;
}

function choreCard(chore) {
  const status = choreStatus(chore);
  const assignee = chore.assignee ? "Depto " + chore.assignee.dept_number + " · " + chore.assignee.name : "Sin asignar";
  const days = daysUntil(chore.due_date);
  const dueTone = days !== null && days < 0 ? "tag--danger" : days !== null && days <= 2 ? "tag--warn" : "";
  let actions = "";

  if (canManageChore(chore)) {
    actions += chore.is_completed
      ? '<button class="btn btn-small" type="button" data-action="reopen-chore" data-id="' + escapeHtml(chore.id) + '">Desmarcar</button>'
      : '<button class="btn btn-small btn-primary" type="button" data-action="complete-chore" data-id="' + escapeHtml(chore.id) + '">Completar</button>';
  }
  if (isAdmin()) {
    actions += '<button class="btn btn-small" type="button" data-action="edit-chore" data-id="' + escapeHtml(chore.id) + '">Editar</button>';
    actions += '<button class="btn btn-small" type="button" data-action="delete-chore" data-id="' + escapeHtml(chore.id) + '">Eliminar</button>';
  }

  const completedBy = chore.is_completed && chore.completer
    ? '<p class="card__meta">Completada por ' + escapeHtml(chore.completer.name) + " · " + escapeHtml(formatDateTime(chore.completed_at)) + "</p>"
    : "";

  return '<article class="card' + (chore.is_completed ? " is-done" : "") + '">' +
    '<div class="card__top"><div><h2 class="card__title">' + escapeHtml(chore.title) + "</h2>" +
    '<p class="card__eyebrow">Creada por ' + escapeHtml(chore.creator ? chore.creator.name : "Vecino") + "</p></div>" +
    badge(status.label, status.tone) + "</div>" +
    (chore.description ? '<p class="card__desc">' + escapeHtml(chore.description) + "</p>" : "") +
    '<div class="tag-row">' +
    '<span class="tag">' + escapeHtml(chore.area) + "</span>" +
    '<span class="tag">' + escapeHtml(chore.frequency) + "</span>" +
    '<span class="tag ' + dueTone + '">Vence: ' + escapeHtml(formatDay(chore.due_date)) + "</span>" +
    "</div>" +
    '<p class="card__meta">Responsable: <strong>' + escapeHtml(assignee) + "</strong></p>" +
    completedBy +
    imageHtml(chore.evidence_url, "Evidencia de la tarea") +
    (actions ? '<div class="card__actions">' + actions + "</div>" : "") +
    "</article>";
}

function renderChores() {
  const pending = state.chores.filter(function (chore) { return !chore.is_completed; });
  const overdue = pending.filter(function (chore) {
    const days = daysUntil(chore.due_date);
    return days !== null && days < 0;
  }).length;
  const soon = pending.filter(function (chore) {
    const days = daysUntil(chore.due_date);
    return days !== null && days >= 0 && days <= 2;
  }).length;
  document.getElementById("chore-overdue").textContent = String(overdue);
  document.getElementById("chore-soon").textContent = String(soon);

  const filtered = state.chores.filter(function (chore) {
    if (state.choreFilter === "pending") return !chore.is_completed;
    if (state.choreFilter === "mine") return !chore.is_completed && chore.assigned_to === state.me.id;
    if (state.choreFilter === "completed") return chore.is_completed;
    return true;
  });
  renderItems("chore-list", "empty-chores", filtered.map(choreCard).join(""), filtered.length);
}

async function loadChores() {
  setLoading("chore-list", "empty-chores", 3);
  state.chores = await safeApi("/api/chores?filter=all", []);
  renderChores();
}

function renderSummary() {
  const summary = state.summary || {};
  document.getElementById("stat-balance").textContent = money(summary.cash_balance);
  document.getElementById("stat-collected").textContent = money(summary.collected_this_month);
  document.getElementById("stat-spent").textContent = money(summary.spent_this_month);
  const pending = Number(summary.pending_reviews) || 0;
  const note = document.getElementById("summary-pending");
  note.textContent = pending === 1 ? "1 aportación por revisar" : pending + " aportaciones por revisar";
  note.classList.toggle("hidden", pending === 0);
}

function expenseCard(expense) {
  const creator = expense.creator ? expense.creator.name : "Vecino";
  let actions = "";
  if (isAdmin()) {
    actions = '<div class="card__actions">' +
      '<button class="btn btn-small" type="button" data-action="edit-expense" data-id="' + escapeHtml(expense.id) + '">Editar</button>' +
      '<button class="btn btn-small" type="button" data-action="delete-expense" data-id="' + escapeHtml(expense.id) + '">Eliminar</button>' +
      "</div>";
  }
  return '<article class="card">' +
    '<div class="card__top"><div><h2 class="card__title">' + escapeHtml(expense.title) + "</h2>" +
    '<p class="card__eyebrow">Registrado por ' + escapeHtml(creator) + "</p></div>" +
    badge(expense.category, "info") + "</div>" +
    '<p class="amount">' + escapeHtml(money(expense.amount)) + "</p>" +
    '<p class="card__meta">Fecha: ' + escapeHtml(formatDay(expense.spent_on)) + "</p>" +
    imageHtml(expense.receipt_url, "Ticket del gasto") +
    actions +
    "</article>";
}

function contributionStatusTone(status) {
  if (status === "Aprobada") return "success";
  if (status === "Rechazada") return "danger";
  return "warn";
}

function contributionCard(contribution) {
  const resident = contribution.resident;
  const label = resident ? "Depto " + resident.dept_number + " · " + resident.name : "Vecino";
  let actions = "";
  if (isAdmin() && contribution.status === "Pendiente") {
    actions = '<div class="card__actions">' +
      '<button class="btn btn-small btn-success" type="button" data-action="review-contribution" data-id="' + escapeHtml(contribution.id) + '" data-review="approve">Aprobar</button>' +
      '<button class="btn btn-small" type="button" data-action="review-contribution" data-id="' + escapeHtml(contribution.id) + '" data-review="reject">Rechazar</button>' +
      "</div>";
  }
  const approver = contribution.approver ? '<p class="card__meta">Revisado por ' + escapeHtml(contribution.approver.name) + "</p>" : "";
  return '<article class="card">' +
    '<div class="card__top"><div><p class="card__eyebrow">' + escapeHtml(label) + "</p>" +
    '<h2 class="card__title">' + escapeHtml(contribution.kind) + "</h2></div>" +
    badge(contribution.status, contributionStatusTone(contribution.status)) + "</div>" +
    '<p class="amount">' + escapeHtml(money(contribution.amount)) + "</p>" +
    '<p class="card__meta">Periodo: ' + escapeHtml(contribution.period) + "</p>" +
    approver +
    imageHtml(contribution.proof_url, "Comprobante de aportación") +
    actions +
    "</article>";
}

function renderExpenses() {
  renderItems("expense-list", "empty-expenses", state.expenses.map(expenseCard).join(""), state.expenses.length);
}

function renderContributions() {
  renderItems("contribution-list", "empty-contributions", state.contributions.map(contributionCard).join(""), state.contributions.length);
}

async function loadFinance() {
  setLoading("expense-list", "empty-expenses", 2);
  setLoading("contribution-list", "empty-contributions", 2);
  const results = await Promise.all([
    safeApi("/api/finance/summary", null),
    safeApi("/api/expenses", []),
    safeApi("/api/contributions", [])
  ]);
  state.summary = results[0];
  state.expenses = results[1];
  state.contributions = results[2];
  renderSummary();
  renderExpenses();
  renderContributions();
}

function residentCard(resident) {
  const paid = Number(resident.amount_paid) || 0;
  const statusTone = resident.account_status === "Al corriente" ? "success" : "warn";
  const phone = resident.phone ? '<a href="tel:' + escapeHtml(String(resident.phone).replace(/[^\d+]/g, "")) + '">' + escapeHtml(resident.phone) + "</a>" : "Sin registrar";
  const emergency = resident.emergency_name || resident.emergency_phone
    ? escapeHtml(resident.emergency_name || "Sin nombre") + (resident.emergency_phone ? " · " + escapeHtml(resident.emergency_phone) : "")
    : "Sin registrar";
  let actions = "";
  if (isAdmin()) {
    actions = '<div class="card__actions">' +
      '<button class="btn btn-small" type="button" data-action="edit-resident" data-id="' + escapeHtml(resident.id) + '">Editar departamento</button>' +
      (resident.id === state.me.id ? "" :
        '<button class="btn btn-small btn-danger" type="button" data-action="delete-resident" data-id="' + escapeHtml(resident.id) + '">Eliminar</button>') +
      "</div>";
  }
  return '<article class="card">' +
    '<div class="card__top">' +
    "<div>" + avatarHtml(resident) +
    '<h2 class="card__title">Depto ' + escapeHtml(resident.dept_number) + " · " + escapeHtml(resident.name) + "</h2>" +
    '<p class="card__meta">' + escapeHtml(roleLabel(resident.role)) + "</p></div>" +
    badge(resident.account_status, statusTone) + "</div>" +
    '<p class="card__meta">Teléfono: ' + phone + "</p>" +
    '<p class="card__meta">Emergencia: ' + emergency + "</p>" +
    '<p class="card__meta">Pagado este mes: <strong>' + escapeHtml(money(paid)) + "</strong></p>" +
    actions +
    "</article>";
}

function renderResidents() {
  const sorted = state.residents.slice().sort(function (left, right) {
    return String(left.dept_number).localeCompare(String(right.dept_number));
  });
  renderItems("resident-list", "empty-residents", sorted.map(residentCard).join(""), sorted.length);
}

async function loadResidents() {
  setLoading("resident-list", "empty-residents", 3);
  state.residents = await safeApi("/api/residents", []);
  renderResidents();
}

function parkingStatusTone(status) {
  if (status === "Disponible") return "success";
  if (status === "Prestado") return "info";
  return "warn";
}

function canManageSpot(spot) {
  return isAdmin() || spot.owner_id === state.me.id;
}

function parkingCard(spot) {
  const owner = spot.owner ? "Depto " + spot.owner.dept_number + " · " + spot.owner.name : "Sin dueño asignado";
  const borrower = spot.borrower ? '<p class="card__meta">Prestado a: <strong>' + escapeHtml("Depto " + spot.borrower.dept_number + " · " + spot.borrower.name) + "</strong></p>" : "";
  const loanUntil = spot.loan_until ? '<p class="card__meta">Hasta: ' + escapeHtml(formatDay(spot.loan_until)) + "</p>" : "";
  const note = spot.note ? '<p class="card__meta">Nota: ' + escapeHtml(spot.note) + "</p>" : "";
  let actions = "";

  if (spot.status === "Disponible" && spot.owner_id !== state.me.id) {
    actions += '<button class="btn btn-small btn-primary" type="button" data-action="request-parking" data-id="' + escapeHtml(spot.id) + '">Solicitar</button>';
  }
  if (spot.status === "Solicitado" && canManageSpot(spot)) {
    actions += '<button class="btn btn-small btn-success" type="button" data-action="approve-parking" data-id="' + escapeHtml(spot.id) + '">Aprobar</button>';
  }
  if (spot.status === "Prestado" && canManageSpot(spot)) {
    actions += '<button class="btn btn-small" type="button" data-action="release-parking" data-id="' + escapeHtml(spot.id) + '">Liberar</button>';
  }
  if (isAdmin()) {
    actions += '<button class="btn btn-small" type="button" data-action="edit-parking" data-id="' + escapeHtml(spot.id) + '">Editar</button>';
    actions += '<button class="btn btn-small" type="button" data-action="delete-parking" data-id="' + escapeHtml(spot.id) + '">Eliminar</button>';
  }

  return '<article class="card">' +
    '<div class="card__top"><div><span class="spot-code">' + escapeHtml(spot.code) + "</span>" +
    '<p class="card__meta">' + escapeHtml(spot.location) + " · " + escapeHtml(spot.spot_type) + "</p></div>" +
    badge(spot.status, parkingStatusTone(spot.status)) + "</div>" +
    '<p class="card__meta">Dueño: <strong>' + escapeHtml(owner) + "</strong></p>" +
    borrower + loanUntil + note +
    (actions ? '<div class="card__actions">' + actions + "</div>" : "") +
    "</article>";
}

function renderParking() {
  const filtered = state.parking.filter(function (spot) {
    return state.parkingFilter === "all" || spot.status === state.parkingFilter;
  });
  renderItems("parking-list", "empty-parking", filtered.map(parkingCard).join(""), filtered.length);
}

async function loadParking() {
  setLoading("parking-list", "empty-parking", 3);
  state.parking = await safeApi("/api/parking", []);
  renderParking();
}

function setFinanceTab(tab) {
  state.financeTab = tab;
  document.getElementById("panel-expenses").classList.toggle("hidden", tab !== "expenses");
  document.getElementById("panel-contributions").classList.toggle("hidden", tab !== "contributions");
  activateChip("finance-tabs", "finance-tab", tab);
  document.querySelector(".panel-head p").textContent = tab === "expenses"
    ? "Registros de la administración vecinal"
    : "Aportaciones de los departamentos";
  updateActionButtons();
}

function setNeighborsTab(tab) {
  state.neighborsTab = tab;
  document.getElementById("panel-directory").classList.toggle("hidden", tab !== "directory");
  document.getElementById("panel-parking").classList.toggle("hidden", tab !== "parking");
  activateChip("neighbors-tabs", "neighbors-tab", tab);
  updateActionButtons();
}

function fillResidentSelect(select, includeEmpty) {
  if (!select) return;
  const previous = select.value;
  const sorted = state.residents.slice().sort(function (left, right) {
    return String(left.dept_number).localeCompare(String(right.dept_number));
  });
  let html = includeEmpty ? '<option value="">Sin asignar</option>' : "";
  html += sorted.map(function (resident) {
    return '<option value="' + escapeHtml(resident.id) + '">Depto ' + escapeHtml(resident.dept_number) + " · " + escapeHtml(resident.name) + "</option>";
  }).join("");
  select.innerHTML = html;
  if (previous && sorted.some(function (resident) { return String(resident.id) === previous; })) {
    select.value = previous;
  }
}

function openAnnouncementSheet(item) {
  const form = document.querySelector('[data-form="announcement"]');
  form.reset();
  state.editing.announcementId = item ? item.id : null;
  document.getElementById("announcement-sheet-title").textContent = item ? "Editar anuncio" : "Nuevo anuncio";
  document.getElementById("announcement-submit").textContent = item ? "Guardar cambios" : "Publicar anuncio";
  if (item) {
    form.elements["title"].value = item.title;
    form.elements["body"].value = item.body;
    form.elements["category"].value = item.category;
    form.elements["is_pinned"].checked = !!item.is_pinned;
  }
  openSheet("announcement-sheet");
}

function openChoreSheet(item) {
  const form = document.querySelector('[data-form="chore"]');
  form.reset();
  state.editing.choreId = item ? item.id : null;
  fillResidentSelect(document.getElementById("chore-assignee"), true);
  document.getElementById("chore-sheet-title").textContent = item ? "Editar tarea" : "Nueva tarea";
  document.getElementById("chore-submit").textContent = item ? "Guardar cambios" : "Guardar tarea";
  if (item) {
    form.elements["title"].value = item.title;
    form.elements["description"].value = item.description || "";
    form.elements["area"].value = item.area;
    form.elements["frequency"].value = item.frequency;
    form.elements["due_date"].value = item.due_date || "";
    form.elements["assigned_to"].value = item.assigned_to == null ? "" : String(item.assigned_to);
  }
  openSheet("chore-sheet");
}

function openCompleteSheet(id) {
  const chore = state.chores.find(function (item) { return item.id === id; });
  if (!chore) return;
  state.editing.choreId = id;
  document.querySelector('[data-form="complete"]').reset();
  document.getElementById("complete-chore-name").textContent = chore.title;
  openSheet("complete-sheet");
}

function openExpenseSheet(item) {
  const form = document.querySelector('[data-form="expense"]');
  form.reset();
  state.editing.expenseId = item ? item.id : null;
  document.getElementById("expense-sheet-title").textContent = item ? "Editar gasto" : "Registrar gasto";
  document.getElementById("expense-submit").textContent = item ? "Guardar cambios" : "Guardar gasto";
  form.elements["spent_on"].value = item ? item.spent_on : localDate();
  if (item) {
    form.elements["title"].value = item.title;
    form.elements["category"].value = item.category;
    form.elements["amount"].value = item.amount;
  }
  openSheet("expense-sheet");
}

function openContributionSheet() {
  const form = document.querySelector('[data-form="contribution"]');
  form.reset();
  form.elements["period"].value = localDate().slice(0, 7);
  openSheet("contribution-sheet");
}

function openResidentSheet(id) {
  const resident = id ? state.residents.find(function (item) { return item.id === id; }) : null;
  if (id && !resident) return;
  const form = document.querySelector('[data-form="resident"]');
  form.reset();
  state.editing.residentId = resident ? resident.id : null;
  document.getElementById("resident-sheet-title").textContent = resident ? "Editar departamento" : "Nuevo departamento";
  document.getElementById("resident-sheet-name").textContent = resident
    ? "Depto " + resident.dept_number + " · " + resident.name
    : "Crea un departamento y asígnale un PIN de acceso.";
  document.getElementById("resident-submit").textContent = resident ? "Guardar cambios" : "Guardar departamento";
  if (resident) {
    form.elements["dept_number"].value = resident.dept_number;
    form.elements["name"].value = resident.name;
    form.elements["role"].value = resident.role;
    form.elements["pin"].placeholder = "Dejar en blanco para no cambiar";
    form.elements["phone"].value = resident.phone || "";
    form.elements["emergency_name"].value = resident.emergency_name || "";
    form.elements["emergency_phone"].value = resident.emergency_phone || "";
  } else {
    form.elements["role"].value = "resident";
    form.elements["pin"].placeholder = "Mínimo 4 caracteres";
  }
  openSheet("resident-sheet");
}

function openParkingSheet(item) {
  const form = document.querySelector('[data-form="parking"]');
  form.reset();
  state.editing.parkingId = item ? item.id : null;
  fillResidentSelect(document.getElementById("parking-owner"), true);
  document.getElementById("parking-sheet-title").textContent = item ? "Editar lugar" : "Registrar lugar";
  document.getElementById("parking-submit").textContent = item ? "Guardar cambios" : "Guardar lugar";
  if (item) {
    form.elements["code"].value = item.code;
    form.elements["location"].value = item.location;
    form.elements["spot_type"].value = item.spot_type;
    form.elements["owner_id"].value = item.owner_id == null ? "" : String(item.owner_id);
    form.elements["loan_until"].value = item.loan_until || "";
    form.elements["note"].value = item.note || "";
  }
  openSheet("parking-sheet");
}

function formText(form, name) {
  const value = new FormData(form).get(name);
  return String(value == null ? "" : value).trim();
}

function formFile(form, name) {
  const input = form.elements[name];
  return input && input.files && input.files[0] ? input.files[0] : null;
}

function readFileAsDataUrl(file) {
  return new Promise(function (resolve, reject) {
    const reader = new FileReader();
    reader.onload = function () { resolve(String(reader.result)); };
    reader.onerror = function () { reject(new Error("No se pudo leer la imagen")); };
    reader.readAsDataURL(file);
  });
}

function drawToDataUrl(source, maxSize, quality) {
  return new Promise(function (resolve, reject) {
    const image = new Image();
    image.onload = function () {
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;
      const scale = Math.min(1, maxSize / Math.max(width, height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(width * scale));
      canvas.height = Math.max(1, Math.round(height * scale));
      const context = canvas.getContext("2d");
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    image.onerror = function () { reject(new Error("No se pudo procesar la imagen")); };
    image.src = source;
  });
}

async function compressImage(file) {
  if (!file) return null;
  const source = await readFileAsDataUrl(file);
  let result = await drawToDataUrl(source, 900, 0.82);
  if (result.length > 1500000) result = await drawToDataUrl(source, 640, 0.7);
  if (result.length > 1500000) result = await drawToDataUrl(source, 420, 0.6);
  return result;
}

async function saveAnnouncement(form) {
  const payload = {
    title: formText(form, "title"),
    body: formText(form, "body"),
    category: form.elements["category"].value,
    is_pinned: isAdmin() && form.elements["is_pinned"].checked
  };
  if (!payload.title || !payload.body) {
    showToast("Completa el título y el mensaje");
    return;
  }
  const id = state.editing.announcementId;
  await api(id ? "/api/announcements/" + id : "/api/announcements", {
    method: id ? "PATCH" : "POST",
    body: payload
  });
  closeSheet("announcement-sheet");
  showToast(id ? "Anuncio actualizado" : "Anuncio publicado");
  clearApiCache();
  await loadAnnouncements();
}

async function saveChore(form) {
  const assigned = form.elements["assigned_to"].value;
  const payload = {
    title: formText(form, "title"),
    description: formText(form, "description") || null,
    area: form.elements["area"].value,
    frequency: form.elements["frequency"].value,
    due_date: form.elements["due_date"].value || null,
    assigned_to: assigned ? Number(assigned) : null
  };
  if (!payload.title) {
    showToast("Escribe el título de la tarea");
    return;
  }
  const id = state.editing.choreId;
  await api(id ? "/api/chores/" + id : "/api/chores", {
    method: id ? "PATCH" : "POST",
    body: payload
  });
  closeSheet("chore-sheet");
  showToast(id ? "Tarea actualizada" : "Tarea creada");
  clearApiCache();
  await loadChores();
}

async function completeChore(form) {
  const id = state.editing.choreId;
  const evidence = await compressImage(formFile(form, "evidence"));
  await api("/api/chores/" + id + "/complete", {
    method: "POST",
    body: { evidence_url: evidence || null }
  });
  closeSheet("complete-sheet");
  showToast("Tarea completada");
  clearApiCache();
  await loadChores();
}

async function saveExpense(form) {
  const payload = {
    title: formText(form, "title"),
    category: form.elements["category"].value,
    amount: Number(form.elements["amount"].value),
    spent_on: form.elements["spent_on"].value
  };
  if (!payload.title || !(payload.amount > 0) || !payload.spent_on) {
    showToast("Completa el título, el monto y la fecha");
    return;
  }
  const receipt = await compressImage(formFile(form, "receipt"));
  if (receipt) payload.receipt_url = receipt;
  const id = state.editing.expenseId;
  await api(id ? "/api/expenses/" + id : "/api/expenses", {
    method: id ? "PATCH" : "POST",
    body: payload
  });
  closeSheet("expense-sheet");
  showToast(id ? "Gasto actualizado" : "Gasto registrado");
  clearApiCache();
  await Promise.all([loadFinance(), loadResidents()]);
}

async function saveContribution(form) {
  const period = formText(form, "period");
  const amount = Number(form.elements["amount"].value);
  if (!/^\d{4}-\d{2}$/.test(period) || !(amount > 0)) {
    showToast("Revisa el periodo y el monto");
    return;
  }
  const payload = {
    kind: form.elements["kind"].value,
    period: period,
    amount: amount
  };
  const proof = await compressImage(formFile(form, "proof"));
  if (proof) payload.proof_url = proof;
  await api("/api/contributions", { method: "POST", body: payload });
  closeSheet("contribution-sheet");
  showToast("Aportación registrada");
  clearApiCache();
  await Promise.all([loadFinance(), loadResidents()]);
}

async function saveResident(form) {
  const id = state.editing.residentId;
  const pin = formText(form, "pin");
  const deptLetter = formText(form, "dept_number").toUpperCase();
  const name = formText(form, "name");
  if (!/^[A-J]$/.test(deptLetter) || !name || (!id && !pin)) {
    showToast("Usa una letra de la A a la J y completa nombre y PIN");
    return;
  }
  const payload = {
    dept_number: deptLetter,
    name: name,
    role: form.elements["role"].value,
    phone: formText(form, "phone") || null,
    emergency_name: formText(form, "emergency_name") || null,
    emergency_phone: formText(form, "emergency_phone") || null
  };
  if (pin) payload.pin = pin;
  await api(id ? "/api/residents/" + id : "/api/residents", {
    method: id ? "PATCH" : "POST",
    body: payload
  });
  closeSheet("resident-sheet");
  showToast(id ? "Departamento actualizado" : "Departamento creado");
  clearApiCache();
  await Promise.all([loadResidents(), loadProfiles()]);
}

async function saveParking(form) {
  const owner = form.elements["owner_id"].value;
  const payload = {
    code: formText(form, "code"),
    location: formText(form, "location"),
    spot_type: form.elements["spot_type"].value,
    owner_id: owner ? Number(owner) : null,
    loan_until: form.elements["loan_until"].value || null,
    note: formText(form, "note") || null
  };
  if (!payload.code || !payload.location) {
    showToast("Completa el código y la ubicación");
    return;
  }
  const id = state.editing.parkingId;
  await api(id ? "/api/parking/" + id : "/api/parking", {
    method: id ? "PATCH" : "POST",
    body: payload
  });
  closeSheet("parking-sheet");
  showToast(id ? "Lugar actualizado" : "Lugar registrado");
  clearApiCache();
  await loadParking();
}

const FORM_HANDLERS = {
  announcement: saveAnnouncement,
  chore: saveChore,
  complete: completeChore,
  expense: saveExpense,
  contribution: saveContribution,
  resident: saveResident,
  parking: saveParking
};

async function submitForm(form) {
  const handler = FORM_HANDLERS[form.dataset.form];
  if (!handler) return;
  const button = form.querySelector('[type="submit"]');
  if (button) button.disabled = true;
  try {
    await handler(form);
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

async function submitComment(id, form) {
  const body = formText(form, "body");
  if (!body) return;
  try {
    await api("/api/announcements/" + id + "/comments", { method: "POST", body: { body: body } });
    form.reset();
    showToast("Comentario publicado");
    clearApiCache();
    await loadAnnouncements();
  } catch (error) {
    showToast(error.message);
  }
}

function askDelete(title, description, action) {
  state.confirmAction = action;
  document.getElementById("confirm-title").textContent = title;
  document.getElementById("confirm-desc").textContent = description;
  document.getElementById("confirm-modal").classList.add("open");
}

async function removeEntity(path, message, loaders) {
  try {
    await api(path, { method: "DELETE" });
    showToast(message);
    clearApiCache();
    await Promise.all(loaders.map(function (loader) { return loader(); }));
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleAnnouncementRead(id) {
  const item = state.announcements.find(function (announcement) { return announcement.id === id; });
  if (!item) return;
  const readers = Array.isArray(item.read_by) ? item.read_by : [];
  const method = readers.indexOf(state.me.id) !== -1 ? "DELETE" : "POST";
  try {
    await api("/api/announcements/" + id + "/read", { method: method });
    clearApiCache();
    await loadAnnouncements();
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteComment(announcementId, commentId) {
  await removeEntity("/api/announcements/" + announcementId + "/comments/" + commentId, "Comentario eliminado", [loadAnnouncements]);
}

async function reopenChore(id) {
  try {
    await api("/api/chores/" + id + "/reopen", { method: "POST" });
    showToast("Tarea reabierta");
    clearApiCache();
    await loadChores();
  } catch (error) {
    showToast(error.message);
  }
}

async function reviewContribution(id, action) {
  try {
    await api("/api/contributions/" + id + "/review", { method: "POST", body: { action: action } });
    showToast(action === "approve" ? "Aportación aprobada" : "Aportación rechazada");
    clearApiCache();
    await Promise.all([loadFinance(), loadResidents()]);
  } catch (error) {
    showToast(error.message);
  }
}

async function changeParking(id, action, message) {
  try {
    await api("/api/parking/" + id + "/" + action, { method: "POST" });
    showToast(message);
    clearApiCache();
    await loadParking();
  } catch (error) {
    showToast(error.message);
  }
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST", skipAuthRedirect: true });
  } catch (error) {}
  state.me = null;
  state.announcements = [];
  state.chores = [];
  state.expenses = [];
  state.contributions = [];
  state.residents = [];
  state.parking = [];
  state.summary = null;
  state.confirmAction = null;
  clearApiCache();
  closeAllSheets();
  updateHeader();
  showScreen("login");
  resetPinPanel();
  await loadProfiles();
}

async function handleClick(event) {
  const target = event.target.closest ? event.target.closest("[data-action]") : null;
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;

  if (action === "close-sheet") {
    if (event.target === target) closeSheet(id);
    return;
  }

  switch (action) {
    case "login-profile":
      selectDepartment(Number(id));
      break;
    case "pin-back":
      resetPinPanel();
      break;
    case "pin-key":
      pressKey(id);
      break;
    case "logout":
      logout();
      break;
    case "nav":
      showScreen(id);
      break;
    case "board-filter":
      state.boardCategory = id;
      activateChip("board-filters", "board-filter", id);
      renderAnnouncements();
      break;
    case "chore-filter":
      state.choreFilter = id;
      activateChip("chore-filters", "chore-filter", id);
      renderChores();
      break;
    case "parking-filter":
      state.parkingFilter = id;
      activateChip("parking-filters", "parking-filter", id);
      renderParking();
      break;
    case "finance-tab":
      setFinanceTab(id);
      break;
    case "neighbors-tab":
      setNeighborsTab(id);
      break;
    case "new-announcement":
      openAnnouncementSheet(null);
      break;
    case "edit-announcement": {
      const item = state.announcements.find(function (announcement) { return announcement.id === Number(id); });
      if (item) openAnnouncementSheet(item);
      break;
    }
    case "delete-announcement":
      askDelete("¿Eliminar el anuncio?", "Desaparecerá de la pizarra para todos los vecinos.", function () {
        return removeEntity("/api/announcements/" + id, "Anuncio eliminado", [loadAnnouncements]);
      });
      break;
    case "toggle-read":
      toggleAnnouncementRead(Number(id));
      break;
    case "delete-comment":
      askDelete("¿Eliminar el comentario?", "El comentario dejará de verse en la pizarra.", function () {
        return deleteComment(Number(target.dataset.parent), Number(id));
      });
      break;
    case "new-chore":
      openChoreSheet(null);
      break;
    case "edit-chore": {
      const chore = state.chores.find(function (item) { return item.id === Number(id); });
      if (chore) openChoreSheet(chore);
      break;
    }
    case "delete-chore":
      askDelete("¿Eliminar la tarea?", "La tarea y su historial se borrarán definitivamente.", function () {
        return removeEntity("/api/chores/" + id, "Tarea eliminada", [loadChores]);
      });
      break;
    case "complete-chore":
      openCompleteSheet(Number(id));
      break;
    case "reopen-chore":
      reopenChore(Number(id));
      break;
    case "new-expense":
      openExpenseSheet(null);
      break;
    case "edit-expense": {
      const expense = state.expenses.find(function (item) { return item.id === Number(id); });
      if (expense) openExpenseSheet(expense);
      break;
    }
    case "delete-expense":
      askDelete("¿Eliminar el gasto?", "El egreso dejará de contarse en el resumen.", function () {
        return removeEntity("/api/expenses/" + id, "Gasto eliminado", [loadFinance, loadResidents]);
      });
      break;
    case "new-contribution":
      openContributionSheet();
      break;
    case "review-contribution":
      reviewContribution(Number(id), target.dataset.review);
      break;
    case "new-resident":
      openResidentSheet(null);
      break;
    case "edit-resident":
      openResidentSheet(Number(id));
      break;
    case "delete-resident":
      askDelete("¿Eliminar el departamento?", "Se borrarán sus anuncios y aportaciones; las tareas y gastos pasarán al admin actual.", function () {
        return removeEntity("/api/residents/" + id, "Departamento eliminado", [loadAllData, loadProfiles]);
      });
      break;
    case "new-parking":
      openParkingSheet(null);
      break;
    case "edit-parking": {
      const spot = state.parking.find(function (item) { return item.id === Number(id); });
      if (spot) openParkingSheet(spot);
      break;
    }
    case "delete-parking":
      askDelete("¿Eliminar el lugar?", "El estacionamiento se quitará del directorio.", function () {
        return removeEntity("/api/parking/" + id, "Lugar eliminado", [loadParking]);
      });
      break;
    case "request-parking":
      changeParking(Number(id), "request", "Solicitud enviada");
      break;
    case "approve-parking":
      changeParking(Number(id), "approve", "Préstamo aprobado");
      break;
    case "release-parking":
      changeParking(Number(id), "release", "Lugar liberado");
      break;
    case "confirm-cancel":
      state.confirmAction = null;
      document.getElementById("confirm-modal").classList.remove("open");
      break;
    case "confirm-accept": {
      const action = state.confirmAction;
      state.confirmAction = null;
      document.getElementById("confirm-modal").classList.remove("open");
      if (action) await action();
      break;
    }
    default:
      break;
  }
}

function bindEvents() {
  document.addEventListener("click", function (event) {
    handleClick(event);
  });

  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (form.dataset.form) {
      event.preventDefault();
      submitForm(form);
    } else if (form.dataset.commentFor) {
      event.preventDefault();
      submitComment(Number(form.dataset.commentFor), form);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    closeAllSheets();
    state.confirmAction = null;
    document.getElementById("confirm-modal").classList.remove("open");
  });
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" })
    .then(function (registration) { return registration.update(); })
    .catch(function () {});
}

async function bootstrap() {
  bindEvents();
  registerServiceWorker();
  renderPinDots();
  showScreen("login");
  await loadProfiles();
  try {
    const me = await api("/api/auth/me", { skipAuthRedirect: true });
    await afterLogin(me);
  } catch (error) {
    state.me = null;
  }
}

bootstrap();

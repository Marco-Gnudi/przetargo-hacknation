const dropzone = document.querySelector("#dropzone");
const fileInput = document.querySelector("#file-input");
const fileList = document.querySelector("#file-list");
const inputMessage = document.querySelector("#input-message");
const submitButton = document.querySelector("#submit");
const resetButton = document.querySelector("#reset");
const summary = document.querySelector("#summary");
const detail = document.querySelector("#detail");
const resultsBody = document.querySelector("#results-body");
const modeButtons = document.querySelectorAll("[data-mode]");
const langButtons = document.querySelectorAll("[data-lang]");

const copy = {
  pl: {
    title: "PrzetarGO",
    tagline: "Odwołania KIO w danych",
    language: "Język",
    heroTitle: "Odczytaj odwołanie z dokumentów",
    heroText: "Dodaj pliki PDF jednej sprawy. Odwołanie, pełnomocnictwo i potwierdzenie przelewu mogą iść razem.",
    processing: "Przetwarzanie",
    processingHint: "Wybierz sposób odczytu tej sprawy.",
    modeRegular: "Regularne",
    modeRegularHint: "Bez modelu językowego",
    modeBielik: "Bielik",
    modeBielikHint: "Model językowy",
    documents: "Dokumenty",
    dropAria: "Dodaj pliki PDF. Upuść je tutaj albo naciśnij Enter, aby je wskazać.",
    dropTitle: "Upuść pliki PDF",
    dropHint: "albo wskaż je na komputerze. Jeden lub więcej plików PDF.",
    process: "Przetwórz dokumenty",
    summary: "Podsumowanie",
    summaryEmpty: "Kompletność i brakujące informacje pojawią się po przetworzeniu sprawy.",
    fields: "Wyodrębnione pola",
    fieldsEmpty: "Sekcje i wartości pól każdego dokumentu pojawią się tutaj.",
    cases: "Sprawy",
    casesHint: "Każdy zestaw dokumentów przesłany w tej sesji.",
    clear: "Wyczyść sesję",
    colPdfs: "Liczba PDF",
    colCompany: "Firma",
    colStatus: "Status",
    noCases: "Brak spraw.",
    remove: "Usuń",
    pdfOnly: "Można dodać tylko pliki PDF. Pominięto: {names}",
    already: "Te pliki PDF są już dodane.",
    pending: "Jeszcze nieprzetworzone",
    working: "Przetwarzanie…",
    recognised: "Rozpoznano {done} z {total}.",
    unrecognised: "Nierozpoznany dokument",
    noFields: "Brak pól dla tego typu.",
    missing: "Brakujące pola",
    failed: "Nie udało się przetworzyć dokumentów.",
    statusDone: "Gotowe",
    statusPartial: "Częściowo",
    statusNone: "Nierozpoznane",
    statusFailed: "Błąd",
    sourceRule: "reguła",
    sourceLlm: "bielik",
    footer: "Hacknation 2026 projekt dla Urzędu Zamówień Publicznych",
  },
  en: {
    title: "PrzetarGO",
    tagline: "KIO appeals as structured data",
    language: "Language",
    heroTitle: "Read an appeal from its documents",
    heroText: "Add the PDFs for one case. The appeal, power of attorney, and transfer confirmation can go in together.",
    processing: "Processing",
    processingHint: "Choose how this case will be read.",
    modeRegular: "Regular",
    modeRegularHint: "No language model",
    modeBielik: "Bielik",
    modeBielikHint: "Language model",
    documents: "Documents",
    dropAria: "Add PDF files. Drop them here or press Enter to browse.",
    dropTitle: "Drop PDFs here",
    dropHint: "or browse files on this computer. One or more PDFs.",
    process: "Process documents",
    summary: "Summary",
    summaryEmpty: "Completeness and missing information will show here after a case is processed.",
    fields: "Extracted fields",
    fieldsEmpty: "Sections and field values for each document will show here.",
    cases: "Cases",
    casesHint: "Every set of documents submitted in this session.",
    clear: "Clear session",
    colPdfs: "PDFs",
    colCompany: "Company",
    colStatus: "Status",
    noCases: "No cases yet.",
    remove: "Remove",
    pdfOnly: "Only PDF files can be added. Skipped: {names}",
    already: "Those PDFs are already attached.",
    pending: "Not processed yet",
    working: "Processing…",
    recognised: "Recognised {done} of {total}.",
    unrecognised: "Unrecognised document",
    noFields: "No fields for this type yet.",
    missing: "Missing fields",
    failed: "The documents could not be processed.",
    statusDone: "Done",
    statusPartial: "Partial",
    statusNone: "Unrecognised",
    statusFailed: "Failed",
    sourceRule: "rule",
    sourceLlm: "bielik",
    footer: "HackNation 2026 project for the Public Procurement Office",
  },
};

const API_URL = "http://127.0.0.1:8000";

const state = {
  mode: "regular",
  lang: savedLang(),
  files: [],
  submissions: [],
  nextId: 1,
  notice: null,
  busy: false,
};

langButtons.forEach((button) => {
  button.addEventListener("click", () => setLang(button.dataset.lang));
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

dropzone.addEventListener("click", (event) => {
  if (event.target.closest(".remove-file")) return;
  fileInput.click();
});

dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

["dragover", "drop"].forEach((name) => {
  document.addEventListener(name, (event) => {
    event.preventDefault();
  });
});

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragover");
  });
});

["dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  addFiles(event.dataTransfer.files);
});

fileInput.addEventListener("change", () => {
  addFiles(fileInput.files);
  fileInput.value = "";
});

submitButton.addEventListener("click", submitFiles);
resetButton.addEventListener("click", resetAll);

function savedLang() {
  try {
    return localStorage.getItem("odwolania-lang") === "en" ? "en" : "pl";
  } catch {
    return "pl";
  }
}

function t(key) {
  return copy[state.lang][key];
}

function setLang(lang) {
  state.lang = lang === "en" ? "en" : "pl";
  try {
    localStorage.setItem("odwolania-lang", state.lang);
  } catch {
    // The page still switches for this visit when storage is blocked.
  }
  applyCopy();
}

function applyCopy() {
  document.documentElement.lang = state.lang;
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  langButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  });
  renderNotice();
  renderFiles();
  renderOutputs();
}

function summarySentence(submission) {
  const files = submission.result.files;
  const done = files.filter((file) => file.type).length;
  const line = t("recognised").replace("{done}", String(done)).replace("{total}", String(files.length));
  const missing = [];
  files.forEach((file) => {
    nullFields(file.json).forEach((field) => missing.push(`${file.filename}: ${field}`));
  });
  if (missing.length === 0) return line;
  return `${line} ${t("missing")}: ${missing.join(", ")}.`;
}

function renderNotice() {
  if (!state.notice) {
    inputMessage.textContent = "";
    return;
  }
  const names = state.notice.names ? state.notice.names.join(", ") : "";
  inputMessage.textContent = t(state.notice.key).replace("{names}", names);
}

function selectMode(mode) {
  state.mode = mode;
  modeButtons.forEach((button) => {
    const selected = button.dataset.mode === mode;
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

function addFiles(fileListLike) {
  const incoming = Array.from(fileListLike || []);
  if (incoming.length === 0) return;

  const rejected = [];
  let added = 0;

  incoming.forEach((file) => {
    if (!isPdf(file)) {
      rejected.push(file.name);
      return;
    }
    const duplicate = state.files.some(
      (item) =>
        item.file.name === file.name &&
        item.file.size === file.size &&
        item.file.lastModified === file.lastModified
    );
    if (duplicate) return;
    state.files.push({ id: state.nextId++, file });
    added += 1;
  });

  if (rejected.length > 0) {
    state.notice = { key: "pdfOnly", names: rejected };
  } else if (added === 0) {
    state.notice = { key: "already" };
  } else {
    state.notice = null;
  }
  renderNotice();

  renderFiles();
}

function isPdf(file) {
  const name = file.name.toLowerCase();
  return file.type === "application/pdf" || name.endsWith(".pdf");
}

function renderFiles() {
  fileList.replaceChildren();
  if (state.files.length === 0) {
    fileList.hidden = true;
  } else {
    fileList.hidden = false;
    state.files.forEach((item) => {
      const row = document.createElement("li");
      const name = document.createElement("span");
      name.className = "file-name";
      name.textContent = item.file.name;
      const size = document.createElement("span");
      size.className = "file-size";
      size.textContent = formatSize(item.file.size);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-file";
      remove.textContent = t("remove");
      remove.addEventListener("click", (event) => {
        event.stopPropagation();
        state.files = state.files.filter((entry) => entry.id !== item.id);
        state.notice = null;
        renderNotice();
        renderFiles();
      });
      row.append(name, size, remove);
      fileList.append(row);
    });
  }
  submitButton.disabled = state.busy || state.files.length === 0;
  submitButton.textContent = state.busy ? t("working") : t("process");
}

async function submitFiles() {
  if (state.files.length === 0 || state.busy) return;

  const files = state.files.slice();
  const mode = state.mode;
  const body = new FormData();
  body.append("mode", mode);
  files.forEach((item) => body.append("files", item.file, item.file.name));

  state.busy = true;
  state.notice = null;
  renderNotice();
  renderFiles();

  let result = null;
  let error = false;
  try {
    const response = await fetch(`${API_URL}/api/process`, { method: "POST", body });
    if (!response.ok) throw new Error(String(response.status));
    result = await response.json();
  } catch {
    error = true;
  }

  state.submissions.push({
    count: files.length,
    names: files.map((item) => item.file.name),
    mode,
    result,
    error,
  });
  if (!error) state.files = [];
  state.busy = false;
  renderNotice();
  renderFiles();
  renderOutputs();
}

function renderOutputs() {
  const latest = state.submissions[state.submissions.length - 1];
  summary.replaceChildren();
  detail.replaceChildren();
  if (!latest) {
    summary.append(placeholder("summaryEmpty"));
    detail.append(placeholder("fieldsEmpty"));
  } else if (latest.error || !latest.result) {
    const text = document.createElement("p");
    text.className = "summary-text";
    text.textContent = t("failed");
    summary.append(text);
    detail.append(placeholder("fieldsEmpty"));
  } else {
    const text = document.createElement("p");
    text.className = "summary-text";
    text.textContent = summarySentence(latest);
    summary.append(text);
    latest.result.files.forEach((file) => detail.append(renderFileFields(file)));
  }

  resultsBody.replaceChildren();
  if (state.submissions.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = t("noCases");
    row.append(cell);
    resultsBody.append(row);
    return;
  }

  state.submissions.forEach((submission) => {
    const row = document.createElement("tr");
    const countCell = document.createElement("td");
    countCell.textContent = String(submission.count);
    const companyCell = document.createElement("td");
    companyCell.textContent = companyName(submission) || "—";
    const statusCell = document.createElement("td");
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = statusLabel(submission);
    statusCell.append(pill);
    row.append(countCell, companyCell, statusCell);
    resultsBody.append(row);
  });
}

function renderFileFields(file) {
  const block = document.createElement("section");
  block.className = "file-block";
  const title = document.createElement("h3");
  title.textContent = `${file.filename} · ${file.type || t("unrecognised")}`;
  block.append(title);
  if (!file.json || Object.keys(file.json).length === 0) {
    const empty = document.createElement("p");
    empty.className = "placeholder";
    empty.textContent = t("noFields");
    block.append(empty);
    return block;
  }
  block.append(renderObject(file.json, file.sources || {}));
  return block;
}

function renderObject(value, sources) {
  const list = document.createElement("dl");
  list.className = "field-list";
  Object.entries(value).forEach(([key, item]) => {
    const term = document.createElement("dt");
    term.textContent = key;
    const definition = document.createElement("dd");
    if (item && typeof item === "object") {
      definition.append(renderObject(item, sources));
    } else {
      definition.textContent = item === null || item === undefined ? "null" : String(item);
      if (sources[key]) {
        const tag = document.createElement("span");
        tag.className = "source";
        tag.textContent = sources[key] === "llm" ? t("sourceLlm") : t("sourceRule");
        definition.append(tag);
      }
    }
    list.append(term, definition);
  });
  return list;
}

function nullFields(value, prefix) {
  if (!value || typeof value !== "object") return [];
  const found = [];
  Object.entries(value).forEach(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (item && typeof item === "object") found.push(...nullFields(item, path));
    else if (item === null) found.push(path);
  });
  return found;
}

function companyName(submission) {
  if (!submission.result) return "";
  for (const file of submission.result.files) {
    const name = findName(file.json);
    if (name) return name;
  }
  return "";
}

function findName(value) {
  if (!value || typeof value !== "object") return "";
  if (typeof value.nazwa === "string" && value.nazwa) return value.nazwa;
  for (const item of Object.values(value)) {
    if (item && typeof item === "object") {
      const name = findName(item);
      if (name) return name;
    }
  }
  return "";
}

function statusLabel(submission) {
  if (submission.error || !submission.result) return t("statusFailed");
  const files = submission.result.files;
  const recognised = files.filter((file) => file.type).length;
  if (recognised === 0) return t("statusNone");
  if (recognised < files.length) return t("statusPartial");
  return t("statusDone");
}

function placeholder(key) {
  const paragraph = document.createElement("p");
  paragraph.className = "placeholder";
  paragraph.textContent = t(key);
  return paragraph;
}

function resetAll() {
  state.files = [];
  state.submissions = [];
  state.notice = null;
  fileInput.value = "";
  renderNotice();
  renderFiles();
  renderOutputs();
}

applyCopy();

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

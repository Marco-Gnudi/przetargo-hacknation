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
    colFile: "Plik",
    colType: "Rodzaj",
    colStatus: "Status",
    noCases: "Brak spraw.",
    processingNow: "Przetwarzanie…",
    apiError: "Nie udało się połączyć z ekstraktorem. Uruchom back-end2/start.sh i otwórz http://127.0.0.1:8000.",
    bielikNote: "Model Bielik nie jest podłączony. Ten przebieg użył ekstraktora deterministycznego.",
    unrecognized: "Dokument nie został rozpoznany. Ekstraktor nie przypisał go do odwołania, pełnomocnictwa ani potwierdzenia przelewu.",
    copyJson: "Kopiuj JSON",
    copied: "Skopiowano",
    downloadJson: "Pobierz JSON",
    showJson: "Pokaż JSON",
    showFields: "Pokaż pola",
    nullValue: "null",
    types: {
      odwolanie: "Odwołanie",
      pelnomocnictwo: "Pełnomocnictwo",
      przelew: "Potwierdzenie przelewu",
      unknown: "Nierozpoznany dokument",
    },
    statuses: { ok: "Przetworzono", unrecognized: "Nierozpoznany", error: "Błąd" },
    remove: "Usuń",
    pdfOnly: "Można dodać tylko pliki PDF. Pominięto: {names}",
    already: "Te pliki PDF są już dodane.",
    pending: "Jeszcze nieprzetworzone",
    footer: "Hacknation 2026 projekt dla Urzędu Zamówień Publicznych",
    modeName: { regular: "przetwarzanie regularne", bielik: "Bielik" },
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
    colFile: "File",
    colType: "Type",
    colStatus: "Status",
    noCases: "No cases yet.",
    processingNow: "Processing…",
    apiError: "The extractor could not be reached. Start back-end2/start.sh and open http://127.0.0.1:8000.",
    bielikNote: "Bielik is not connected. This run used the deterministic extractor.",
    unrecognized: "The document was not recognized. It was not classified as an appeal, a power of attorney, or a transfer confirmation.",
    copyJson: "Copy JSON",
    copied: "Copied",
    downloadJson: "Download JSON",
    showJson: "Show JSON",
    showFields: "Show fields",
    nullValue: "null",
    types: {
      odwolanie: "Appeal",
      pelnomocnictwo: "Power of attorney",
      przelew: "Transfer confirmation",
      unknown: "Unrecognized document",
    },
    statuses: { ok: "Processed", unrecognized: "Unrecognized", error: "Error" },
    remove: "Remove",
    pdfOnly: "Only PDF files can be added. Skipped: {names}",
    already: "Those PDFs are already attached.",
    pending: "Not processed yet",
    footer: "HackNation 2026 project for the Public Procurement Office",
    modeName: { regular: "regular processing", bielik: "Bielik" },
  },
};

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
  submitButton.textContent = state.busy ? t("processingNow") : t("process");
}

async function submitFiles() {
  if (state.files.length === 0 || state.busy) return;
  const selected = state.files.slice();
  const mode = state.mode;
  state.busy = true;
  state.notice = null;
  renderFiles();

  const form = new FormData();
  selected.forEach((item) => form.append("files", item.file, item.file.name));
  try {
    const response = await fetch("/api/extract/batch", { method: "POST", body: form });
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json();
    state.submissions.push({ mode, results: body.results || [] });
    state.files = [];
  } catch {
    state.notice = { key: "apiError" };
  } finally {
    state.busy = false;
    renderNotice();
    renderFiles();
    renderOutputs();
  }
}

function renderOutputs() {
  const results = state.submissions.flatMap((submission) => submission.results || []);
  const latest = state.submissions[state.submissions.length - 1];

  summary.replaceChildren();
  if (!latest) {
    summary.append(placeholder("summaryEmpty"));
  } else {
    const recognized = latest.results.filter((item) => item.status === "ok").length;
    const unrecognized = latest.results.filter((item) => item.status === "unrecognized").length;
    const failed = latest.results.filter((item) => item.status === "error").length;
    const text = document.createElement("p");
    text.className = "summary-text";
    text.textContent = summarySentence(recognized, unrecognized, failed);
    summary.append(text);
    if (latest.mode === "bielik") {
      const note = document.createElement("p");
      note.className = "placeholder";
      note.textContent = t("bielikNote");
      summary.append(note);
    }
  }

  detail.replaceChildren();
  if (!latest) {
    detail.append(placeholder("fieldsEmpty"));
  } else {
    latest.results.forEach((item) => detail.append(renderResult(item)));
  }

  resultsBody.replaceChildren();
  if (results.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = t("noCases");
    row.append(cell);
    resultsBody.append(row);
    return;
  }
  results.forEach((item) => {
    const row = document.createElement("tr");
    const fileCell = document.createElement("td");
    fileCell.textContent = item.filename;
    const typeCell = document.createElement("td");
    typeCell.textContent = typeLabel(item.document_type);
    const statusCell = document.createElement("td");
    const pill = document.createElement("span");
    pill.className = `pill pill-${item.status}`;
    pill.textContent = t("statuses")[item.status] || item.status;
    statusCell.append(pill);
    row.append(fileCell, typeCell, statusCell);
  });
}

function summarySentence(recognized, unrecognized, failed) {
  if (state.lang === "pl") {
    return `Rozpoznane: ${recognized}. Nierozpoznane: ${unrecognized}. Błędy: ${failed}.`;
  }
  return `Recognized: ${recognized}. Unrecognized: ${unrecognized}. Errors: ${failed}.`;
}

function typeLabel(documentType) {
  return t("types")[documentType] || t("types").unknown;
}

function renderResult(item) {
  const article = document.createElement("article");
  article.className = "result";
  const heading = document.createElement("h3");
  heading.textContent = `${item.filename} — ${typeLabel(item.document_type)}`;
  article.append(heading);

  if (item.status === "unrecognized") {
    const note = document.createElement("p");
    note.className = "placeholder";
    note.textContent = t("unrecognized");
    article.append(note);
  } else if (item.status === "error") {
    const note = document.createElement("p");
    note.className = "message";
    note.textContent = item.error || t("statuses").error;
    article.append(note);
  } else {
    article.append(renderFields(item.result));
  }

  if (item.warnings && item.warnings.length) {
    const warnings = document.createElement("p");
    warnings.className = "placeholder";
    warnings.textContent = item.warnings.join(" ");
    article.append(warnings);
  }

  const raw = document.createElement("pre");
  raw.className = "json-view";
  raw.hidden = true;
  raw.textContent = JSON.stringify(item.result, null, 2);
  article.append(raw);

  const actions = document.createElement("div");
  actions.className = "result-actions";
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "btn btn-ghost";
  toggle.textContent = t("showJson");
  toggle.addEventListener("click", () => {
    raw.hidden = !raw.hidden;
    toggle.textContent = raw.hidden ? t("showJson") : t("showFields");
  });
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "btn btn-ghost";
  copy.textContent = t("copyJson");
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(raw.textContent);
      copy.textContent = t("copied");
    } catch {
      copy.textContent = t("copyJson");
    }
  });
  const download = document.createElement("button");
  download.type = "button";
  download.className = "btn btn-ghost";
  download.textContent = t("downloadJson");
  download.addEventListener("click", () => downloadJson(item.filename, raw.textContent));
  actions.append(toggle, copy, download);
  article.append(actions);
  return article;
}

function renderFields(value) {
  const list = document.createElement("dl");
  list.className = "field-list";
  Object.entries(flattenFields(value)).forEach(([key, fieldValue]) => {
    const term = document.createElement("dt");
    term.textContent = key;
    const description = document.createElement("dd");
    if (fieldValue === null) {
      description.className = "is-null";
      description.textContent = t("nullValue");
    } else {
      description.textContent = String(fieldValue);
    }
    list.append(term, description);
  });
  return list;
}

function flattenFields(value, prefix = "", output = {}) {
  if (Array.isArray(value)) {
    if (value.length === 0) output[prefix] = "[]";
    value.forEach((item, index) => flattenFields(item, `${prefix}[${index}]`, output));
    return output;
  }
  if (value && typeof value === "object") {
    Object.entries(value).forEach(([key, child]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      flattenFields(child, path, output);
    });
    return output;
  }
  output[prefix || "value"] = value;
  return output;
}

function downloadJson(filename, contents) {
  const base = filename.replace(/\.pdf$/i, "") || "document";
  const blob = new Blob([contents + "\n"], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${base}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
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

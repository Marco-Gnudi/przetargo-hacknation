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
const MAX_PDFS = 30;

const copy = {
  pl: {
    title: "PrzetarGO",
    tagline: "Odwołania KIO jako ustrukturyzowane dane",
    language: "Język",
    heroTitle: "Konwertuj pliki PDF na JSON-y",
    processing: "Przetwarzanie",
    processingHint: "Wybierz sposób odczytu tej sprawy.",
    modeRegular: "Regularne",
    modeRegularHint: "Bez modelu językowego",
    modeBielik: "Bielik",
    modeBielikHint: "Reguły, potem model",
    modeBielikOnly: "Tylko Bielik",
    modeBielikOnlyHint: "Bez reguł, same wywołania modelu",
    documents: "Dokumenty",
    dropAria: "Dodaj do 30 plików PDF. Upuść je tutaj albo naciśnij Enter, aby wybrać je z urządzenia.",
    dropTitle: "Upuść pliki PDF tutaj albo dodaj je ze swojego urządzenia.",
    dropHint: "Do 30 plików PDF.",
    process: "Przetwórz dokumenty",
    summary: "Podsumowanie",
    summaryEmpty: "Kompletność i brakujące informacje pojawią się po przetworzeniu sprawy.",
    complete: "Kompletny",
    incomplete: "Niekompletny",
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
    apiError: "Ekstraktor nie odpowiada. Odśwież tę stronę. Jeśli błąd zostaje, uruchom back-end2/start.sh.",
    emptyFiles: "Ten plik ma 0 bajtów w oknie wyboru, więc nie ma w nim treści PDF. Wybierz PDF, przy którym widać rozmiar.",
    tooMany: "Można dodać najwyżej 30 plików PDF.",
    uncertain: "Niepewne",
    filesTotal: "{count} plików · {size}",
    bielikNote: "Model Bielik nie jest podłączony. Ten przebieg użył ekstraktora deterministycznego.",
    bielikUsed: "Bielik",
    tokens: "Tokeny",
    promptTokens: "prompt",
    completionTokens: "odpowiedź",
    llmCalls: "Wywołania",
    sourceRule: "Reguły",
    sourceLlm: "Bielik",
    sourceAgree: "Reguły ✓ Bielik",
    timing: "Czas procesowania: {total} · {average} na plik",
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
    modeName: { regular: "przetwarzanie regularne", bielik: "Bielik", bielik_only: "Tylko Bielik" },
  },
  en: {
    title: "PrzetarGO",
    tagline: "KIO appeals as structured data",
    language: "Language",
    heroTitle: "Convert PDFs to JSONS",
    processing: "Processing",
    processingHint: "Choose how this case will be read.",
    modeRegular: "Regular",
    modeRegularHint: "No language model",
    modeBielik: "Bielik",
    modeBielikHint: "Rules, then the model",
    modeBielikOnly: "Bielik only",
    modeBielikOnlyHint: "No rules, model calls only",
    documents: "Documents",
    dropAria: "Add up to 30 PDF files. Drop them here or press Enter to choose them from your device.",
    dropTitle: "Drop PDFs here or add them from your device.",
    dropHint: "Up to 30 PDFs.",
    process: "Process documents",
    summary: "Summary",
    summaryEmpty: "Completeness and missing information will show here after a case is processed.",
    complete: "Complete",
    incomplete: "Incomplete",
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
    apiError: "The extractor did not respond. Refresh this page. If it still fails, run back-end2/start.sh.",
    emptyFiles: "That file is 0 bytes in the file window, so it has no PDF content. Choose a PDF that shows a size.",
    tooMany: "You can add up to 30 PDFs.",
    uncertain: "Uncertain",
    filesTotal: "{count} files · {size}",
    bielikNote: "Bielik is not connected. This run used the deterministic extractor.",
    bielikUsed: "Bielik",
    tokens: "Tokens",
    promptTokens: "prompt",
    completionTokens: "completion",
    llmCalls: "Calls",
    sourceRule: "Rules",
    sourceLlm: "Bielik",
    sourceAgree: "Rules ✓ Bielik",
    timing: "Processing time: {total} · {average} per file",
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
    modeName: { regular: "regular processing", bielik: "Bielik", bielik_only: "Bielik only" },
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
  if (state.notice.text) {
    inputMessage.textContent = state.notice.text;
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

function apiBase() {
  const here = location.hostname === "127.0.0.1" || location.hostname === "localhost";
  if (here && location.port === "8000") return "";
  return "http://127.0.0.1:8000";
}

async function addFiles(fileListLike) {
  const incoming = Array.from(fileListLike || []);
  if (incoming.length === 0) return;

  const rejected = [];
  const empty = [];
  let added = 0;
  let overflow = false;

  for (const file of incoming) {
    if (state.files.length >= MAX_PDFS) {
      overflow = true;
      break;
    }
    if (!(await isPdf(file))) {
      rejected.push(file.name);
      continue;
    }
    const size = await fileByteSize(file);
    if (size === 0) {
      empty.push(file.name);
      continue;
    }
    const duplicate = state.files.some(
      (item) =>
        item.file.name === file.name &&
        item.size === size &&
        item.file.lastModified === file.lastModified
    );
    if (duplicate) continue;
    state.files.push({ id: state.nextId++, file, size });
    added += 1;
  }

  if (rejected.length > 0) {
    state.notice = { text: rejected.map((name) => `Rejected: ${name} – not a PDF`).join("\n") };
  } else if (empty.length > 0) {
    state.notice = { key: "emptyFiles", names: empty };
  } else if (overflow) {
    state.notice = { key: "tooMany" };
  } else if (added === 0) {
    state.notice = { key: "already" };
  } else {
    state.notice = null;
  }
  renderNotice();

  renderFiles();
}

async function isPdf(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) return false;
  const bytes = new Uint8Array(await file.slice(0, 5).arrayBuffer());
  return bytes.length >= 4 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
}

function renderFiles() {
  fileList.replaceChildren();
  const total = state.files.reduce((sum, item) => sum + item.size, 0);
  if (state.files.length === 0) {
    fileList.hidden = true;
  } else {
    const summary = document.createElement("li");
    summary.className = "file-total";
    summary.textContent = t("filesTotal")
      .replace("{count}", String(state.files.length))
      .replace("{size}", formatSize(total));
    fileList.append(summary);
    fileList.hidden = false;
    state.files.forEach((item) => {
      const row = document.createElement("li");
      const name = document.createElement("span");
      name.className = "file-name";
      name.textContent = item.file.name;
      const size = document.createElement("span");
      size.className = "file-size";
      size.textContent = formatSize(item.size);
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
  const selected = state.files.slice(0, MAX_PDFS);
  const mode = state.mode;
  state.busy = true;
  state.notice = null;
  renderFiles();

  const form = new FormData();
  form.append("mode", mode);
  selected.forEach((item) => form.append("files", item.file, item.file.name));
  try {
    const response = await fetch(`${apiBase()}/api/extract/batch`, { method: "POST", body: form });
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json();
    state.submissions.push({
      mode,
      results: body.results || [],
      servedMode: body.mode || null,
      usage: body.usage || null,
      elapsed: body.elapsed_seconds,
      perFile: body.seconds_per_file,
    });
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
    const list = document.createElement("div");
    list.className = "summary-docs";
    latest.results
      .filter((item) => item.status !== "rejected")
      .forEach((item) => list.append(renderSummaryDoc(item)));
    summary.append(list);
    if (Number.isFinite(Number(latest.elapsed))) {
      const timing = document.createElement("p");
      timing.className = "summary-text summary-timing";
      timing.textContent = t("timing")
        .replace("{total}", formatDuration(latest.elapsed))
        .replace("{average}", formatDuration(latest.perFile));
      summary.append(timing);
    }
    latest.results
      .filter((item) => item.status === "rejected")
      .forEach((item) => {
        const line = document.createElement("p");
        line.className = "message";
        line.textContent = item.error || `Rejected: ${item.filename} – not a PDF`;
        summary.append(line);
      });
    const note = document.createElement("p");
    note.className = "summary-text";
    if (latest.servedMode === "bielik" || latest.servedMode === "bielik_only") {
      const usage = latest.usage || {};
      const prompt = Number(usage.prompt_tokens) || 0;
      const completion = Number(usage.completion_tokens) || 0;
      const calls = Number(usage.calls) || 0;
      const label = latest.servedMode === "bielik_only" ? t("modeBielikOnly") : t("bielikUsed");
      note.textContent = `${label} · ${t("tokens")} ${prompt + completion} (${t("promptTokens")} ${prompt}, ${t("completionTokens")} ${completion}) · ${t("llmCalls")} ${calls}`;
      summary.append(note);
    } else if (latest.mode === "bielik" || latest.mode === "bielik_only") {
      note.className = "placeholder";
      note.textContent = t("bielikNote");
      summary.append(note);
    }
  }

  detail.replaceChildren();
  if (!latest) {
    detail.append(placeholder("fieldsEmpty"));
  } else {
    latest.results
      .filter((item) => item.status !== "rejected")
      .forEach((item) => detail.append(renderResult(item)));
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

function renderSummaryDoc(item) {
  const block = document.createElement("div");
  block.className = "summary-doc";
  const title = document.createElement("p");
  title.className = "summary-doc-title";
  const name = document.createElement("span");
  name.textContent = `${item.filename} — ${typeLabel(item.document_type)}`;
  const status = document.createElement("span");
  title.append(name, status);
  block.append(title);

  if (item.status !== "ok") {
    status.className = "summary-status is-bad";
    status.textContent = t("statuses")[item.status] || item.status;
    return block;
  }

  const missing = Object.entries(flattenFields(item.result))
    .filter(([, value]) => value === null)
    .map(([path]) => path);
  if (missing.length === 0) {
    status.className = "summary-status is-ok";
    status.textContent = t("complete");
    return block;
  }

  status.className = "summary-status is-bad";
  status.textContent = t("incomplete");
  const bullets = document.createElement("ul");
  bullets.className = "summary-missing";
  missing.forEach((path) => {
    const line = document.createElement("li");
    line.textContent = path;
    bullets.append(line);
  });
  block.append(bullets);
  return block;
}

function typeLabel(documentType) {
  return t("types")[documentType] || t("types").unknown;
}

function renderResult(item) {
  const article = document.createElement("details");
  article.className = "result";
  article.open = true;
  const heading = document.createElement("summary");
  const sizeLabel = Number.isFinite(item.size) ? ` · ${formatSize(item.size)}` : "";
  heading.textContent = `${item.filename}${sizeLabel} — ${typeLabel(item.document_type)}`;
  if (item.status === "unrecognized" || item.status === "error") heading.append(uncertainMark());
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
    article.append(renderFields(item.result, item.sources || {}, item.review || {}));
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
  const json = () => JSON.stringify(item.result, null, 2);
  raw.textContent = json();
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
      raw.textContent = json();
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
  download.addEventListener("click", () => downloadJson(item.filename, json()));
  actions.append(toggle, copy, download);
  article.append(actions);
  return article;
}

function uncertainMark() {
  const mark = document.createElement("span");
  mark.className = "uncertain-mark";
  mark.title = t("uncertain");
  mark.setAttribute("role", "img");
  mark.setAttribute("aria-label", t("uncertain"));
  mark.innerHTML = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="8" fill="#d52f2b"/><text x="8" y="12" text-anchor="middle" font-size="11" font-family="Segoe UI, sans-serif" font-weight="700" fill="#fff">?</text></svg>';
  return mark;
}

function renderFields(value, sources, review) {
  const list = document.createElement("div");
  list.className = "field-list";
  Object.entries(flattenFields(value)).forEach(([key, fieldValue]) => {
    const row = document.createElement("div");
    row.className = "field-row";
    const label = document.createElement("div");
    label.className = "field-label";
    label.textContent = key;
    const content = document.createElement("div");
    content.className = "field-value";
    if (fieldValue === null) {
      content.classList.add("is-null");
      content.textContent = t("nullValue");
      label.append(uncertainMark());
    } else {
      content.textContent = String(fieldValue);
    }
    const tag = sourceBadge(key, sources, review);
    if (tag) content.append(tag);
    row.append(label, content);
    list.append(row);
  });
  return list;
}

function sourceBadge(path, sources, review) {
  const mark = review && review[path];
  const tag = document.createElement("span");
  tag.className = "source";
  if (mark && mark.mark === "agree") {
    tag.textContent = t("sourceAgree");
    return tag;
  }
  if (mark && mark.mark === "diff") {
    tag.append(`${t("sourceRule")} (`);
    const muted = document.createElement("span");
    muted.className = "bielik-diff";
    const shown = mark.bielik === null || mark.bielik === undefined ? t("nullValue") : String(mark.bielik);
    muted.textContent = `${t("sourceLlm")}: ${shown}`;
    tag.append(muted, ")");
    return tag;
  }
  if (mark && mark.mark === "llm") {
    tag.textContent = t("sourceLlm");
    return tag;
  }
  if (mark && mark.mark === "rule") {
    tag.textContent = t("sourceRule");
    return tag;
  }
  if (sources && sources[path]) {
    tag.textContent = sources[path] === "llm" ? t("sourceLlm") : t("sourceRule");
    return tag;
  }
  return null;
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

async function fileByteSize(file) {
  if (file.size > 0) return file.size;
  try {
    return (await file.arrayBuffer()).byteLength;
  } catch {
    return 0;
  }
}

function formatDuration(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 1) {
    const milliseconds = Math.round(value * 1000);
    return `${value > 0 ? Math.max(1, milliseconds) : 0} ms`;
  }
  if (value < 10) return `${value.toFixed(2)} s`;
  return `${value.toFixed(1)} s`;
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

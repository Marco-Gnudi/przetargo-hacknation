const dropzone = document.querySelector("#dropzone");
const fileInput = document.querySelector("#file-input");
const fileList = document.querySelector("#file-list");
const inputMessage = document.querySelector("#input-message");
const submitButton = document.querySelector("#submit");
const resetButton = document.querySelector("#reset");
const summary = document.querySelector("#summary");
const viewButtons = document.querySelectorAll("[data-view]");
const viewSwitch = document.querySelector(".source-switch");
const modeButtons = document.querySelectorAll("[data-mode]");
const langButtons = document.querySelectorAll("[data-lang]");
const bielikSettings = document.querySelector("#bielik-settings");
const bielikKey = document.querySelector("#bielik-key");
const bielikBaseUrl = document.querySelector("#bielik-base-url");
const bielikModel = document.querySelector("#bielik-model");
const bielikStatus = document.querySelector("#bielik-status");
const bielikCheck = document.querySelector("#bielik-check");
const samplePicker = document.querySelector("#sample-picker");
const sampleSelect = document.querySelector("#sample-select");
const sampleLoad = document.querySelector("#sample-load");
const inputFolder = document.querySelector("#input-folder");
const ocrWarning = document.querySelector("#ocr-warning");
const MAX_PDFS = 150;
const VALID_TYPES = ["odwolanie", "pelnomocnictwo", "przelew"];
// The Hacknation Task view has no mode switch. On 20 random cases Mistral alone scored
// F1 0.995, ahead of Regular (0.984) and Regular + Mistral (0.982).
const TASK_MODE = "bielik_only";

const copy = {
  pl: {
    title: "PrzetarGO",
    tagline: "Odwołania KIO jako ustrukturyzowane dane",
    language: "Język",
    heroTitle: "Konwertuj pliki PDF na JSON-y",
    viewLabel: "Widok",
    viewTask: "Zadanie Hacknation",
    viewDrop: "Przeciągnij i upuść",
    taskMode: "Zadanie Hacknation przetwarza dokumenty trybem Tylko Mistral.",
    taskKeyLabel: "Klucz API Mistral",
    taskKeyAdd: "Dodaj",
    taskKeyHint: "Klucz zostaje tylko w pamięci tej karty. Nie jest zapisywany w przeglądarce, na dysku ani w logach.",
    taskKeyAdded: "Klucz dodany. Połączono z modelem {model}.",
    taskKeyEmpty: "Wpisz klucz API.",
    casesAdded: "Dodano {cases} spraw · {files} plików PDF",
    refreshInput: "Odśwież",
    filesCount: "{count} plików PDF",
    rootCase: "input/ (pliki bez folderu sprawy)",
    progressHead: "Przetworzono {done} z {total}",
    progressPending: "w kolejce",
    progressRunning: "przetwarzanie…",
    finishedIn: "Zakończono w {total} ({average} na dokument).",
    mistralTokens: "Tokeny Mistral: {total} (prompt {prompt}, odpowiedź {completion}) · wywołania: {calls}",
    mistralNone: "Tokeny Mistral: 0 — tryb regularny nie używa modelu językowego.",
    validDocs: "Poprawne dokumenty: {count}",
    invalidDocs: "Dokumenty spoza zakresu (negatywne): {count}",
    failedDocs: "Błędy odczytu: {count}",
    outputWhere: "Pliki JSON znajdziesz w folderze output w repozytorium:",
    outputRoot: "Pełna ścieżka: {path}",
    processingIndex: "{index}. dokument przetworzony",
    processing: "Przetwarzanie",
    processingHint: "Wybierz sposób odczytu tej sprawy.",
    modeRegular: "Regularne",
    modeRegularHint: "Bez modelu językowego",
    modeBielik: "Mistral",
    modeBielikHint: "Reguły, potem model",
    modeBielikOnly: "Tylko Mistral",
    modeBielikOnlyHint: "Bez reguł, same wywołania modelu",
    documents: "Dokumenty",
    inputFolder: "Folder input",
    selectAll: "Zaznacz wszystkie",
    deleteInput: "Usuń input",
    deleteInputConfirm: "Usunąć pliki z folderu input? Folder output zostanie.",
    inputEmpty: "Folder input jest pusty. Skopiuj do niego foldery spraw z plikami PDF (np. input/case1/) i naciśnij Odśwież.",
    inputHint: "Wszystkie sprawy z folderu input zostaną przetworzone. Każdy PDF da plik JSON o tej samej nazwie w folderze output.",
    dropAria: "Dodaj do 150 plików PDF. Upuść je tutaj albo naciśnij Enter, aby wybrać je z urządzenia.",
    dropTitle: "Upuść pliki PDF tutaj albo dodaj je ze swojego urządzenia.",
    dropHint: "Do 150 plików PDF.",
    process: "Przetwórz dokumenty",
    summary: "Podsumowanie",
    summaryEmpty: "Postęp przetwarzania i podsumowanie pojawią się tutaj.",
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
    processingCount: "Przetwarzanie {done}/{total}…",
    apiError: "Ekstraktor nie odpowiada. Odśwież tę stronę. Jeśli błąd zostaje, uruchom ponownie ./start.sh (w Windows start.bat).",
    emptyFiles: "Ten plik ma 0 bajtów w oknie wyboru, więc nie ma w nim treści PDF. Wybierz PDF, przy którym widać rozmiar.",
    tooMany: "Można dodać najwyżej 150 plików PDF.",
    uncertain: "Niepewne",
    filesTotal: "{count} plików · {size}",
    bielikNote: "Model Mistral nie jest podłączony. Ten przebieg użył ekstraktora deterministycznego.",
    bielikUsed: "Mistral",
    tokens: "Tokeny",
    promptTokens: "prompt",
    completionTokens: "odpowiedź",
    llmCalls: "Wywołania",
    sourceRule: "Reguły",
    sourceLlm: "Mistral",
    sourceAgree: "Reguły ✓ Mistral",
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
    statuses: { ok: "Przetworzono", unrecognized: "Nierozpoznany", needs_ocr: "Wymaga OCR", error: "Błąd" },
    remove: "Usuń",
    pdfOnly: "Można dodać tylko pliki PDF. Pominięto: {names}",
    already: "Te pliki PDF są już dodane.",
    pending: "Jeszcze nieprzetworzone",
    viewExtract: "Ekstrakcja",
    viewStats: "Statystyki",
    statsF1Label: "F1 (całość)",
    statsPrecision: "precyzja",
    statsRecall: "czułość",
    statsMissing: "Brak pliku ze statystykami. Uruchom ewaluację, aby go utworzyć.",
    statsChartOverview: "F1 według rodzaju dokumentu",
    statsChartFlow: "Przepływ przetwarzania",
    statsTypes: {
      odwolanie: "Odwołanie",
      pelnomocnictwo: "Pełnomocnictwo",
      przelew: "Przelew",
    },
    footer: "Hacknation 2026 projekt dla Urzędu Zamówień Publicznych",
    modeName: { regular: "przetwarzanie regularne", bielik: "Mistral", bielik_only: "Tylko Mistral" },
    apiErrorHosted: "Ekstraktor nie odpowiada. Odśwież stronę i spróbuj ponownie.",
    bielikKeyTitle: "Klucz API Mistral",
    bielikKeyHint: "Klucz jest tylko w pamięci tej karty i trafia wyłącznie do lokalnego serwera PrzetarGO. Nie jest nigdzie zapisywany.",
    bielikCheck: "Sprawdź połączenie",
    bielikAdvanced: "Ustawienia zaawansowane",
    bielikBaseUrl: "Adres API (zgodny z OpenAI)",
    bielikModel: "Model",
    bielikChecking: "Sprawdzanie połączenia…",
    bielikOk: "Połączono z modelem {model}.",
    bielikServerKey: "Serwer ma ustawiony MISTRAL_API_KEY. Zostaw pole puste, aby go użyć.",
    bielikKeyMissing: "Wpisz klucz API Mistral albo wybierz tryb Regularne.",
    bielikKeyRejected: "API odrzuciło klucz albo model. Sprawdź klucz i spróbuj ponownie.",
    llmFailures: "nieudane: {count}",
    ocrMissing: "Tesseract OCR nie jest zainstalowany, więc skany nie zostaną odczytane. PDF-y z tekstem działają. Uruchom: python doctor.py",
    needsOcr: "To skan bez warstwy tekstowej i nie udało się go odczytać przez OCR. Wynik jest pusty, a nie zgadywany.",
    sampleTitle: "Wypróbuj przykładową sprawę",
    sampleLoad: "Dodaj pliki",
    sampleText: "Sprawa {id} · PDF z tekstem",
    sampleScan: "Skany {id} · OCR",
    sampleError: "Nie udało się pobrać przykładowych plików.",
  },
  en: {
    title: "PrzetarGO",
    tagline: "KIO appeals as structured data",
    language: "Language",
    heroTitle: "Convert PDFs to JSONS",
    viewLabel: "View",
    viewTask: "Hacknation Task",
    viewDrop: "Drag & Drop",
    taskMode: "The Hacknation Task processes documents with Mistral only.",
    taskKeyLabel: "Mistral API key",
    taskKeyAdd: "Add",
    taskKeyHint: "The key stays in this tab's memory only. It is not saved in the browser, on disk or in logs.",
    taskKeyAdded: "Key added. Connected to {model}.",
    taskKeyEmpty: "Enter an API key.",
    casesAdded: "Added {cases} cases · {files} PDF files",
    refreshInput: "Refresh",
    filesCount: "{count} PDF files",
    rootCase: "input/ (files outside a case folder)",
    progressHead: "Processed {done} of {total}",
    progressPending: "queued",
    progressRunning: "processing…",
    finishedIn: "Finished in {total} ({average} per document).",
    mistralTokens: "Mistral tokens: {total} (prompt {prompt}, completion {completion}) · calls: {calls}",
    mistralNone: "Mistral tokens: 0 — regular mode does not use a language model.",
    validDocs: "Valid documents: {count}",
    invalidDocs: "Out-of-scope documents (negative): {count}",
    failedDocs: "Read errors: {count}",
    outputWhere: "The JSON files are in the output folder in the repository:",
    outputRoot: "Full path: {path}",
    processingIndex: "Document {index} processed",
    processing: "Processing",
    processingHint: "Choose how this case will be read.",
    modeRegular: "Regular",
    modeRegularHint: "No language model",
    modeBielik: "Mistral",
    modeBielikHint: "Rules, then the model",
    modeBielikOnly: "Mistral only",
    modeBielikOnlyHint: "No rules, model calls only",
    documents: "Documents",
    inputFolder: "Input folder",
    selectAll: "Select all",
    deleteInput: "Delete input",
    deleteInputConfirm: "Delete the files in the input folder? The output folder will stay.",
    inputEmpty: "The input folder is empty. Copy case folders of PDFs into it (e.g. input/case1/) and press Refresh.",
    inputHint: "Every case in the input folder is processed. Each PDF gives a JSON file with the same name in the output folder.",
    dropAria: "Add up to 150 PDF files. Drop them here or press Enter to choose them from your device.",
    dropTitle: "Drop PDFs here or add them from your device.",
    dropHint: "Up to 150 PDFs.",
    process: "Process documents",
    summary: "Summary",
    summaryEmpty: "Processing progress and the summary will show here.",
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
    processingCount: "Processing {done}/{total}…",
    apiError: "The extractor did not respond. Refresh this page. If it still fails, run ./start.sh again (start.bat on Windows).",
    emptyFiles: "That file is 0 bytes in the file window, so it has no PDF content. Choose a PDF that shows a size.",
    tooMany: "You can add up to 150 PDFs.",
    uncertain: "Uncertain",
    filesTotal: "{count} files · {size}",
    bielikNote: "Mistral is not connected. This run used the deterministic extractor.",
    bielikUsed: "Mistral",
    tokens: "Tokens",
    promptTokens: "prompt",
    completionTokens: "completion",
    llmCalls: "Calls",
    sourceRule: "Rules",
    sourceLlm: "Mistral",
    sourceAgree: "Rules ✓ Mistral",
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
    statuses: { ok: "Processed", unrecognized: "Unrecognized", needs_ocr: "Needs OCR", error: "Error" },
    remove: "Remove",
    pdfOnly: "Only PDF files can be added. Skipped: {names}",
    already: "Those PDFs are already attached.",
    pending: "Not processed yet",
    viewExtract: "Extraction",
    viewStats: "Statistics",
    statsF1Label: "F1 (overall)",
    statsPrecision: "precision",
    statsRecall: "recall",
    statsMissing: "The statistics file is missing. Run an evaluation to create it.",
    statsChartOverview: "F1 by document type",
    statsChartFlow: "Processing flow",
    statsTypes: {
      odwolanie: "Appeal",
      pelnomocnictwo: "Power of attorney",
      przelew: "Transfer",
    },
    footer: "HackNation 2026 project for the Public Procurement Office",
    modeName: { regular: "regular processing", bielik: "Mistral", bielik_only: "Mistral only" },
    apiErrorHosted: "The extractor did not respond. Refresh the page and try again.",
    bielikKeyTitle: "Mistral API key",
    bielikKeyHint: "The key stays in this tab's memory and is sent only to your local PrzetarGO server. It is never saved.",
    bielikCheck: "Check connection",
    bielikAdvanced: "Advanced settings",
    bielikBaseUrl: "API base URL (OpenAI-compatible)",
    bielikModel: "Model",
    bielikChecking: "Checking the connection…",
    bielikOk: "Connected to {model}.",
    bielikServerKey: "The server has MISTRAL_API_KEY set. Leave this empty to use it.",
    bielikKeyMissing: "Enter a Mistral API key, or choose Regular mode.",
    bielikKeyRejected: "The API rejected the key or the model. Check the key and try again.",
    llmFailures: "failed: {count}",
    ocrMissing: "Tesseract OCR is not installed, so scans cannot be read. Text PDFs still work. Run: python doctor.py",
    needsOcr: "This is a scan with no text layer and OCR could not read it. The result is empty, not guessed.",
    sampleTitle: "Try an example case",
    sampleLoad: "Add files",
    sampleText: "Case {id} · text PDFs",
    sampleScan: "Scans {id} · OCR",
    sampleError: "The example files could not be downloaded.",
  },
};

const state = {
  mode: "regular",
  lang: savedLang(),
  files: [],
  nextId: 1,
  notice: null,
  busy: false,
  taskKeyAdded: false,
  taskKeyModel: "",
  hosted: false,
  serverKey: false,
  samples: [],
  keyStatus: null,
  keyModel: "",
  progress: null,
  view: "task",
  run: null,
  outputRoot: "",
};

let inputCatalog = [];

[bielikKey, bielikBaseUrl, bielikModel].forEach((field) => {
  field.addEventListener("input", () => {
    state.keyStatus = null;
    renderKeyStatus();
  });
});
bielikCheck.addEventListener("click", checkKey);
sampleLoad.addEventListener("click", loadSample);

langButtons.forEach((button) => {
  button.addEventListener("click", () => setLang(button.dataset.lang));
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

viewButtons.forEach((button) => {
  button.addEventListener("click", () => selectView(button.dataset.view));
});

const taskKeyInput = document.querySelector("#task-key-input");
const taskKeyAdd = document.querySelector("#task-key-add");
let taskApiKey = "";

taskKeyAdd.addEventListener("click", addTaskKey);
taskKeyInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addTaskKey();
  }
});

document.querySelector("#refresh-input").addEventListener("click", () => {
  if (!state.busy) loadInputCases();
});

document.querySelector("#delete-input").addEventListener("click", async () => {
  if (state.busy) return;
  if (!window.confirm(t("deleteInputConfirm"))) return;
  try {
    const response = await fetch(`${apiBase()}/api/input`, { method: "DELETE" });
    if (!response.ok) throw new Error(String(response.status));
    await loadInputCases();
  } catch {
    state.notice = { key: "apiError" };
    renderNotice();
  }
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
  document.querySelectorAll("[data-i18n-alt]").forEach((el) => {
    el.alt = t(el.dataset.i18nAlt);
  });
  renderStats();
  langButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  });
  renderNotice();
  renderFiles();
  renderInputCases();
  renderTaskKeyStatus();
  renderSamples();
  renderKeyStatus();
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
  if (state.notice.key === "apiError") {
    inputMessage.textContent = apiErrorText();
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
  bielikSettings.hidden = state.view === "task" || !needsBielik(mode);
}

function selectView(view) {
  if (state.busy) return;
  state.view = view === "drop" || state.hosted ? "drop" : "task";
  viewButtons.forEach((button) => {
    const selected = button.dataset.view === state.view;
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  const task = state.view === "task";
  inputFolder.hidden = !task;
  dropzone.hidden = task;
  samplePicker.hidden = task || state.samples.length === 0;
  document.querySelector(".mode-bar").hidden = task;
  document.querySelector("#task-mode").hidden = !task;
  document.querySelector("#task-key").hidden = !task;
  bielikSettings.hidden = task || !needsBielik(state.mode);
  state.notice = null;
  renderNotice();
  renderFiles();
}

function needsBielik(mode) {
  return mode === "bielik" || mode === "bielik_only";
}

function apiBase() {
  const local = location.hostname === "127.0.0.1" || location.hostname === "localhost";
  // A file opened directly, or the old :8080 page, still calls the API on :8000.
  if (location.protocol === "file:" || (local && location.port === "8080")) return "http://127.0.0.1:8000";
  return "";
}

// Set true to show the Statystyki tab again. The view, API and chart stay in place.
const SHOW_STATS = false;
const STAT_TYPES = ["odwolanie", "pelnomocnictwo", "przelew"];
let statsPayload = null;

if (SHOW_STATS) document.querySelector(".view-switch").hidden = false;

document.querySelector("#view-extract").addEventListener("click", () => showView("extract"));
document.querySelector("#view-stats").addEventListener("click", () => showView("stats"));
document.querySelector("#chart-flow img").addEventListener("load", (event) => {
  event.currentTarget.parentElement.hidden = false;
});
document.querySelector("#chart-flow img").addEventListener("error", (event) => {
  event.currentTarget.parentElement.hidden = true;
});

function showView(name) {
  const stats = name === "stats";
  document.querySelector("#extract-view").hidden = stats;
  document.querySelector("#stats-view").hidden = !stats;
  document.querySelector("#view-extract").setAttribute("aria-selected", String(!stats));
  document.querySelector("#view-stats").setAttribute("aria-selected", String(stats));
  if (stats) loadStats();
}

async function loadStats() {
  const error = document.querySelector("#stats-error");
  if (!statsPayload) {
    try {
      const response = await fetch(`${apiBase()}/api/stats`);
      if (!response.ok) throw new Error(await response.text());
      statsPayload = await response.json();
    } catch {
      error.hidden = false;
      error.textContent = t("statsMissing");
      return;
    }
  }
  error.hidden = true;
  renderStats();
}

function renderStats() {
  if (!statsPayload || document.querySelector("#stats-view").hidden) return;
  const overall = statsPayload;
  document.querySelector("#stats-f1").textContent = plNumber(overall.f1);
  document.querySelector("#stats-detail").textContent =
    `${t("statsPrecision")} ${plNumber(overall.precision)}  ·  ${t("statsRecall")} ${plNumber(overall.recall)}`;
  const cards = document.querySelector("#stats-cards");
  const types = overall.types || {};
  cards.replaceChildren(...STAT_TYPES.filter((key) => types[key]).map((key) => statCard(key, types[key])));
}

function statCard(key, bucket) {
  const card = document.createElement("article");
  card.className = "stats-card";
  const title = document.createElement("h2");
  title.textContent = copy[state.lang].statsTypes[key];
  const score = document.createElement("p");
  score.className = "stats-card-f1";
  score.textContent = plNumber(bucket.f1);
  const detail = document.createElement("p");
  detail.textContent =
    `${t("statsPrecision")} ${plNumber(bucket.precision)}  ·  ${t("statsRecall")} ${plNumber(bucket.recall)}`;
  const count = document.createElement("p");
  count.className = "stats-n";
  count.textContent = `n = ${bucket.documents}`;
  card.append(title, score, detail, count);
  return card;
}

function plNumber(value) {
  return Number(value).toFixed(2).replace(".", ",");
}

function llmHeaders() {
  const headers = {};
  const key = state.view === "task" ? taskApiKey : bielikKey.value.trim();
  if (key) headers["X-LLM-Key"] = key;
  if (state.view !== "task" && bielikBaseUrl.value.trim()) headers["X-LLM-Base-Url"] = bielikBaseUrl.value.trim();
  if (state.view !== "task" && bielikModel.value.trim()) headers["X-LLM-Model"] = bielikModel.value.trim();
  return headers;
}

async function addTaskKey() {
  const status = document.querySelector("#task-key-status");
  const value = taskKeyInput.value.trim();
  status.className = "key-status";
  if (!value) {
    status.classList.add("is-bad");
    status.textContent = t("taskKeyEmpty");
    return;
  }
  taskKeyAdd.disabled = true;
  status.textContent = t("bielikChecking");
  try {
    const response = await fetch(`${apiBase()}/api/llm/check`, {
      method: "POST",
      headers: { "X-LLM-Key": value },
    });
    const body = await response.json();
    if (!response.ok || !body.ok) throw new Error((body && (body.error || body.detail)) || t("bielikKeyRejected"));
    taskApiKey = value;
    taskKeyInput.value = "";
    state.taskKeyAdded = true;
    state.taskKeyModel = body.model || "Mistral";
    renderTaskKeyStatus();
  } catch (error) {
    taskApiKey = "";
    state.taskKeyAdded = false;
    status.classList.add("is-bad");
    status.textContent = (error && error.message) || t("bielikKeyRejected");
  } finally {
    taskKeyAdd.disabled = false;
  }
}

function renderTaskKeyStatus() {
  const status = document.querySelector("#task-key-status");
  if (!state.taskKeyAdded) return;
  status.className = "key-status is-ok";
  status.textContent = t("taskKeyAdded").replace("{model}", state.taskKeyModel || "Mistral");
}

function renderKeyStatus() {
  bielikStatus.className = "key-status";
  if (state.keyStatus === "checking") {
    bielikStatus.textContent = t("bielikChecking");
  } else if (state.keyStatus === "ok") {
    bielikStatus.classList.add("is-ok");
    bielikStatus.textContent = t("bielikOk").replace("{model}", state.keyModel || "Mistral");
  } else if (state.keyStatus && state.keyStatus.error) {
    bielikStatus.classList.add("is-bad");
    bielikStatus.textContent = state.keyStatus.error;
  } else if (state.serverKey && !bielikKey.value.trim()) {
    bielikStatus.textContent = t("bielikServerKey");
  } else {
    bielikStatus.textContent = "";
  }
}

async function checkKey() {
  state.keyStatus = "checking";
  renderKeyStatus();
  try {
    const response = await fetch(`${apiBase()}/api/llm/check`, { method: "POST", headers: llmHeaders() });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || String(response.status));
    state.keyModel = body.model || "";
    state.keyStatus = body.ok ? "ok" : { error: body.error || t("bielikKeyMissing") };
  } catch (error) {
    state.keyStatus = { error: error.message || apiErrorText() };
  }
  renderKeyStatus();
}

function apiErrorText() {
  return state.hosted ? t("apiErrorHosted") : t("apiError");
}

async function loadServerInfo() {
  try {
    const response = await fetch(`${apiBase()}/api/health`);
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json();
    state.hosted = Boolean(body.hosted);
    state.serverKey = Boolean(body.server_key);
    ocrWarning.hidden = body.ocr !== false;
  } catch {
    state.hosted = false;
  }
  // The hosted site has no input folder, so only drag and drop is offered there.
  viewSwitch.hidden = state.hosted;
  selectView(state.hosted ? "drop" : state.view);
  renderKeyStatus();
  if (!state.hosted) loadInputCases();
}

async function loadSamples() {
  try {
    const response = await fetch(`${apiBase()}/api/samples`);
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json();
    state.samples = body.samples || [];
  } catch {
    state.samples = [];
  }
  renderSamples();
}

function renderSamples() {
  samplePicker.hidden = state.view === "task" || state.samples.length === 0;
  const chosen = sampleSelect.value;
  sampleSelect.replaceChildren();
  state.samples.forEach((sample) => {
    const option = document.createElement("option");
    option.value = sample.id;
    const id = sample.id.replace(/^(przyklad|skany)_/, "");
    option.textContent = t(sample.kind === "scan" ? "sampleScan" : "sampleText").replace("{id}", id);
    sampleSelect.append(option);
  });
  if (chosen) sampleSelect.value = chosen;
}

async function loadSample() {
  const sample = state.samples.find((item) => item.id === sampleSelect.value);
  if (!sample || state.busy) return;
  sampleLoad.disabled = true;
  try {
    const files = await Promise.all(
      sample.files.map(async (entry) => {
        const response = await fetch(`${apiBase()}/api/samples/file?path=${encodeURIComponent(entry.path)}`);
        if (!response.ok) throw new Error(String(response.status));
        const blob = await response.blob();
        return new File([blob], entry.name, { type: "application/pdf", lastModified: 0 });
      })
    );
    await addFiles(files);
  } catch {
    state.notice = { key: "sampleError" };
    renderNotice();
  } finally {
    sampleLoad.disabled = false;
  }
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
  if (state.files.length === 0 || state.view === "task") {
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
  const ready = state.view === "task" ? selectedInputFiles().length > 0 : state.files.length > 0;
  submitButton.disabled = state.busy || !ready;
  if (!state.busy) submitButton.textContent = t("process");
  else if (state.progress) submitButton.textContent = t("processingCount").replace("{done}", state.progress.done).replace("{total}", state.progress.total);
  else submitButton.textContent = t("processingNow");
}

function renderInputCases() {
  const host = document.querySelector("#input-cases");
  host.replaceChildren();
  const hint = document.createElement("p");
  hint.className = "input-hint";
  hint.textContent = t("inputHint");
  host.append(hint);
  const files = inputCatalog.reduce((sum, item) => sum + item.files.length, 0);
  if (files === 0) {
    const empty = document.createElement("p");
    empty.className = "input-hint";
    empty.textContent = t("inputEmpty");
    host.append(empty);
    return;
  }
  const cases = inputCatalog.filter((item) => item.name !== "." && item.files.length > 0).length;
  const row = document.createElement("p");
  row.className = "case-total";
  row.textContent = t("casesAdded").replace("{cases}", String(cases)).replace("{files}", String(files));
  host.append(row);
}

function selectedInputFiles() {
  return inputCatalog.flatMap((item) => item.files.map((file) => ({ case: item.name, file: file.name })));
}

async function loadInputCases() {
  try {
    const response = await fetch(`${apiBase()}/api/input`);
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json();
    inputCatalog = body.cases || [];
    state.outputRoot = body.output_root || "";
  } catch {
    inputCatalog = [];
  }
  renderInputCases();
  renderFiles();
}

async function submitFiles() {
  if (state.busy) return;
  const task = state.view === "task";
  const jobs = task
    ? selectedInputFiles().map((job) => ({ ...job, name: job.case === "." ? job.file : `${job.case}/${job.file}` }))
    : state.files.slice(0, MAX_PDFS).map((item) => ({ upload: item.file, name: item.file.name }));
  if (jobs.length === 0) return;
  const mode = task ? TASK_MODE : state.mode;
  const hasKey = task ? taskApiKey || state.serverKey : bielikKey.value.trim() || state.serverKey;
  if (needsBielik(mode) && !hasKey) {
    state.notice = { key: "bielikKeyMissing" };
    renderNotice();
    (task ? taskKeyInput : bielikKey).focus();
    return;
  }
  state.busy = true;
  state.notice = null;
  state.run = {
    mode,
    servedMode: mode,
    jobs: jobs.map((job) => ({ name: job.name, status: "pending", item: null })),
    current: 0,
    usage: null,
    started: performance.now(),
    elapsed: null,
    done: false,
  };
  state.progress = { done: 0, total: jobs.length };
  renderNotice();
  renderFiles();
  renderInputCases();
  renderOutputs();

  // One request per document keeps every request short and lets the summary tick off each file.
  let caseName = "";
  try {
    for (let index = 0; index < jobs.length; index += 1) {
      const job = jobs[index];
      state.run.current = index;
      state.run.jobs[index].status = "running";
      renderOutputs();
      let body;
      if (task) {
        const response = await fetch(`${apiBase()}/api/extract/input/file`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...llmHeaders() },
          body: JSON.stringify({ case: job.case, file: job.file, mode }),
        });
        await ensureOk(response);
        body = await response.json();
      } else {
        const form = new FormData();
        form.append("mode", mode);
        if (caseName) form.append("case", caseName);
        form.append("files", job.upload, job.upload.name);
        const response = await fetch(`${apiBase()}/api/extract/batch`, { method: "POST", headers: llmHeaders(), body: form });
        await ensureOk(response);
        const batch = await response.json();
        caseName = batch.case || caseName;
        body = { result: (batch.results || [])[0], usage: batch.usage, mode: batch.mode };
      }
      state.run.jobs[index] = { name: job.name, status: "done", item: body.result || null };
      state.run.usage = addUsage(state.run.usage, body.usage);
      state.run.servedMode = body.mode || state.run.servedMode;
      state.progress.done = index + 1;
      renderFiles();
      renderOutputs();
    }
    if (!task) state.files = [];
  } catch (error) {
    state.notice = error && error.notice ? error.notice : { key: "apiError" };
  } finally {
    state.run.elapsed = (performance.now() - state.run.started) / 1000;
    state.run.done = true;
    state.busy = false;
    state.progress = null;
    renderNotice();
    renderFiles();
    renderOutputs();
    if (!state.hosted) loadInputCases();
  }
}

function addUsage(total, extra) {
  if (!extra) return total;
  if (!total) return { ...extra };
  const sum = { ...total };
  ["prompt_tokens", "completion_tokens", "calls", "failures"].forEach((key) => {
    sum[key] = (Number(total[key]) || 0) + (Number(extra[key]) || 0);
  });
  return sum;
}

async function ensureOk(response) {
  if (response.ok) return;
  let detail = "";
  try {
    detail = (await response.json()).detail;
  } catch {
    detail = "";
  }
  const error = new Error(String(response.status));
  if (detail === "llm_key_missing") error.notice = { key: "bielikKeyMissing" };
  else if (detail === "llm_key_rejected") error.notice = { key: "bielikKeyRejected" };
  else if (typeof detail === "string" && detail) error.notice = { text: detail };
  throw error;
}

function renderOutputs() {
  summary.replaceChildren();
  const run = state.run;
  if (!run) {
    summary.append(placeholder("summaryEmpty"));
    return;
  }
  const finished = run.jobs.filter((job) => job.status === "done");
  const head = document.createElement("p");
  head.className = "progress-head";
  head.textContent = t("progressHead").replace("{done}", finished.length).replace("{total}", run.jobs.length);
  const bar = document.createElement("div");
  bar.className = "progress-bar";
  const fill = document.createElement("span");
  fill.style.width = `${run.jobs.length ? (finished.length / run.jobs.length) * 100 : 0}%`;
  bar.append(fill);
  summary.append(head, bar);

  const list = document.createElement("ol");
  list.className = "progress-list";
  run.jobs.forEach((job, index) => {
    if (job.status === "pending" && !run.done && index > run.current + 2) return;
    const row = document.createElement("li");
    row.className = `progress-item is-${job.status}`;
    const name = document.createElement("span");
    name.className = "progress-name";
    name.textContent = job.name;
    const outcome = document.createElement("span");
    outcome.className = "progress-state";
    if (job.status === "done" && job.item) {
      outcome.textContent = `${typeLabel(job.item.document_type)} · ${t("statuses")[job.item.status] || job.item.status}`;
      outcome.classList.add(jobOutcome(job.item) === "valid" ? "is-ok" : "is-bad");
      const badge = ocrBadge(job.item);
      if (badge) name.append(badge);
    } else if (job.status === "running") {
      outcome.textContent = t("progressRunning");
    } else {
      outcome.textContent = t("progressPending");
    }
    row.title = job.status === "done" ? t("processingIndex").replace("{index}", index + 1) : "";
    row.append(name, outcome);
    list.append(row);
  });
  summary.append(list);
  const running = list.querySelector(".is-running");
  if (running) running.scrollIntoView({ block: "nearest" });

  if (!run.done) return;

  const items = finished.map((job) => job.item).filter(Boolean);
  const counts = { valid: 0, invalid: 0, failed: 0 };
  const byType = {};
  items.forEach((item) => {
    const outcome = jobOutcome(item);
    counts[outcome] += 1;
    if (outcome === "valid") byType[item.document_type] = (byType[item.document_type] || 0) + 1;
  });

  const report = document.createElement("div");
  report.className = "run-report";
  const line = (text, className = "") => {
    const paragraph = document.createElement("p");
    paragraph.className = className;
    paragraph.textContent = text;
    report.append(paragraph);
    return paragraph;
  };
  line(
    t("finishedIn")
      .replace("{total}", formatDuration(run.elapsed))
      .replace("{average}", formatDuration(items.length ? run.elapsed / items.length : 0)),
    "report-strong"
  );
  if (run.servedMode === "bielik" || run.servedMode === "bielik_only") {
    const usage = run.usage || {};
    const prompt = Number(usage.prompt_tokens) || 0;
    const completion = Number(usage.completion_tokens) || 0;
    const failures = Number(usage.failures) || 0;
    const failed = failures ? ` (${t("llmFailures").replace("{count}", failures)})` : "";
    line(
      t("mistralTokens")
        .replace("{total}", prompt + completion)
        .replace("{prompt}", prompt)
        .replace("{completion}", completion)
        .replace("{calls}", Number(usage.calls) || 0) + failed
    );
  } else {
    line(t("mistralNone"));
  }
  const breakdown = VALID_TYPES.filter((type) => byType[type])
    .map((type) => `${typeLabel(type)} ${byType[type]}`)
    .join(", ");
  line(t("validDocs").replace("{count}", counts.valid) + (breakdown ? ` (${breakdown})` : ""), "is-ok");
  line(t("invalidDocs").replace("{count}", counts.invalid));
  if (counts.failed) line(t("failedDocs").replace("{count}", counts.failed), "is-bad");

  const folders = [...new Set(items.map((item) => item.output).filter(Boolean).map((path) => path.replace(/[^/]+$/, "")))];
  if (folders.length) {
    line(t("outputWhere"));
    const paths = document.createElement("ul");
    paths.className = "output-paths";
    folders.forEach((folder) => {
      const entry = document.createElement("li");
      entry.textContent = folder;
      paths.append(entry);
    });
    report.append(paths);
    if (state.outputRoot) line(t("outputRoot").replace("{path}", state.outputRoot), "input-hint");
  }
  summary.append(report);
}

function jobOutcome(item) {
  if (item.status === "ok" && VALID_TYPES.includes(item.document_type)) return "valid";
  if (item.status === "unrecognized") return "invalid";
  return "failed";
}

function typeLabel(documentType) {
  return t("types")[documentType] || t("types").unknown;
}

function ocrBadge(item) {
  if (!item || item.text_source !== "ocr") return null;
  const badge = document.createElement("span");
  badge.className = "ocr-badge";
  badge.textContent = "OCR";
  return badge;
}

function placeholder(key) {
  const paragraph = document.createElement("p");
  paragraph.className = "placeholder";
  paragraph.textContent = t(key);
  return paragraph;
}

function resetAll() {
  if (state.busy) return;
  state.files = [];
  state.run = null;
  state.notice = null;
  fileInput.value = "";
  renderNotice();
  renderFiles();
  renderOutputs();
}

applyCopy();
selectMode(state.mode);
loadServerInfo();
loadSamples();

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

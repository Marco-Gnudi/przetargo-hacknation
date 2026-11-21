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

const state = {
  mode: "regular",
  files: [],
  submissions: [],
  nextId: 1,
};

const modeLabel = {
  regular: "Regular Processing (No LLM)",
  bielik: "Bielik Powered Processing",
};

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
    inputMessage.textContent = `Only PDF files can be added. Skipped: ${rejected.join(", ")}`;
  } else if (added === 0) {
    inputMessage.textContent = "Those PDFs are already attached.";
  } else {
    inputMessage.textContent = "";
  }

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
      name.textContent = `${item.file.name} (${formatSize(item.file.size)})`;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-file";
      remove.textContent = "Remove";
      remove.addEventListener("click", (event) => {
        event.stopPropagation();
        state.files = state.files.filter((entry) => entry.id !== item.id);
        inputMessage.textContent = "";
        renderFiles();
      });
      row.append(name, remove);
      fileList.append(row);
    });
  }
  submitButton.disabled = state.files.length === 0;
}

function submitFiles() {
  if (state.files.length === 0) return;

  state.submissions.push({
    count: state.files.length,
    names: state.files.map((item) => item.file.name),
    mode: state.mode,
  });
  state.files = [];
  inputMessage.textContent = "";
  renderFiles();
  renderOutputs();
}

function renderOutputs() {
  const latest = state.submissions[state.submissions.length - 1];
  if (!latest) {
    summary.innerHTML = '<p class="placeholder">Is the submission complete, is any information missing?</p>';
    detail.innerHTML = '<p class="placeholder">Exact sections and fields</p>';
  } else {
    summary.innerHTML = "";
    const text = document.createElement("p");
    text.className = "summary-text";
    text.textContent = `${latest.count} PDF${latest.count === 1 ? "" : "s"} received with ${modeLabel[latest.mode]}. Extraction is not connected yet, so completeness is unknown.`;
    summary.append(text);

    detail.innerHTML = "";
    const list = document.createElement("ul");
    list.className = "detail-list";
    latest.names.forEach((name) => {
      const item = document.createElement("li");
      item.textContent = name;
      list.append(item);
    });
    detail.append(list);
  }

  resultsBody.replaceChildren();
  if (state.submissions.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = "No submissions yet. Add one or more PDFs, then submit.";
    row.append(cell);
    resultsBody.append(row);
    return;
  }

  state.submissions.forEach((submission) => {
    const row = document.createElement("tr");
    [String(submission.count), "—", "Not processed yet"].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    resultsBody.append(row);
  });
}

function resetAll() {
  state.files = [];
  state.submissions = [];
  inputMessage.textContent = "";
  fileInput.value = "";
  renderFiles();
  renderOutputs();
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const askButton = document.querySelector("#ask-button");
const formMessage = document.querySelector("#form-message");
const answer = document.querySelector("#answer");
const statusBadge = document.querySelector("#status-badge");
const traceId = document.querySelector("#trace-id");
const sql = document.querySelector("#sql");
const rowCount = document.querySelector("#row-count");
const rowsEmpty = document.querySelector("#rows-empty");
const rowsTable = document.querySelector("#rows-table");
const clarification = document.querySelector("#clarification");
const clarificationQuestion = document.querySelector("#clarification-question");
const clarificationOptions = document.querySelector("#clarification-options");
const clarificationForm = document.querySelector("#clarification-form");
const clarificationText = document.querySelector("#clarification-text");
const clarificationMessage = document.querySelector("#clarification-message");
const tableSelect = document.querySelector("#table-select");
const schemaDetails = document.querySelector("#schema-details");
const schemaError = document.querySelector("#schema-error");
const retrySchema = document.querySelector("#retry-schema");

let loading = false;
let originalQuestion = "";
let schema = null;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    formMessage.textContent = "Enter a question before submitting.";
    questionInput.focus();
    return;
  }
  originalQuestion = question;
  formMessage.textContent = "";
  submitQuestion(question);
});

clarificationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const explanation = clarificationText.value.trim();
  if (!explanation) {
    clarificationMessage.textContent = "Enter an explanation before submitting.";
    clarificationText.focus();
    return;
  }
  clarificationMessage.textContent = "";
  submitQuestion(clarifiedQuestion(explanation));
});

tableSelect.addEventListener("change", () => renderSchemaTable(tableSelect.value));
retrySchema.addEventListener("click", loadSchema);

async function submitQuestion(question) {
  if (loading) return;
  setLoading(true);
  resetResult();
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) {
      renderFailure(payload.error || "Ask Data could not complete the request.", payload.request_id);
      return;
    }
    renderResult(payload);
  } catch {
    renderFailure("The local Ask Data service could not be reached.");
  } finally {
    setLoading(false);
  }
}

function setLoading(value) {
  loading = value;
  askButton.disabled = value;
  questionInput.disabled = value;
  clarificationText.disabled = value;
  statusBadge.dataset.status = value ? "loading" : statusBadge.dataset.status;
  if (value) {
    statusBadge.textContent = "Running";
    answer.textContent = "QueryForge is resolving and validating your request…";
  }
}

function resetResult() {
  clarification.hidden = true;
  clarificationOptions.replaceChildren();
  clarificationText.value = "";
  clarificationMessage.textContent = "";
  traceId.hidden = true;
  sql.textContent = "No approved query yet.";
  rowCount.textContent = "0 rows";
  rowsTable.hidden = true;
  rowsTable.querySelector("thead").replaceChildren();
  rowsTable.querySelector("tbody").replaceChildren();
  rowsEmpty.hidden = false;
  rowsEmpty.textContent = "Returned rows will appear here.";
}

function renderResult(payload) {
  statusBadge.dataset.status = payload.status;
  statusBadge.textContent = statusLabel(payload.status);
  answer.textContent = payload.answer;
  traceId.textContent = `Trace: ${payload.trace_id}`;
  traceId.hidden = false;

  if (payload.status === "clarification_required") {
    renderClarification(payload);
    return;
  }
  if (payload.status !== "ok") return;

  sql.textContent = payload.sql || "No approved query was returned.";
  rowCount.textContent = `${payload.row_count} ${payload.row_count === 1 ? "row" : "rows"}`;
  renderRows(payload.rows);
}

function renderRows(rows) {
  if (!rows.length) {
    rowsEmpty.textContent = "The approved query returned no rows.";
    return;
  }
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const headRow = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = humanize(column);
    headRow.append(th);
  });
  rowsTable.querySelector("thead").append(headRow);
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = formatValue(row[column]);
      tr.append(td);
    });
    rowsTable.querySelector("tbody").append(tr);
  });
  rowsEmpty.hidden = true;
  rowsTable.hidden = false;
}

function renderClarification(payload) {
  clarification.hidden = false;
  clarificationQuestion.textContent = payload.clarification_question || payload.answer;
  payload.clarification_candidates.forEach((candidate) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = candidate.label;
    button.addEventListener("click", () => submitQuestion(clarifiedQuestion(candidate.label)));
    clarificationOptions.append(button);
  });
}

function clarifiedQuestion(explanation) {
  return `Original question: ${originalQuestion}\nUser clarification: ${explanation}`;
}

function renderFailure(message, supportId = "") {
  statusBadge.dataset.status = "error";
  statusBadge.textContent = "Error";
  answer.textContent = message;
  if (supportId) {
    traceId.textContent = `Request: ${supportId}`;
    traceId.hidden = false;
  }
}

function statusLabel(status) {
  const labels = {
    ok: "Complete",
    blocked: "Blocked",
    unsupported: "Unsupported",
    invalid: "Invalid",
    error: "Error",
    clarification_required: "Needs clarification",
  };
  return labels[status] || "Complete";
}

async function loadSchema() {
  tableSelect.disabled = true;
  schemaError.hidden = true;
  schemaDetails.hidden = true;
  tableSelect.replaceChildren(new Option("Loading schema…", ""));
  try {
    const response = await fetch("/api/schema");
    if (!response.ok) throw new Error("schema request failed");
    schema = await response.json();
    tableSelect.replaceChildren();
    schema.tables.forEach((table) => tableSelect.add(new Option(humanize(table.name), table.name)));
    tableSelect.disabled = false;
    renderSchemaTable(schema.tables[0]?.name);
  } catch {
    tableSelect.replaceChildren(new Option("Schema unavailable", ""));
    schemaError.hidden = false;
  }
}

function renderSchemaTable(name) {
  const table = schema?.tables.find((item) => item.name === name);
  if (!table) return;
  tableSelect.value = table.name;
  document.querySelector("#table-name").textContent = humanize(table.name);
  document.querySelector("#table-description").textContent = table.description;
  document.querySelector("#table-grain").textContent = table.grain;

  const columns = document.querySelector("#column-list");
  columns.replaceChildren();
  table.columns.forEach((column) => {
    const li = document.createElement("li");
    const nameSpan = document.createElement("span");
    nameSpan.className = "column-name";
    nameSpan.textContent = column.name;
    const typeSpan = document.createElement("span");
    typeSpan.className = "column-type";
    typeSpan.textContent = ` · ${column.data_type}`;
    li.append(nameSpan, typeSpan);
    if (column.description) li.append(` · ${column.description}`);
    columns.append(li);
  });

  const relationships = document.querySelector("#relationship-list");
  relationships.replaceChildren();
  const related = schema.relationships.filter(
    (item) => item.source_table === table.name || item.target_table === table.name,
  );
  if (!related.length) {
    relationships.append(Object.assign(document.createElement("li"), { textContent: "None" }));
  } else {
    related.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item.source_table}.${item.source_column} → ${item.target_table}.${item.target_column}`;
      relationships.append(li);
    });
  }
  schemaDetails.hidden = false;
}

function humanize(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value) {
  if (value === null) return "null";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

loadSchema();

const api = {
  entities: "/api/entities",
  clients: "/api/clients",
  values: "/api/values",
  templates: "/api/templates",
  placeholders: (id) => `/api/templates/${id}/placeholders`,
  generate: "/api/generate",
  history: "/api/history",
};

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function refreshEntities() {
  const data = await fetchJSON(api.entities);
  const list = document.getElementById("entities-list");
  list.innerHTML = data.map(e => `<div>• ${e.name} <code>${e.code}</code></div>`).join("") || "<em>пусто</em>";
  const sel = document.getElementById("entity-select");
  sel.innerHTML = data.map(e => `<option value="${e.id}">${e.name} ${e.code}</option>`).join("");
}

async function refreshClients() {
  const data = await fetchJSON(api.clients);
  document.getElementById("clients-list").innerHTML = data.map(c => `<div>• ${c.name}</div>`).join("") || "<em>пусто</em>";
  const sel1 = document.getElementById("client-select");
  sel1.innerHTML = data.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
  const sel2 = document.getElementById("clients-multi");
  sel2.innerHTML = data.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
}

async function refreshValues() {
  const data = await fetchJSON(api.values);
  const list = document.getElementById("values-list");
  list.innerHTML = data.map(v => `<div>• [client ${v.client_id}] [entity ${v.entity_id}] = ${v.value_text}</div>`).join("") || "<em>пусто</em>";
}

async function refreshTemplates() {
  const data = await fetchJSON(api.templates);
  document.getElementById("templates-list").innerHTML = data.map(t => `<div>• ${t.filename}</div>`).join("") || "<em>пусто</em>";
  const sel = document.getElementById("template-select");
  sel.innerHTML = data.map(t => `<option value="${t.id}">${t.filename}</option>`).join("");
  updatePlaceholders();
}

async function refreshHistory() {
  const data = await fetchJSON(api.history);
  document.getElementById("history-list").innerHTML = data.map(h => `<div>• [${h.id}] template ${h.template_id}, client ${h.client_id} — ${h.output_path}</div>`).join("") || "<em>пусто</em>";
}

// Forms

document.getElementById("entity-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await fetchJSON(api.entities, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ name: fd.get("name"), code: fd.get("code") })
    });
    e.target.reset();
    refreshEntities();
  } catch(err) { alert(err); }
});

document.getElementById("client-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await fetchJSON(api.clients, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ name: fd.get("name") })
    });
    e.target.reset();
    refreshClients();
  } catch(err) { alert(err); }
});

document.getElementById("value-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await fetchJSON(api.values, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        entity_id: Number(fd.get("entity_id")),
        client_id: Number(fd.get("client_id")),
        value_text: fd.get("value_text")
      })
    });
    e.target.reset();
    refreshValues();
  } catch(err) { alert(err); }
});

document.getElementById("template-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const res = await fetch(api.templates, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    e.target.reset();
    refreshTemplates();
  } catch(err) { alert(err); }
});

async function updatePlaceholders() {
  const sel = document.getElementById("template-select");
  if (!sel.value) return;
  try {
    const data = await fetchJSON(api.placeholders(sel.value));
    document.getElementById("placeholders").innerHTML =
      `<strong>Плейсхолдеры в шаблоне:</strong> ` +
      (data.placeholders.map(p => `<code>${p}</code>`).join(" ") || "—");
  } catch(err) { console.warn(err); }
}

document.getElementById("template-select").addEventListener("change", updatePlaceholders);

// Генерация

document.getElementById("generate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const template_id = Number(fd.get("template_id"));
  const on_missing = fd.get("on_missing");
  const clientsSel = document.getElementById("clients-multi");
  const client_ids = Array.from(clientsSel.selectedOptions).map(o => Number(o.value));
  if (client_ids.length === 0) { alert("Выберите хотя бы одного клиента"); return; }

  try {
    const res = await fetch(api.generate, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ template_id, client_ids, on_missing })
    });
    if (!res.ok) throw new Error(await res.text());

    // Скачивание результата (docx или zip)
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "attachment; filename=output";
    const fname = cd.split("filename=").pop().replaceAll('"','');

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = fname; a.click();
    URL.revokeObjectURL(url);

    refreshHistory();
  } catch(err) { alert(err); }
});

// init
(async function(){
  await refreshEntities();
  await refreshClients();
  await refreshValues();
  await refreshTemplates();
  await refreshHistory();
})();

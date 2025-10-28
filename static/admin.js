// ============================================================
// 🧿 Amulet Admin Pro v2.9 — Full JS
// ============================================================

async function api(url, method = "GET", data = null) {
  const opt = { method, headers: { "Content-Type": "application/json" } };
  if (data) opt.body = JSON.stringify(data);
  const r = await fetch(url, opt);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return await r.json();
}
function $(id) { return document.getElementById(id); }
function toast(m) { console.log(m); alert(m); }

// ============================================================
// ===== LICENSES =====
// ============================================================
async function loadLicenses() {
  const q = $("licSearch").value.trim();
  const data = await api("/admin_api/licenses" + (q ? `?q=${q}` : ""));
  const tb = $("licTbody"); tb.innerHTML = "";
  data.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td><span style="cursor:pointer;color:#2563eb" onclick="copyToClipboard('${x.key}')">${x.key}</span></td>
      <td>${x.credit}</td>
      <td>${x.active ? '✅' : '❌'}</td>
      <td>${x.mac_id || ''}</td>
      <td>${x.created_at || ''}</td>
      <td>
        <button class='btn btn-sm btn-outline-primary me-1' onclick='editLicense(${x.id},"${x.key}","${x.mac_id||""}",${x.credit},${x.active})'>✏️</button>
        <button class='btn btn-sm btn-outline-danger' onclick='deleteLicense(${x.id})'>🗑</button>
      </td>`;
    tb.appendChild(tr);
  });
}

function editLicense(id, key, mac, credit, active) {
  $("licId").value = id;
  $("licKey").value = key;
  $("licMac").value = mac;
  $("licCredit").value = credit;
  $("licActive").checked = active;
  $("licFormTitle").innerText = "Редагувати ліцензію";
}

function resetLicenseForm() {
  $("licId").value = "";
  $("licKey").value = "";
  $("licMac").value = "";
  $("licCredit").value = 0;
  $("licActive").checked = true;
  $("licFormTitle").innerText = "Додати ліцензію";
}

async function submitLicense() {
  const d = {
    key: $("licKey").value.trim(),
    mac_id: $("licMac").value.trim(),
    credit: +$("licCredit").value,
    active: $("licActive").checked
  };
  const id = $("licId").value;
  if (id) await api(`/admin_api/licenses/${id}`, "PUT", d);
  else await api("/admin_api/licenses", "POST", d);
  toast("💾 Збережено");
  loadLicenses();
  resetLicenseForm();
}

async function deleteLicense(id) {
  if (!confirm("Видалити ліцензію?")) return;
  await api(`/admin_api/licenses/${id}`, "DELETE");
  loadLicenses();
}

async function filterLicenses() {
  const min = $("minCredit").value, max = $("maxCredit").value, active = $("filterActive").value;
  const data = await api(`/admin_api/licenses/filter?min_credit=${min}&max_credit=${max}&active=${active}`);
  const tb = $("licTbody"); tb.innerHTML = "";
  data.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td><span style='cursor:pointer;color:#2563eb' onclick="copyToClipboard('${x.key}')">${x.key}</span></td>
      <td>${x.credit}</td>
      <td>${x.active ? '✅' : '❌'}</td>
      <td>${x.mac_id || ''}</td>
      <td><button class='btn btn-sm btn-outline-danger' onclick='deleteLicense(${x.id})'>🗑</button></td>`;
    tb.appendChild(tr);
  });
}

function copyToClipboard(t) {
  navigator.clipboard.writeText(t);
  toast("Скопійовано: " + t);
}

// ============================================================
// ===== API KEYS =====
// ============================================================
async function loadKeys() {
  const d = await api("/admin_api/apikeys");
  const tb = $("keysTbody"); tb.innerHTML = "";
  d.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td>${x.api_key}</td>
      <td>${x.status}</td>
      <td><button class='btn btn-sm btn-outline-danger' onclick='deleteKey(${x.id})'>🗑</button></td>`;
    tb.appendChild(tr);
  });
}
async function submitApiKey() {
  const d = { api_key: $("keyValue").value, status: $("keyStatus").value };
  await api("/admin_api/apikeys", "POST", d);
  toast("API key added");
  loadKeys();
}
async function deleteKey(id) {
  if (!confirm("Видалити ключ?")) return;
  await api(`/admin_api/apikeys/${id}`, "DELETE");
  loadKeys();
}

// ============================================================
// ===== VOICES =====
// ============================================================
async function loadVoices() {
  const d = await api("/admin_api/voices");
  const tb = $("voicesTbody"); tb.innerHTML = "";
  d.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td>${x.name}</td>
      <td>${x.voice_id}</td>
      <td>${x.active ? '✅' : '❌'}</td>
      <td><button class='btn btn-sm btn-outline-danger' onclick='deleteVoice(${x.id})'>🗑</button></td>`;
    tb.appendChild(tr);
  });
}

async function submitVoice() {
  const d = { name: $("voiceName").value.trim(), voice_id: $("voiceValue").value.trim(), active: $("voiceActive").checked };
  await api("/admin_api/voices", "POST", d);
  toast("Voice saved");
  loadVoices();
}

async function deleteVoice(id) {
  if (!confirm("Видалити голос?")) return;
  await api(`/admin_api/voices/${id}`, "DELETE");
  loadVoices();
}

async function deleteAllVoices() {
  if (!confirm("Видалити всі голоси?")) return;
  await api("/admin_api/voices/delete_all", "DELETE");
  toast("All voices deleted");
  loadVoices();
}

// -------- BULK UPLOAD --------
async function uploadVoices() {
  const f = $("voiceFile").files[0];
  if (!f) return toast("Вибери .txt файл");

  const txt = await f.text();
  const lines = txt.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  const voices = [];

  for (const line of lines) {
    const [name, id] = line.split(":").map(x => x.trim());
    if (name && id) voices.push({ name, voice_id: id });
  }

  if (!voices.length) return toast("Порожній або некоректний файл");

  const res = await api("/admin_api/voices/bulk", "POST", { voices });
  toast(`✅ Завантажено ${res.added} голосів`);
  loadVoices();
}

// -------- EXPORT VOICES --------
async function exportVoices() {
  const d = await api("/admin_api/voices");
  if (!d.length) return toast("Немає голосів для експорту");
  const lines = d.map(v => `${v.name}:${v.voice_id}`).join("\n");
  const blob = new Blob([lines], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "voices_export.txt";
  a.click();
  toast(`📥 Експортовано ${d.length} голосів`);
}

function resetVoiceForm() {
  $("voiceName").value = "";
  $("voiceValue").value = "";
  $("voiceActive").checked = true;
}

// ============================================================
// ===== LOGS =====
// ============================================================
async function loadLogs() {
  const d = await api("/admin_api/logs");
  const tb = $("logsTbody"); tb.innerHTML = "";
  d.forEach(x => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${x.id}</td>
      <td>${x.license_id}</td>
      <td>${x.action}</td>
      <td>${x.char_count}</td>
      <td>${x.details || ''}</td>
      <td>${x.created_at}</td>`;
    tb.appendChild(tr);
  });
}

// ============================================================
// ===== CONFIG =====
// ============================================================
async function loadConfig() {
  const c = await api("/admin_api/config");
  $("cfgLatest").value = c.latest_version || "";
  $("cfgForce").checked = c.force_update;
  $("cfgMaint").checked = c.maintenance;
  $("cfgMaintMsg").value = c.maintenance_message || "";
  $("cfgDesc").value = c.update_description || "";
  $("cfgLinks").value = c.update_links || "";
}

async function saveConfig() {
  const d = {
    latest_version: $("cfgLatest").value,
    force_update: $("cfgForce").checked,
    maintenance: $("cfgMaint").checked,
    maintenance_message: $("cfgMaintMsg").value,
    update_description: $("cfgDesc").value,
    update_links: $("cfgLinks").value
  };
  await api("/admin_api/config", "PUT", d);
  toast("Config saved");
}

function downloadBackup() {
  const a = document.createElement("a");
  a.href = "/admin_api/backup";
  a.download = "amulet_backup.json";
  a.click();
}

function downloadUsersBackup() {
  const a = document.createElement("a");
  a.href = "/admin_api/backup/users";
  a.download = "users_backup.json";
  a.click();
}

// ============================================================
// ===== API CONSOLE =====
// ============================================================
async function runConsole() {
  try {
    const action = $("apiAction").value;
    const payload = $("apiPayload").value;
    const d = payload ? JSON.parse(payload) : {};
    d.action = action;
    const res = await api("/api", "POST", d);
    $("apiResult").innerText = JSON.stringify(res, null, 2);
  } catch (e) {
    $("apiResult").innerText = "❌ " + e.message;
  }
}

function formatJson() {
  try {
    $("apiPayload").value = JSON.stringify(JSON.parse($("apiPayload").value), null, 2);
  } catch (e) {
    toast("Bad JSON");
  }
}

// ============================================================
// ===== INIT =====
// ============================================================
window.addEventListener("DOMContentLoaded", () => {
  loadLicenses();
  loadKeys();
  loadVoices();
  loadLogs();
  loadConfig();
});
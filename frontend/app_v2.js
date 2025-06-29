function getBaseUrl() {
  const url = document.getElementById("apiUrl").value.trim();
  return url || "http://localhost:8000";
}

function displayResults(data) {
  if (Array.isArray(data)) {
    const out = data.map((r, i) => `#${i + 1}\n${r.stdout || ""}`).join("\n---\n");
    const err = data
      .map((r) => r.stderr)
      .filter((s) => s)
      .join("\n---\n");
    const met = data
      .map(
        (r, i) =>
          `#${i + 1} exitCode: ${r.exitCode}, duration: ${r.duration.toFixed(0)}ms, memory: ${r.memoryUsed}KB, timedOut: ${r.timedOut}`
      )
      .join("\n");
    document.getElementById("stdout").textContent = out;
    document.getElementById("stderr").textContent = err;
    document.getElementById("metrics").textContent = met;
  } else {
    document.getElementById("stdout").textContent = data.stdout || "";
    document.getElementById("stderr").textContent = data.stderr || "";
    document.getElementById("metrics").textContent =
      `exitCode: ${data.exitCode}, duration: ${data.duration.toFixed(0)}ms, ` +
      `memory: ${data.memoryUsed}KB, timedOut: ${data.timedOut}`;
  }
}

/**
 * Connect to the WebSocket progress stream and update the UI.
 */
function watchProgress(requestId) {
  const wsUrl = getBaseUrl().replace(/^http/, "ws") + `/ws/progress/${requestId}`;
  const socket = new WebSocket(wsUrl);
  const results = [];
  socket.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "progress") {
      results[msg.index] = msg.result;
      displayResults(results.filter((r) => r));
    } else if (msg.type === "final") {
      displayResults(msg.results);
      socket.close();
    }
  };
  socket.onerror = () => {
    document.getElementById("stderr").textContent = "WebSocket error";
  };
}

document.getElementById("run").addEventListener("click", async () => {
  const lang = document.getElementById("lang").value;
  const code = document.getElementById("code").value;
  const stdinsRaw = document.getElementById("stdins").value;
  let stdins;
  if (stdinsRaw.trim()) {
    stdins = stdinsRaw.trim().split(/\n\s*\n/);
  } else {
    stdins = [""];
  }
  const token = document.getElementById("token").value.trim();
  const timeLimit = parseInt(document.getElementById("timeLimit").value);
  const memoryLimit = parseInt(document.getElementById("memoryLimit").value);

  document.getElementById("stdout").textContent = "실행 중...";
  document.getElementById("stderr").textContent = "";
  document.getElementById("metrics").textContent = "";

  const body = { language: lang, code, stdins };
  if (!isNaN(timeLimit)) body.timeLimit = timeLimit;
  if (!isNaN(memoryLimit)) body.memoryLimit = memoryLimit;

  const res = await fetch(`${getBaseUrl()}/execute_v2`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (!res.ok) {
    document.getElementById("stderr").textContent =
      data.error || data.detail || "Error";
    document.getElementById("stdout").textContent = "";
    return;
  }

  watchProgress(data.requestId);
});

function getBaseUrl() {
  const url = document.getElementById("apiUrl").value.trim();
  return url || "http://localhost:8000";
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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

async function pollResult(token, requestId) {
  while (true) {
    await sleep(1000);
    const res = await fetch(`${getBaseUrl()}/execute/${requestId}`, {
      headers: { Authorization: token ? `Bearer ${token}` : "" },
    });
    const data = await res.json();
    if (res.status === 202) {
      continue;
    } else if (res.status === 200) {
      displayResults(data);
      break;
    } else {
      document.getElementById("stderr").textContent = data.error || "Error";
      break;
    }
  }
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

  const res = await fetch(`${getBaseUrl()}/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (res.status === 202) {
    await pollResult(token, data.requestId);
    return;
  }

  if (!res.ok) {
    document.getElementById("stderr").textContent =
      data.error || data.detail || "Error";
    document.getElementById("stdout").textContent = "";
    return;
  }

  displayResults(data);
});

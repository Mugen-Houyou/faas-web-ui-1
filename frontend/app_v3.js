let totalRuns = 1;

function getBaseUrl() {
  const url = document.getElementById("apiUrl").value.trim();
  return url || "http://localhost:18651";
}

function displayRunResults(data) {
  const statusMap = {
    success: "PASS",
    compile_error: "COMPILE ERROR",
    wrong_output: "WRONG OUTPUT",
    timeout: "TIMEOUT",
    failure: "FAIL",
  };
  const out = data
    .map((r, i) => {
      const status = r.status ? ` [${statusMap[r.status] || r.status}]` : "";
      return `#${i + 1}${status}\n${r.stdout || ""}`;
    })
    .join("\n---\n");
  const err = data
    .map((r) => r.stderr)
    .filter((s) => s)
    .join("\n---\n");
  const met = data
    .map(
      (r, i) => {
        const status = r.status ? `, status: ${statusMap[r.status] || r.status}` : "";
        return `#${i + 1} exitCode: ${r.exitCode}, duration: ${r.duration.toFixed(0)}ms, memory: ${r.memoryUsed}KB, timedOut: ${r.timedOut}${status}`;
      }
    )
    .join("\n");
  document.getElementById("stdout").textContent = out;
  document.getElementById("stderr").textContent = err;
  document.getElementById("metrics").textContent = met;
}

function displayGradedResults(data) {
  const lines = data.results.map((r) => {
    const statusMap = {
      success: "PASS",
      compile_error: "COMPILE ERROR",
      wrong_output: "WRONG OUTPUT",
      timeout: "TIMEOUT",
      failure: "FAIL",
    };
    const status = statusMap[r.status] || r.status;
    return (
      `#${r.id} [${r.visibility}] ${status}\n` +
      `stdout: ${r.stdout}\n` +
      `stderr: ${r.stderr}\n` +
      `exitCode: ${r.exitCode}, duration: ${r.duration.toFixed(0)}ms, memory: ${r.memoryUsed}KB, timedOut: ${r.timedOut}`
    );
  });
  document.getElementById("stdout").textContent = lines.join("\n---\n");
  const msgEl = document.getElementById("judgeMessage");
  msgEl.textContent = data.allPassed
    ? "모든 테스트를 통과했습니다!"
    : "일부 테스트가 실패했습니다.";
  msgEl.style.color = data.allPassed ? "green" : "red";
  totalRuns = data.results.length;
  updateProgress(totalRuns);
}

function updateProgress(completed) {
  const percent = Math.min(100, (completed / totalRuns) * 100);
  document.getElementById("progressBar").style.width = `${percent}%`;
  document.getElementById("progressLabel").textContent = `${percent.toFixed(0)}%`;
}

function watchProgress(requestId) {
  const wsUrl = getBaseUrl().replace(/^http/, "ws") + `/ws/progress/${requestId}`;
  const socket = new WebSocket(wsUrl);
  const results = [];
  socket.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "progress") {
      if (msg.total) {
        totalRuns = msg.total;
      }
      results[msg.index] = msg.result;
      const completed = results.filter((r) => r).length;
      displayRunResults(results.filter((r) => r));
      updateProgress(completed);
    } else if (msg.type === "final") {
      if (msg.error) {
        document.getElementById("stderr").textContent = msg.error;
        updateProgress(totalRuns);
        socket.close();
        return;
      }
      displayGradedResults(msg);
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
  const problemId = document.getElementById("problemId").value.trim();
  const token = document.getElementById("token").value.trim();

  document.getElementById("stdout").textContent = "실행 중...";
  document.getElementById("stderr").textContent = "";
  document.getElementById("judgeMessage").textContent = "";
  document.getElementById("metrics").textContent = "";
  totalRuns = 1;
  updateProgress(0);

  const body = { language: lang, code, problemId, token: token || null };

  const res = await fetch(`${getBaseUrl()}/execute_v3`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (!res.ok) {
    document.getElementById("stderr").textContent = data.error || data.detail || "Error";
    document.getElementById("stdout").textContent = "";
    return;
  }

  watchProgress(data.requestId);
});

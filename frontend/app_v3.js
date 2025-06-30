function getBaseUrl() {
  const url = document.getElementById("apiUrl").value.trim();
  return url || "http://localhost:8000";
}

function displayGradedResults(data) {
  const lines = data.results.map((r) => {
    const status = r.passed ? "PASS" : "FAIL";
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
}

document.getElementById("run").addEventListener("click", async () => {
  const lang = document.getElementById("lang").value;
  const code = document.getElementById("code").value;
  const problemId = document.getElementById("problemId").value.trim();
  const token = document.getElementById("token").value.trim();

  document.getElementById("stdout").textContent = "실행 중...";
  document.getElementById("stderr").textContent = "";
  document.getElementById("judgeMessage").textContent = "";

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

  displayGradedResults(data);
});

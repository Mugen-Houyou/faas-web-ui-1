/*
실행 방법:

단순 정적 파일이므로 `frontend/` 디렉터리를 브라우저로 열거나, `python -m http.server` 등을 이용해 서빙하세요.
Python 백엔드가 먼저 실행되어 있어야 합니다.
*/


document.getElementById("run").addEventListener("click", async () => {
  const lang = document.getElementById("lang").value;
  const code = document.getElementById("code").value;

  document.getElementById("stdout").textContent = "실행 중...";
  document.getElementById("stderr").textContent = "";
  document.getElementById("time").textContent = "";

  try {
    const res = await fetch("http://localhost:8000/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: lang, code, timeout: 5.0 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Unknown error");

    document.getElementById("stdout").textContent = data.stdout;
    document.getElementById("stderr").textContent = data.stderr;
    document.getElementById("time").textContent = `실행 시간: ${data.exec_time.toFixed(3)} 초`;
  } catch (err) {
    document.getElementById("stderr").textContent = err.message;
  }
});

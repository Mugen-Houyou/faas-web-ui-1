/*
실행 방법:

단순 정적 파일이므로 `frontend/` 디렉터리를 브라우저로 열거나 `python -m http.server` 등으로 제공하면 됩니다.
AWS Lambda로 배포된 컴파일 API 엔드포인트를 입력해야 합니다.
*/


document.getElementById("run").addEventListener("click", async () => {
  const endpoint = document.getElementById("endpoint").value;
  const lang = document.getElementById("lang").value;
  const code = document.getElementById("code").value;
  const input = document.getElementById("input").value;

  document.getElementById("stdout").textContent = "실행 중...";
  document.getElementById("stderr").textContent = "";
  document.getElementById("time").textContent = "";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language: lang, input })
    });
    const data = await res.json();

    if (data.success) {
      document.getElementById("stdout").textContent = data.output;
      document.getElementById("stderr").textContent = data.error || "";
      document.getElementById("time").textContent = `실행 시간: ${data.execution_time.toFixed(3)} 초`;
    } else {
      document.getElementById("stdout").textContent = "";
      document.getElementById("stderr").textContent = data.compilation_error || "Unknown error";
    }
  } catch (err) {
    document.getElementById("stdout").textContent = "";
    document.getElementById("stderr").textContent = err.message;
  }
});

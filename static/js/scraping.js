  document.addEventListener("DOMContentLoaded", function() {
    function checkTaskStatus(taskId) {
      fetch(`/check_task_status/${taskId}/`)
        .then(response => response.json())
        .then(data => {
          const bar = document.getElementById("progress-bar");
          document.getElementById("status").innerText = `タスクID: ${taskId}`;
          document.getElementById("stop-btn").disabled = false;
          if (data.status === "SUCCESS") {
            bar.style.width = "100%";
            bar.textContent = "完了しました";
            setTimeout(() => location.reload(), 1500);
          } else if (data.status === "FAILURE") {
            bar.style.width = "100%";
            bar.classList.add("bg-danger");
            bar.textContent = "エラー発生";
          } else if (data.status === "PROGRESS") {
            const percent = Math.round((data.result.current / data.result.total) * 100);
            bar.style.width = percent + "%";
            bar.textContent = data.result.message || `${percent}% 完了`;
            setTimeout(() => checkTaskStatus(taskId), 1000);
          } else {
            // ステータスが PENDING の場合など
            bar.style.width = "10%";
            bar.textContent = "キュー待機中...";
            setTimeout(() => checkTaskStatus(taskId), 1000);
          }
        });
    }

    checkTaskStatus("{{ task_id }}");
  });

// 停止ボタン押下時
document.getElementById("stop-btn").addEventListener("click", function() {
  if (!currentTaskId) return;

  fetch(`/stop_task/${currentTaskId}/`)
    .then(response => response.json())
    .then(data => {
      document.getElementById("status").innerText = data.message;
      document.getElementById("stop-btn").disabled = true;
    });
});
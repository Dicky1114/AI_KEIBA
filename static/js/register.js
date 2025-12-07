// DOMが完全に読み込まれた後に実行される
document.addEventListener('DOMContentLoaded', function () {
    // successメッセージが存在する場合
    if (document.getElementById('success-message')) {
        // アラートを表示
        alert("Registration successful!"); // メッセージを英語に変更

        // アラートを閉じた後にログイン画面にリダイレクト
        window.location.href = '/app_folder/login'; // ログインページのURLにリダイレクト
    }
});

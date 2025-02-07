document.addEventListener('DOMContentLoaded', function () {
    const sendVerificationEmailBtn = document.getElementById('sendVerificationEmailBtn');
    const passwordSection = document.getElementById('passwordSection');
    const resultMessage = document.getElementById('resultMessage');
    const currentPasswordBtn = document.getElementById('verifyCurrentPasswordBtn');
    const newPasswordBtn = document.getElementById('verifyNewPasswordBtn');

    let isVerified = false; // 用來追踪是否完成信箱驗證
    let countdownTimer; // 倒數計時器

    // 顯示加載動畫的函數
    function showLoading() {
        resultMessage.innerHTML = `<div class="spinner-border text-primary" role="status">
                                      <span class="visually-hidden">Loading...</span>
                                   </div>`;
    }

    // 停止加載動畫，顯示最終結果
    function hideLoading() {
        resultMessage.innerHTML = ''; // 清空加載動畫
    }

    // 顯示通知的函數
    function showNotification(message, type) {
        resultMessage.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    }

    // 顯示/隱藏密碼修改部分
    function togglePasswordSection() {
        passwordSection.style.display = isVerified ? 'block' : 'none';
    }

    togglePasswordSection(); // 初始化

    // 倒數計時函數
    function startCountdown(duration, display) {
        let timer = duration, minutes, seconds;
        countdownTimer = setInterval(function () {
            minutes = parseInt(timer / 60, 10);
            seconds = parseInt(timer % 60, 10);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            display.textContent = `請於 ${minutes}:${seconds} 內完成驗證`;

            if (--timer < 0) {
                clearInterval(countdownTimer);
                showNotification('驗證超時，請重新發送驗證信。', 'danger');
            }
        }, 1000);
    }

    // 寄送驗證信並等待用戶驗證
    sendVerificationEmailBtn.addEventListener('click', function () {
        showLoading();

        // 假設向後端發送請求發送驗證信
        fetch('/send-verification-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: document.getElementById('bound_email').value })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showNotification('驗證信已寄出，請檢查您的信箱並完成驗證。', 'success');
                
                // 開始倒數計時 10 分鐘 (600 秒)
                const display = document.getElementById('countdown');
                startCountdown(600, display); // 600 秒倒數計時
                
                // 模擬用戶驗證後的行為（驗證信成功後啟用後續部分）
                setTimeout(() => {
                    isVerified = true; // 標記為已驗證
                    passwordSection.style.display = 'block'; // 顯示修改密碼的部分
                }, 2000); // 模擬延遲
            } else {
                showNotification(data.message || '發送驗證信失敗，請稍後再試。', 'danger');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            showNotification('發生錯誤，請稍後再試。', 'danger');
        });
    });

    // 驗證當前密碼
    currentPasswordBtn.addEventListener('click', function () {
        const currentPassword = document.getElementById('current_password').value;

        // 驗證密碼格式是否正確
        if (!currentPassword) {
            showNotification('請輸入當前密碼。', 'danger');
            return;
        }

        // 顯示加載動畫
        showLoading();

        // 發送當前密碼到後端進行驗證
        fetch('/verify-current-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ current_password: currentPassword })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showNotification('當前密碼驗證成功。', 'success');
            } else {
                showNotification('當前密碼錯誤。', 'danger');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            showNotification('發生錯誤，請稍後再試。', 'danger');
        });
    });

    // 驗證新密碼並發送到後端更新
    newPasswordBtn.addEventListener('click', function () {
        const newPassword = document.getElementById('new_password').value;

        // 驗證新密碼格式
        if (!newPassword) {
            showNotification('請輸入新密碼。', 'danger');
            return;
        }

        // 顯示加載動畫
        showLoading();

        // 發送新密碼到後端更新資料庫
        fetch('/update-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_password: newPassword })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showNotification('密碼已成功更改，請重新登入。', 'success');
                // 顯示登出提示或直接登出
                setTimeout(() => {
                    window.location.href = '/logout';
                }, 3000);
            } else {
                showNotification('更改密碼失敗，請稍後再試。', 'danger');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            showNotification('發生錯誤，請稍後再試。', 'danger');
        });
    });
});
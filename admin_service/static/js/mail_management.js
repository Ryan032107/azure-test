document.addEventListener('DOMContentLoaded', function () {
    const emailForm = document.getElementById('emailForm');
    const resultMessage = document.getElementById('resultMessage');
    const loadingSpinner = document.getElementById('loading');
    let countdownInterval;

    emailForm.addEventListener('submit', function (event) {
        event.preventDefault();  // 防止表單的默認提交行為

        // 判斷是綁定還是刪除信箱
        const newEmail = document.getElementById('new_email') ? document.getElementById('new_email').value : null;
        const oldEmail = document.getElementById('old_email') ? document.getElementById('old_email').value : null;

        if (newEmail) {
            // 綁定信箱邏輯
            if (!validateEmail(newEmail)) {
                showNotification('請輸入有效的信箱格式。', 'danger');
                return;
            }

            // 顯示加載動畫並開始倒數
            loadingSpinner.style.display = 'flex';
            startCountdown(10);  // 開始倒數10分鐘

            // 發送綁定信箱請求
            fetch('/mail-management', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()  // 如果使用 CSRF 保護，添加這行
                },
                body: JSON.stringify({ new_email: newEmail })
            })
            .then(response => response.json())
            .then(data => {
                loadingSpinner.style.display = 'none';
                if (data.success) {
                    showNotification('驗證信已成功發送，請檢查您的信箱。', 'success');
                } else {
                    showNotification(data.message || '發生錯誤，請稍後再試。', 'danger');
                }
            })
            .catch(error => {
                loadingSpinner.style.display = 'none';
                console.error('Error:', error);
                showNotification('發生錯誤，請稍後再試。', 'danger');
            });
        } else if (oldEmail) {
            // 刪除信箱邏輯
            showNotification('正在刪除信箱，請稍候...', 'info');
            loadingSpinner.style.display = 'flex';

            fetch('/delete-mail', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()  // 如果使用 CSRF 保護，添加這行
                },
                body: JSON.stringify({ old_email: oldEmail })
            })
            .then(response => response.json())
            .then(data => {
                loadingSpinner.style.display = 'none';
                if (data.success) {
                    showNotification('信箱已成功刪除，頁面即將刷新以重新綁定信箱。', 'success');
                    setTimeout(() => {
                        location.reload();  // 刷新頁面
                    }, 3000);  // 3秒後刷新頁面
                } else {
                    showNotification(data.message || '刪除信箱失敗，請稍後再試。', 'danger');
                }
            })
            .catch(error => {
                loadingSpinner.style.display = 'none';
                console.error('Error:', error);
                showNotification('發生錯誤，請稍後再試。', 'danger');
            });
        }
    });

    // 驗證 email 格式的函數
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    // 顯示通知的函數
    function showNotification(message, type) {
        const notificationHTML = `<div class="alert alert-${type}">${message}</div>`;
        resultMessage.innerHTML = notificationHTML;
    }

    // 倒數計時函數
    function startCountdown(minutes) {
        const countdownElement = document.createElement('div');
        countdownElement.className = 'alert alert-warning';
        resultMessage.appendChild(countdownElement);

        let remainingTime = minutes * 60;  // 將分鐘轉換為秒數

        countdownInterval = setInterval(() => {
            const minutesLeft = Math.floor(remainingTime / 60);
            const secondsLeft = remainingTime % 60;

            countdownElement.innerHTML = `請在 ${minutesLeft} 分 ${secondsLeft} 秒內完成驗證，否則會失效。`;

            if (remainingTime <= 0) {
                clearInterval(countdownInterval);
                countdownElement.innerHTML = '驗證時間已過期，請重新發送驗證信。';
            }

            remainingTime--;
        }, 1000);  // 每秒更新一次
    }

    // CSRF Token 獲取函數（如果使用 Flask-WTF CSRF 保護，確保 CSRF token 正確傳遞）
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
});
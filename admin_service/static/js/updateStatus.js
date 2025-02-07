// updateStatus.js
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function checkUpdateStatus() {
    function fetchUpdateStatus() {
        $.ajax({
            url: '/api/get_update_result',  // 获取更新状态的 API
            type: 'GET',
            success: function(response) {
                var status = response.update_status;  // 获取返回的状态

                if (status === 'updating') {
                    showLoading();
                } else if (status === 'completed') {
                    clearInterval(interval);
                    hideLoading();
                    alert('模型更新完成！');
                } else if (status === 'failed') {
                    clearInterval(interval);
                    hideLoading();
                    alert('更新出現問題! 請儘速聯繫管理員！');
                } else if (status === 'pending') {
                    clearInterval(interval);
                    hideLoading();
                }
            },
            error: function() {
                clearInterval(interval);
                alert('無法檢查更新狀態，請儘速聯繫管理員！！');
            }
        });
    }

    // 首次立即执行
    fetchUpdateStatus();

    // 然后每五秒执行一次
    var interval = setInterval(fetchUpdateStatus, 6000);
}
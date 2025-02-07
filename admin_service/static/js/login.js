$(document).ready(function() {
    $('#login_req').on('click', function(event) {
        event.preventDefault();
        var username = $('#username').val();
        var password = $('#password').val();
        $.ajax({
            type: 'POST',
            url: '/login',
            contentType: 'application/json',
            data: JSON.stringify({username: username, password: password}),
            success: function(response) {
                if (response.status === 'success') {
                    window.location.href = '/';
                } else {
                    alert('登入失敗，請再試一次。');
                }
            },
            error: function() {
                alert('登入失敗，請再試一次。');
            }
        });
    });
});
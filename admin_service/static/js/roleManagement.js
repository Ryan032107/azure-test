$(document).ready(function() {
    // Select all checkboxes with the class 'edit-permission'
    $('.edit-permission').on('click', function() {
        // 'this' refers to the checkbox that was clicked
        var isChecked = $(this).is(':checked');
        var checkboxName = $(this).attr('name');  

        // Send a POST request to the "/api/update_user_permissions" endpoint
        $.ajax({
            url: '/api/update_user_permissions',
            type: 'POST',
            data: {
                name: checkboxName,
                checked: isChecked
            },
            success: function(response) {
                console.log('Successfully updated user permissions');
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log('Failed to update user permissions: ' + errorThrown);
            }
        });
    });
});

// 新增 管理者 的函式
$(document).ready(function() {
    $('#addUserForm').on('submit', function(event) {
        event.preventDefault(); // Prevent the form from submitting the traditional way

        var form = $(this);
        var formData = form.serialize();

        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: formData,
            success: function(response) {
                if (response.status === 'success') {
                    // Show success message
                    alert(response.message);
                    form[0].reset(); // Optionally reset the form fields
                } else {
                    // Show error message
                    alert(response.message);
                }
            },            
            error: function(xhr, status, error) {
                alert('An error occurred. Please try again.');
            }
        });
    });
});

// 刪除 管理者 的函式
$(document).ready(function() {
    $('.admin-delete-button').on('click', function() {
        var userId = $(this).data('id');
        
        $.ajax({
            url: '/delete_admin/' + userId,
            type: 'POST',
            success: function(response) {
                if (response.status === 'success') {
                    alert(response.message);  // 顯示成功消息
                    $('button[data-id="' + userId + '"]').closest('tr').remove();  // 刪除行
                } else {
                    alert(response.message);  // 顯示錯誤消息
                }
            },
            error: function(xhr, status, error) {
                alert('刪除操作失敗。請重試。');
            }
        });
    });
});

function saveNote(userId, noteValue) {
    // Check if the note content has changed
    var oldContent = $("#note-" + userId).data('original-value');
    if (noteValue === oldContent) {
        console.log('Note content has not changed for user:', userId);
        return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/save_note',
            type: 'POST',
            data: JSON.stringify({
                user_id: userId,
                new_note: noteValue
            }),
            contentType: 'application/json',
            success: function(response) {
                console.log(`備註內容已成功儲存: ${response}`);
                $("#note-" + userId).data('original-value', noteValue);
                resolve(response);
            },
            error: function(error) {
                console.log(`儲存備註內容時發生錯誤: ${error}`);
                reject(error);
            }
        });
    });
}

$(document).ready(function(){
    // Store original values
    $(".edit_note").each(function() {
        $(this).data('original-value', $(this).val());
    });

    // Single save button click event
    $(".save_note").on('click', function(e) {
        e.preventDefault();
        var userId = $(this).data('user-id');
        var noteContent = $("#note-" + userId).val();
        
        saveNote(userId, noteContent).then(function() {
            alert('設定儲存成功');
        }).catch(function(error) {
            alert('設定儲存失敗: ' + error);
            console.error('設定儲存失敗:', error);
        });
    });

    // Save all notes button click event
    $("#notes_save_all").on('click', function(e){
        e.preventDefault();
        var savePromises = $(".edit_note").map(function(){
            var userId = $(this).attr('id').split('-')[1];
            var noteContent = $(this).val();
            return saveNote(userId, noteContent);
        }).get();

        Promise.all(savePromises).then(function() {
            alert('全部設定儲存成功');
        }).catch(function(error) {
            alert('全部設定儲存失敗');
            console.error('Error saving all settings:', error);
        });
    });
});

// 刪除 使用者 的函式
$(document).ready(function() {
    $('.user-delete-button').on('click', function() {
        var userId = $(this).data('id');
        
        $.ajax({
            url: '/delete_user/' + userId,
            type: 'POST',
            success: function(response) {
                if (response.status === 'success') {
                    alert(response.message);  // 顯示成功消息
                    $('button[data-id="' + userId + '"]').closest('tr').remove();  // 刪除行
                } else {
                    alert(response.message);  // 顯示錯誤消息
                }
            },
            error: function(xhr, status, error) {
                alert('刪除操作失敗。請重試。');
            }
        });
    });
});

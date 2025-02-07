function showLoading() {
  document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
  document.getElementById('loading').style.display = 'none';
}

$(document).ready(function() {
    $("#update_all").click(function() {
      // Show a confirm dialog before the upload
      if (!confirm('已經儲存所有更新了嗎? 已儲存請按確認!')) {
        return;  // If the user clicked "Cancel", stop here
      }
      showLoading();

      // 發送請求時包含特定消息
      $.ajax({
        url: '/api/update_model',
        type: 'POST',
        contentType: 'application/json',
        success: function(response){
            checkUpdateStatus(); // 開始檢查更新狀態
        },
        error: function(jqXHR){
          hideLoading();
          let errorMessage = '無法開始更新，請再試一次！';
          if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
              errorMessage = jqXHR.responseJSON.message;
          }
          alert(errorMessage);
        }
      });
    });
});

// 下方是用來檢查 collection_name 跟 prompt 表單是否被更新的函式
$(document).ready(function(){
  $(".settingsForm").on('input', function(){
      $(this).data('changed', true);
  });
});

// 下方是用來儲存 collection_name 跟 prompt 表單的函式，當表單資料有變動時，將會透過 AJAX POST 請求將資料傳送至後端
function saveForm(form) {
    var oldCollectionName = form.find('[name="oldCollectionName"]').val();
    var collectionId = form.find('[name="collectionId"]').val();
    var newCollectionName = form.find('[name="collectionName"]').val();
    var newPrompt = form.find('[name="prompt"]').val();
    // console.log(collectionId, newCollectionName, newPrompt)

    // Check if the form values is valid
    if (!newCollectionName.trim()) {
        return Promise.reject(`${oldCollectionName} 名稱為空，請輸入名稱。`);
    }
    if (!newPrompt.trim()) {
        return Promise.reject(`${oldCollectionName} 提示詞為空，請輸入提示詞。`);
    }

    // Check if the form values have changed
    if (!form.data('changed')) {
      // The form values have not changed, so resolve the promise immediately
      console.log('Form values have not changed');
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/settings',
            type: 'POST',
            data: {
                collection_id: collectionId,
                collection_name: newCollectionName,
                prompt: newPrompt
            },
            success: function(response){
                // Update the collection name in the legend
                form.closest('fieldset').find('[name="collection_display"]').text(newCollectionName);
                // 測試直接 reload 能否解決檔案無法陳列問題
                // location.reload();
                console.log(response)
                resolve(response);
            },
            error: function(error){
                console.log(error)
                reject(error);
            }
        });
    });
}

$(document).ready(function(){
    $(".settingsForm").each(function(){
        var form = $(this);
        form.on('submit', function(e) {
            e.preventDefault();
            saveForm(form).then(function() {
                alert('設定儲存成功');
            }).catch(function(error) {
                alert(error);  
                console.error('設定儲存失敗:', error);
            });
        });
    });

    $("#save_all").on('click', function(e){
        e.preventDefault();
        var savePromises = $(".settingsForm").map(function(){
            var form = $(this);
            return saveForm(form);
        }).get();
        Promise.all(savePromises).then(function() {
            alert('全部設定儲存成功');
        }).catch(function(error) {
          alert(error);  
          alert('全部設定儲存失敗');
          console.error('Error saving all settings:', error);
        });
    });
});

// 下方是用來上傳檔案的函式，可上傳多個檔案，並且將檔案資訊存入資料庫
// 將會使用 for 迴圈遍歷上傳至 GCS(GCS目前不支援一次上傳多檔案)
$(document).ready(function(){
  // Handle file upload on submit
  $('form[action^="/upload/"]').on('submit', function(e){
    e.preventDefault();

    // Show a confirm dialog before the upload
    if (!confirm('請在上傳文件之前「Save」您的設定變更。\n否則，未儲存的資料將會遺失。繼續？')) {
        return;  // If the user clicked "Cancel", stop here
    }

    var form = $(this);
    // Extract collection_id from the form action attribute
    var action = form.attr('action');
    var collectionId = action.split('/').pop(); // Assumes collection_id is the last part of the action URL

    // var formData = new FormData(form[0]);
    // Create a new FormData object to only include the files being uploaded in this submission
    
    // Create a new FormData object to only include the files being uploaded in this submission
    var formData = new FormData();

    // Get the files from the input
    var files = form.find('input[type="file"]')[0].files;
    
    // Add the files to the new FormData object
    for (var i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    console.log([...formData.entries()]); // This will log the form data entries, including the files

    // acceptable format: pdf, txt, docx, pptx, xlsx
    var allowedExtensions = ['pdf', 'txt', 'docx', 'pptx', 'xlsx']; // Allowed file types
    var hasInvalidFiles = false;

    // Iterate over all files in the FormData object
    for (var i = 0; i < form[0].elements.file.files.length; i++) {
      var file = form[0].elements.file.files[i];
      var fileExtension = file.name.split('.').pop().toLowerCase();

      if (!allowedExtensions.includes(fileExtension)) {
        alert('無效的資料格式: ' + file.name + '. \n僅可上傳 pdf, txt, docx, pptx, xlsx 格式的檔案！');
        hasInvalidFiles = true;
        break;  // Stop checking further files once an invalid file is found
      }
    }

    if (hasInvalidFiles) {
      // Clear the file input field
      form.find('input[type="file"]').val('');
      return; // Stop the form submission
    }

    // Show the loading animation
    $('#loading-' + collectionId).show(); // Use jQuery to show the loading element

    $.ajax({
      url: form.attr('action'),
      type: 'POST',
      data: formData,
      processData: false,  // tell jQuery not to process the data
      contentType: false,  // tell jQuery not to set contentType 
      success: function(response){
        console.log(response);
        $('#loading-' + collectionId).hide(); // Use jQuery to hide the loading element
        location.reload();
      },
      error: function(error){
        console.log(error);
        $('#loading-' + collectionId).hide(); // Use jQuery to hide the loading element
      }
    });
  });
});

// 下方是用來刪除檔案的函式
$(document).ready(function() {
  // Handle delete form submission
  $('form[action^="/delete/"]').on('submit', function(e) {
    e.preventDefault();

    var form = $(this);
    var action = form.attr('action');
    var collectionId = action.split('/')[2]; // Assumes collection_id is the last part of the action URL
    // Show the loading animation
    $('#loading-' + collectionId).show(); // Use jQuery to show the loading element

    $.ajax({
      url: action,
      type: 'POST',
      success: function(response) {
        // Remove the corresponding row from the table
        form.closest('tr').remove();
        console.log(response);
        $('#loading-' + collectionId).hide(); // Use jQuery to hide the loading element
      },
      error: function(error) {
        console.log(error);
        $('#loading-' + collectionId).hide(); // Use jQuery to hide the loading element
      }
    });
  });
});


// 下載檔案的函式
$(document).ready(function() {
  $('form[action^="/download/"]').on('submit', function(e) {
    e.preventDefault();
    var form = $(this);
    var action = form.attr('action');
    var collectionId = action.split('/')[2];

    $('#loading-' + collectionId).show();

    fetch(action)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');

            // 從 Content-Disposition 頭中獲取文件名
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'download';
            if (contentDisposition) {
                const filenameRegex = /filename\*=UTF-8''([\w%.-]+)/;
                const matches = filenameRegex.exec(contentDisposition);
                if (matches != null && matches[1]) {
                    filename = decodeURIComponent(matches[1]);
                }
            }

            return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => console.error('Error:', error))
        .finally(() => {
            $('#loading-' + collectionId).hide();
        });
  });
});

// 顯示GCS檔案使用量(GB)並檢查是否超過限制
$(document).ready(function() {
  var bucket_size_api = '/api/bucket_size';
  $.getJSON(bucket_size_api, function(data) {
      var usedSize = parseFloat(data.used_size).toFixed(2);
      var limitSize = parseFloat(data.limit_size).toFixed(2);
      $('#total_size').text(usedSize + ' GB / ' + limitSize + ' GB');

      // 檢查如果超過限制
      if (parseFloat(data.used_size) > parseFloat(data.limit_size)) {
          alert('警告: 已超過 GCS 使用容量限制！請清理空間或升級配額。');
          // 在這裡添加更多處理邏輯，如禁用上傳按鈕等
          $('#upload_button').prop('disabled', true); // 禁用上傳按鈕，假設它的ID為upload_button
      }
  }).fail(function() {
      $('#total_size').text('Error');
  });
});

// 顯示上次模型更新時間
$(document).ready(function() {
  function updateModelTime() {
      var update_time_api = '/api/get_update_time'; // 使用新的 API 端点
      $.getJSON(update_time_api, function(data) {
          var updateTime = new Date(data.update_time);
          var formattedTime = updateTime.toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
          $('#update_time').text(formattedTime);
      }).fail(function() {
          $('#update_time').text('Error');
      });
  }

  // 初次加载时立即执行一次
  updateModelTime();

  // 每分钟执行一次
  setInterval(updateModelTime, 60000); // 60000 毫秒 = 1 分钟
});
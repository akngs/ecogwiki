/*global gapi */
var gdrive = (function($) {
    "use strict";

    var GAPI_CLIENT_ID = $('#oauth2_web_client_id').val();
    var GAPI_SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ];

    var gdrive = {};

    gdrive.main = function() {
        registerEventHandlers();
    };

    gdrive.gapiLoaded = function() {
        gapi.auth.authorize(
            {'client_id': GAPI_CLIENT_ID, 'scope': GAPI_SCOPES.join(' '), 'immediate': true},
            handleAuthResult
        );
    };

    function handleAuthResult(result) {
        if(result) {
            $('#file').attr('disabled', false);
        } else {
            gapi.auth.authorize(
                {'client_id': GAPI_CLIENT_ID, 'scope': GAPI_SCOPES.join(' '), 'immediate': false},
                handleAuthResult
            );
        }
    }

    function registerEventHandlers() {
        $('#fileUploadLink').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            $('#file').click();
        }).on('dragenter', function(e) {
            e.stopPropagation();
            e.preventDefault();

            $(this).addClass('dragover');
        }).on('dragleave', function(e) {
            e.stopPropagation();
            e.preventDefault();

            $(this).removeClass('dragover');
        }).on('drop', function(e) {
            e.stopPropagation();
            e.preventDefault();

            var files = e.originalEvent.dataTransfer.files;
            uploadFiles(files, function() {
                console.log('Done');
            });
        });

        $('#file').on('change', function() {
            var file = this.files[0];
            uploadFiles(file, function() {
                console.log('Done');
            });
        });
    }

    function uploadFiles(files, callback) {
        var boundary = '-------314159265358979323846';
        var delimiter = '\r\n--' + boundary + '\r\n';
        var close_delim = '\r\n--' + boundary + '--';

        var fileData = files[0];
        var reader = new FileReader();
        reader.readAsBinaryString(fileData);
        reader.onload = function(e) {
            var contentType = fileData.type || 'application/octet-stream';
            var metadata = {
                'title': (fileData.name || fileData.fileName),
                'mimeType': contentType
            };
            var base64Data = btoa(reader.result);
            var multipartRequestBody =
                delimiter +
                'Content-Type: application/json\r\n\r\n' +
                JSON.stringify(metadata) +
                delimiter +
                'Content-Type: ' + contentType + '\r\n' +
                'Content-Transfer-Encoding: base64\r\n' +
                '\r\n' +
                base64Data +
                close_delim;
            var request = gapi.client.request({
                'path': '/upload/drive/v2/files',
                'method': 'POST',
                'params': {'uploadType': 'multipart'},
                'headers': {
                    'Content-Type': 'multipart/mixed; boundary="' + boundary + '"'
                },
                'body': multipartRequestBody
            });
            request.execute(callback);
        };
    }

    return gdrive;
})($);

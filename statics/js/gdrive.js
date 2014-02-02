/*global gapi */
var gdrive = (function($) {
    "use strict";

    if($('#google_oauth2_web_client_id').length === 0) return;

    var USERNAME = $('.user-email').text().split('@')[0];
    var GAPI_CLIENT_ID = $('#google_oauth2_web_client_id').val();
    var GAPI_FOLDER = $('#google_drive_folder').val().replace(/\{username\}/, USERNAME);
    var GAPI_SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.readonly.metadata',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ];
    var GAPI_FOLDER_ID = null;

    var gdrive = {};

    gdrive.main = function(editor) {
        this._editor = editor;
        registerEventHandlers();
    };

    gdrive.addFileLinkToContent = function(url, mimeType) {
        var embeddable = [
            'image/jpg',
            'image/jpeg',
            'image/png',
            'image/gif'
        ];
        if(embeddable.indexOf(mimeType) === -1) {
            this._editor.appendContent(url);
        } else {
            this._editor.appendContent('![Image](' + url + ')');
        }
    };

    gdrive.gapiLoaded = function() {
        gapi.auth.authorize(
            {'client_id': GAPI_CLIENT_ID, 'scope': GAPI_SCOPES.join(' '), 'immediate': true},
            handleAuthResult
        );
    };

    function handleAuthResult(result) {
        if(result) {
            prepareUploadFolder(GAPI_FOLDER, function(folderId) {
                GAPI_FOLDER_ID = folderId;
                $('#fileUploadLink').removeClass('disabled');
                $('#file').attr('disabled', false);
            });
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

            if($(this).hasClass('disabled')) return;

            $('#file').click();
        });

        $('#file').on('change', function() {
            uploadFile(GAPI_FOLDER_ID, this.files[0], function(resp) {
                var mimeType = resp['mimeType'];
                var url = resp['webContentLink'];
                gdrive.addFileLinkToContent(url, mimeType);
            });
        });
    }

    function prepareUploadFolder(path, callback) {
        recursivelyCreateFolder(null, path.split('/'), callback);
    }

    function recursivelyCreateFolder(parentId, pathTokens, callback) {
        if(pathTokens.length === 0) {
            callback(parentId);
            return;
        }

        var head = pathTokens.shift();
        findFolder(head, parentId, function(folders) {
            if(folders.length) {
                recursivelyCreateFolder(folders[0].id, pathTokens, callback);
            } else {
                createPublicFolder(head, parentId, function(folder) {
                    recursivelyCreateFolder(folder.id, pathTokens, callback);
                });
            }
        });
    }

    function findFolder(folderName, parentId, callback) {
        var q = "trashed=false and mimeType = 'application/vnd.google-apps.folder' and title='" + folderName + "'";
        if(parentId) {
            q += " and '" + parentId + "' in parents";
        }

        var request = gapi.client.drive.files.list({
            maxResults: 1,
            q: q
        });
        request.execute(function(resp) {
            callback(resp.items || []);
        });
    }

    function createPublicFolder(folderName, parentId, callback) {
        var body = {
            'title': folderName,
            'mimeType': 'application/vnd.google-apps.folder'
        };
        if(parentId) {
            body['parents'] = [{'id': parentId}];
        }

        var request = gapi.client.drive.files.insert({
            'resource': body
        });

        request.execute(function(folder) {
            var permissionBody = {
                'value': '',
                'type': 'anyone',
                'role': 'reader'
            };
            var permissionRequest = gapi.client.drive.permissions.insert({
                'fileId': folder.id,
                'resource': permissionBody
            });
            permissionRequest.execute(function() {
                callback(folder);
            });
        });
    }

    function uploadFile(folderId, file, callback) {
        $('#fileUploadLink').addClass('disabled');

        var boundary = '-------314159265358979323846';
        var delimiter = '\r\n--' + boundary + '\r\n';
        var close_delim = '\r\n--' + boundary + '--';
        var reader = new FileReader();
        reader.readAsBinaryString(file);
        reader.onload = function(e) {
            var contentType = file.type || 'application/octet-stream';
            var metadata = {
                'title': (file.name || file.fileName),
                'mimeType': contentType,
                'parents': [{'id': folderId}]
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
            request.execute(function(resp) {
                $('#fileUploadLink').removeClass('disabled');
                callback(resp);
            });
        };
    }

    return gdrive;
})($);

var upload = (function($) {
    "use strict";

    var Uploader = Class.extend({
        init: function() {},
        prepareUpload: function() {},
        performUpload: function() {}
    });

    var GDriveUploader = Uploader.extend({
        init: function(gapi, oauthClientId, gdriveFolder, listener) {
            this._api = gapi;
            this._oauthClientId = oauthClientId;
            this._gdriveFolder = gdriveFolder;
            this._listener = listener;

            this._apiScopes = [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.readonly.metadata',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ];
            this._folderId = null;
        },
        prepareUpload: function() {
            this._api.auth.authorize(
                {'client_id': this._oauthClientId, 'scope': this._apiScopes.join(' '), 'immediate': true},
                this._prepareUploadCallback.bind(this)
            );
        },
        performUpload: function(file) {
            var boundary = '-------314159265358979323846';
            var delimiter = '\r\n--' + boundary + '\r\n';
            var close_delim = '\r\n--' + boundary + '--';
            var reader = new FileReader();
            var self = this;
            reader.readAsBinaryString(file);
            reader.onload = function(e) {
                var contentType = file.type || 'application/octet-stream';
                var metadata = {
                    'title': (file.name || file.fileName),
                    'mimeType': contentType,
                    'parents': [{'id': self._folderId}]
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
                var request = self._api.client.request({
                    'path': '/upload/drive/v2/files',
                    'method': 'POST',
                    'params': {'uploadType': 'multipart'},
                    'headers': {
                        'Content-Type': 'multipart/mixed; boundary="' + boundary + '"'
                    },
                    'body': multipartRequestBody
                });
                request.execute(function(resp) {
                    var mimeType = resp['mimeType'];
                    var url = resp['webContentLink'];
                    self._listener.onUploaded(url, mimeType);
                });
            };
        },
        _prepareUploadCallback: function(result) {
            // Try again if fail
            if(!result) {
                this._api.auth.authorize(
                    {'client_id': this._oauthClientId, 'scope': this._apiScopes.join(' '), 'immediate': false},
                    this._prepareUploadCallback.bind(this)
                );
                return;
            }

            // Recursively create upload folder if success
            this._recursivelyCreateFolder(null, this._gdriveFolder.split('/'), this._prepareUploadFolderCallback.bind(this));
        },
        _recursivelyCreateFolder: function(parentId, pathTokens, callback) {
            if(pathTokens.length === 0) {
                callback(parentId);
                return;
            }

            var head = pathTokens.shift();
            var self = this;
            this._findFolder(head, parentId, function(folders) {
                if(folders.length) {
                    self._recursivelyCreateFolder(folders[0].id, pathTokens, callback);
                } else {
                    self._createPublicFolder(head, parentId, function(folder) {
                        self._recursivelyCreateFolder(folder.id, pathTokens, callback);
                    });
                }
            });
        },
        _prepareUploadFolderCallback: function(folderId) {
            this._folderId = folderId;
            this._listener.onUploadPrepared();
        },
        _findFolder: function(folderName, parentId, callback) {
            var q = "trashed=false and mimeType = 'application/vnd.google-apps.folder' and title='" + folderName + "'";
            if(parentId) {
                q += " and '" + parentId + "' in parents";
            }
            var request = this._api.client.drive.files.list({
                maxResults: 1,
                q: q
            });
            request.execute(function(resp) {
                callback(resp.items || []);
            });
        },
        _createPublicFolder: function(folderName, parentId, callback) {
            var body = {
                'title': folderName,
                'mimeType': 'application/vnd.google-apps.folder'
            };
            if(parentId) {
                body['parents'] = [{'id': parentId}];
            }

            var request = this._api.client.drive.files.insert({
                'resource': body
            });

            var self = this;
            request.execute(function(folder) {
                var permissionBody = {
                    'value': '',
                    'type': 'anyone',
                    'role': 'reader'
                };
                var permissionRequest = self._api.client.drive.permissions.insert({
                    'fileId': folder.id,
                    'resource': permissionBody
                });
                permissionRequest.execute(function() {
                    callback(folder);
                });
            });
        }
    });

    return {
        'Uploader': Uploader,
        'GDriveUploader': GDriveUploader
    };
})($);

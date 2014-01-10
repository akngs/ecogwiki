var editor = (function($) {
    "use strict";

    var editor = {};

    editor.main = function() {
        initPlainEditor();
        initStructuredEditor();
        registerEventHandlers();
    };

    editor.updateFormValues = function() {};

    editor.parseBody = function(body) {
        var bodyAndMd = this.extractMetadata(body, ['schema']);

        var result = {
            'itemtype': bodyAndMd['metadata']['schema'] || 'Article',
            'properties': [],
            'body': bodyAndMd['body']
        }
        return result;
    };

    editor.extractMetadata = function(body, keys) {
        var metadata = {};

        var lines = body.split('\n');
        for(var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if(line.indexOf('.') !== 0) break;
            for(var j = 0; j < keys.length; j++) {
                if(line.indexOf('.' + keys[j]) === 0) {
                    // save metadata
                    var sep = line.indexOf(' ');
                    if(sep === -1) {
                        metadata[line.substring(1)] = true;
                    } else {
                        metadata[line.substring(1, sep)] = line.substring(sep + 1).trim();
                    }

                    // remove this line
                    lines.splice(i, 1);
                    i--;
                    break;
                }
            }
        }

        return {
            'body': lines.join('\n').trim(),
            'metadata': metadata
        };
    }

    function initPlainEditor() {
        if(window['CodeMirror']) {
            // Enable CodeMirror editor
            var cm = CodeMirror.fromTextArea(document.querySelector('textarea'), {
                indentUnit: 4,
                indentWithTabs: false,
                lineWrapping: true,
                lineNumbers: true,
                autofocus: true,
                mode: 'markdown',
                viewportMargin: Infinity
            });
            cm.addKeyMap({
                'Cmd-Enter': function() {$('input.comment').focus();},
                'Ctrl-Enter': function() {$('input.comment').focus();}
            });

            editor.updateFormValues = function() {
                $('.editform').find('textarea[name="body"]').val(cm.getValue());
            };
        } else {
            var $textarea = $('.editform textarea');
            if ($textarea.length === 0) return;

            $(resizeEditor);
            $(window).resize(resizeEditor);
            $(window).on('orientationchange', resizeEditor);
            $textarea.on('input propertychange', resizeEditor);
        }
    }

    function resizeEditor() {
        // It doesn't work when there's large amount of reduction in text
        var $textarea = $('.editform textarea');
        $textarea.height($textarea.height() - 50);
        $textarea.height($textarea.prop('scrollHeight'));
    }

    function initStructuredEditor() {
        $('.editor-tab').append('<li class="tab struct" data-name="struct"><a href="#struct">Structured editor</a></li>');
        $('.editor-content').append('<li class="content struct" data-name="struct">...</li>');
    }

    function registerEventHandlers() {
        /* Editor tab switch */
        $('.editor-tab').on('click', '.tab > a', function(e) {
            var $this = $(this);
            // do nothing if it's already active
            if($this.parent().hasClass('active')) {
                e.preventDefault();
                return;
            }

            // make it active
            $('.editor-tab .tab.active').removeClass('active');
            $('.editor-content .content.active').removeClass('active');

            $this.parent().addClass('active');
            var name = $this.parent().data('name');
            $('.editor-content .content.' + name).addClass('active');
        });

        /* Delete */
        $('.btn-delete').on('click', function() {
            if(!window.confirm('Are you sure?')) return false;

            $.post($('.deleteform').attr('action'), {}, function() {
                window.location = window.location.pathname;
            });

            return false;
        });

        /* Preview */
        $('.btn-preview').on('click', function() {
            $('.preview').show();

            var $form = $('.editform');
            $form.find('input[name="preview"]').val('1');
            editor.updateFormValues();
            var formdata = $form.serialize();
            $form.find('input[name="preview"]').val(0);

            $.post('?_method=PUT', formdata, function(data) {
                var html = $('<div>').append(jQuery.parseHTML(data)).find('.wrap').html();
                $('.preview .body').html(html);
            });
        });
    }

    return editor;
})($);

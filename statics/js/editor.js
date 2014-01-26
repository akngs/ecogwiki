var editor = (function($) {
    "use strict";

    var editor = {};

    editor.main = function() {
        initPlainEditor();
        initStructuredEditor();
        registerEventHandlers();
    };

    editor.updateFormValues = function() {};
    editor.getContent = function() {};
    editor.updateFormValues = function() {};
    editor.appendContent = function(content) {};

    editor.parseBody = function(body) {
        // parse yaml/schema block
        var dataAndBody = this.extractYaml(body);
        var data = dataAndBody['data'];
        var bodyWithoutYamlBlock = dataAndBody['body'];

        // extract out schema metadata
        var schema = 'Article';
        var lines = bodyWithoutYamlBlock.split('\n');
        for(var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if(line.indexOf('.schema ') !== 0) break;

            // save metadata
            var sep = line.indexOf(' ');
            if(sep === -1) {
                schema = 'Article';
            } else {
                schema = line.substring(sep + 1).trim();
            }

            // remove this line
            lines.splice(i, 1);
            i--;
        }

        return {
            'body': lines.join('\n').trim(),
            'itemtype': schema,
            'data': data
        };
    }

    editor.extractYaml = function(body) {
        var p_yaml = /(?:\s{4}|\t)#!yaml\/schema[\n\r]+(((?:\s{4}|\t).+[\n\r]+?)+)/;
        var m = body.match(p_yaml);
        if(m) {
            return {
                'data': jsyaml.load((m[0])) || {},
                'body': body.replace(p_yaml, '')
            };
        } else {
            return {
                'data': {},
                'body': body
            };
        }
    }

    editor.generateBody = function(data) {
        var lines = [];

        // .schema
        if(data['itemtype'] != 'Article') {
            lines.push('.schema ' + data['itemtype']);
        }
        // other metadatas
        var bodylines = data['body'].split('\n');
        while(bodylines[0].indexOf('.') == 0) {
            lines.push(bodylines.splice(0, 1));
        }

        // empty line
        if(lines.length > 0) {
            lines.push('');
        }

        // yaml/schema block
        if(!$.isEmptyObject(data['data'])) {
            var dump = jsyaml.dump(data['data']).trim().split('\n');

            lines.push('    #!yaml/schema');
            dump.forEach(function(i) {
                lines.push('    ' + i);
            });
        }

        // empty line
        if(lines.length > 0 && lines[lines.length - 1] !== '') {
            lines.push('');
        }

        // remove starting empty lines in body
        while(bodylines[0] === '') {
            bodylines.splice(0, 1);
        }

        // rest
        bodylines.forEach(function(i) {
            lines.push(i);
        });

        return lines.join('\n');
    };

    editor.generateForm = function(types, schema) {
        var result = [];

        result.push('<form>');

        // render item types
        result.push('<select id="sed_type">');
        for(var i = 0; i < types.length; i++) {
            result.push('<option>' + types[i] + '</option>');
        }
        result.push('</select>');

        // render form fields
        var props = schema['properties'];
        for(var prop in props) {
            if(props[prop]['cardinality'][0] > 0) {
                result.push('<label for="prop_' + prop + '">' + props[prop]['type']['label'] + '</label>');
                result.push('<input type="text" id="prop_' + prop + '" name="prop_' + prop + '" value="">');
            }
        }

        result.push('</form>');
        return result.join('\n');
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

            editor.getContent = function() {
                return cm.getValue();
            };
            editor.updateFormValues = function() {
                var content = this.getContent();
                $('.editform').find('textarea[name="body"]').val(content);
            };

            editor.appendContent = function(content) {
                cm.setValue(this.getContent() + '\n\n' + content);
            };
        } else {
            var $textarea = $('.editform textarea');
            if ($textarea.length === 0) return;

            $(resizeEditor);
            $(window).resize(resizeEditor);
            $(window).on('orientationchange', resizeEditor);
            $textarea.on('input propertychange', resizeEditor);

            editor.getContent = function() {
                return $textarea.val();
            };
            editor.appendContent = function(content) {
                $textarea.val(this.getContent() + '\n\n' + content);
            };
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
        $('.editor-content').append('<li class="content struct" data-name="struct"></li>');
    }

    function renderStructuredEditor() {
        var $sed = $('.editor-content .struct');
        var content = editor.getContent();
        var parsed = editor.parseBody(content);

        $sed.addClass('initializing');
        $.get('/sp.schema/types?_type=json', function(json) {
            var types = json['values'];
            var curType = parsed['itemtype'];

            $.get('/sp.schema/sctypes/' + curType + '?_type=json', function(schema) {
                $sed.removeClass('initializing');
                $sed.html(editor.generateForm(types, schema));
                updateStructuredEditor();
            });
        });
    }

    function updateStructuredEditor() {
        var content = editor.getContent();
        var parsed = editor.parseBody(content);
        $('#sed_type').val(parsed['itemtype']);
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

            if(name === 'struct') {
                renderStructuredEditor();
            }
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

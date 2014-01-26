var editor2 = (function($) {
    "use strict";

    var Editor = Class.extend({
        init: function(textarea) {
            var _this = this;

            this._textarea = textarea;
            $(this._textarea.form).on('submit', function() {
                $(_this._textarea).val(_this.getContent());
            });

            // Hide underlaying textarea
            $(this._textarea).hide();

            // Create root div
            this._$root = $('<div class="ecogwiki-editor"></div>');
            this._$root.insertAfter(this._textarea);

            // Create tabs
            this._$root.append(
                '<ul class="mode-tab">' +
                '<li class="plain active" data-name="plain"><a href="#">Plain</a></li>' +
                '<li class="structured" data-name="structured"><a href="#">Structured</a></li>' +
                '</ul>'
            );
            this._$root.find('.mode-tab > li > a').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                _this.setActiveModeName($(this).parent().data('name'));
            });

            // Create content panes
            this._$root.append(
                '<ul class="mode-pane">' +
                '<li class="plain"></li>' +
                '<li class="structured" style="display: none;"></li>' +
                '</ul>'
            );

            this._plainEditMode = new PlainEditMode(this._$root.find('.mode-pane .plain')[0], $(this._textarea).val());
            this._structEditMode = new StructuredEditMode(this._$root.find('.mode-pane .structured')[0], $(this._textarea).val());
        },
        setActiveModeName: function(newMode) {
            // If not changed, do nothing
            var $oldTab = this._$root.find('.mode-tab > li.active');
            if($oldTab.data('name') === newMode) return;

            // Deactive old mode
            var oldMode = this._$root.find('.mode-tab > li.active').data('name');
            $oldTab.removeClass('active');
            this._$root.find('.mode-pane > li.' + oldMode).hide();

            // Activate new mode
            this._$root.find('.mode-tab > li.' + newMode).addClass('active');
            this._$root.find('.mode-pane > li.' + newMode).show();
        },
        getActiveModeName: function() {
            return this._$root.find('.mode-tab > li.active').data('name');
        },
        getActiveMode: function() {
            return this.getActiveModeName() === 'plain' ? this._plainEditMode : this._structEditMode;
        },
        setContent: function(content) {
            this.getActiveMode().setContent(content);
        },
        updateTextarea: function() {
            $(this._textarea).val(this.getContent());
        },
        getContent: function() {
            return this.getActiveMode().getContent();
        },
        appendContent: function(content) {
            this.getActiveMode().appendContent(content);
        }
    });


    var EditMode = Class.extend({
        getContent: function() {},
        setContent: function(content) {},
        appendContent: function(content) {}
    });


    var PlainEditMode = EditMode.extend({
        init: function(rootEl, content) {
            this._rootEl = rootEl;

            var $textarea = $('<textarea></textarea>')
                .appendTo(this._rootEl);
            this._editlet = TextEditlet.createInstance($textarea[0]);
            this._editlet.setContent(content);
        },
        getEditlet: function() {
            return this._editlet;
        },
        getContent: function() {
            return this._editlet.getContent();
        },
        setContent: function(content) {
            this._editlet.setContent(content);
        },
        appendContent: function(content) {
            this._editlet.appendContent(content);
        }
    });


    var StructuredEditMode = EditMode.extend({
    });


    var ContentParser = Class.extend({
        parseBody: function(body) {
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
        },
        generateBody: function(data) {
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
        },
        extractYaml: function(body) {
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
    });


    var TextEditlet = Class.extend({
        init: function(textarea) {
            this._textarea = textarea;
        },
        setContent: function(content) {},
        getContent: function() {},
        appendContent: function(content) {
            this.setContent(this.getContent() + '\n\n' + content);
        }
    });
    TextEditlet.createInstance = function(textarea) {
        if(window['CodeMirror']) {
            return new CodeMirrorTextEditlet(textarea);
        } else {
            return new SimpleTextEditlet(textarea);
        }
    };


    var SimpleTextEditlet = TextEditlet.extend({
        init: function(textarea) {
            this._super(textarea);

            this.resizeToAutofit();

            var resizeToAutofit = this.resizeToAutofit.bind(this);
            $(window).resize(resizeToAutofit);
            $(window).on('orientationchange', resizeToAutofit);
            $(this._textarea).on('input propertychange', resizeToAutofit);
        },
        setContent: function(content) {
            $(this._textarea).val(content);
        },
        getContent: function() {
            return $(this._textarea).val();
        },
        resizeToAutofit: function() {
            // It doesn't work when there's large amount of reduction in text
            var $textarea = $(this._textarea);
            $textarea.height($textarea.height() - 50);
            $textarea.height($textarea.prop('scrollHeight'));
        }
    });


    var CodeMirrorTextEditlet = TextEditlet.extend({
        init: function(textarea) {
            this._super(textarea);

            if(!window['CodeMirror']) throw "CodeMirror not found";

            this._cm = CodeMirror.fromTextArea(textarea, {
                indentUnit: 4,
                indentWithTabs: false,
                lineWrapping: true,
                lineNumbers: true,
                autofocus: true,
                mode: 'markdown',
                viewportMargin: Infinity
            });

            var getNextFocusTarget = this.getNextFocusTarget.bind(this);
            this._cm.addKeyMap({
                'Cmd-Enter': function() {getNextFocusTarget().focus();},
                'Ctrl-Enter': function() {getNextFocusTarget().focus();}
            });
        },
        getContent: function() {
            return this._cm.getValue();
        },
        setContent: function(content) {
            this._cm.setValue(content);
            this._cm.refresh();
            $(this._textarea).val(this.getContent());
        },
        getNextFocusTarget: function() {
            var form = this._textarea.form;
            var candidates = form.querySelectorAll('input, button, textarea, select');
            // find index of textarea;
            for(var i = 0; i < candidates.length; i++) {
                if(candidates[i] == this._textarea) break;
            }
            // skip controls generated by CodeMirror
            for(var j = i + 1; j < candidates.length; j++) {
                if($(candidates[j]).parents('.CodeMirror').length === 0) break;
            }
            return candidates[j === candidates.length ? 0 : j];
        }
    });


    return {
        Editor: Editor,

        EditMode: EditMode,
        PlainEditMode: PlainEditMode,
        StructuredEditMode: StructuredEditMode,

        ContentParser: ContentParser,

        TextEditlet: TextEditlet,
        SimpleTextEditlet: SimpleTextEditlet,
        CodeMirrorTextEditlet: CodeMirrorTextEditlet
    };
})($);

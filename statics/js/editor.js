var editor = (function($) {
    "use strict";

    var Editor = Class.extend({
        init: function(textarea, callback, typesLoader, schemaLoader) {
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
                '<li class="plain" data-name="plain"><a href="#">Plain</a></li>' +
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

            this._plainEditMode = new PlainEditMode(this._$root.find('.mode-pane .plain')[0]);
            this._structEditMode = new StructuredEditMode(this._$root.find('.mode-pane .structured')[0], typesLoader, schemaLoader);
            this.setActiveModeName('plain', callback);
        },
        setActiveModeName: function(newMode, callback) {
            // If not changed, do nothing
            var $oldTab = this._$root.find('.mode-tab > li.active');
            if($oldTab.data('name') === newMode) return;

            // Deactive old mode
            if($oldTab.length) {
                this.updateTextarea();

                var oldMode = this._$root.find('.mode-tab > li.active').data('name');
                $oldTab.removeClass('active');
                this._$root.find('.mode-pane > li.' + oldMode).hide();
            }

            // Activate new mode
            this._$root.find('.mode-tab > li.' + newMode).addClass('active');
            this._$root.find('.mode-pane > li.' + newMode).show();
            this.setContent($(this._textarea).val(), callback);
        },
        getActiveModeName: function() {
            return this._$root.find('.mode-tab > li.active').data('name');
        },
        getActiveMode: function() {
            return this.getActiveModeName() === 'plain' ? this._plainEditMode : this._structEditMode;
        },
        setContent: function(content, callback) {
            this.getActiveMode().setContent(content, callback);
        },
        updateTextarea: function() {
            $(this._textarea).val(this.getContent());
        },
        getContent: function() {
            return this.getActiveMode().getContent();
        },
        appendContent: function(content, callback) {
            this.getActiveMode().appendContent(content, callback);
        }
    });


    var EditMode = Class.extend({
        getContent: function() {},
        setContent: function(content, callback) {},
        appendContent: function(content, callback) {}
    });


    var PlainEditMode = EditMode.extend({
        init: function(rootEl) {
            this._rootEl = rootEl;

            var $textarea = $('<textarea></textarea>')
                .appendTo(this._rootEl);
            this._editlet = TextEditlet.createInstance($textarea[0]);
        },
        getEditlet: function() {
            return this._editlet;
        },
        getContent: function() {
            return this._editlet.getContent();
        },
        setContent: function(content, callback) {
            this._editlet.setContent(content);
            if(callback) callback();
        },
        appendContent: function(content, callback) {
            this._editlet.appendContent(content);
            if(callback) callback();
        }
    });


    var StructuredEditMode = EditMode.extend({
        init: function(rootEl, typesLoader, schemaLoader) {
            this._rootEl = rootEl;
            this._parser = new ContentParser();
            this._types = [];
            this._schema = {};
            this._wikibodyEditlet = null;
            this._typesLoader = typesLoader;
            this._schemaLoader = schemaLoader;
        },
        setContent: function(content, callback) {
            var self = this;

            // load types
            if(this._types.length === 0) {
                this._typesLoader(function(types) {
                    self._types = types;
                    self.setContent(content, callback);
                });
                return;
            }

            // load schema
            var parsed = this._parser.parseBody(content);
            var itemtype = parsed['itemtype'];
            var schema = this._schema[itemtype];
            if(schema === undefined) {
                this._schemaLoader(itemtype, function(schema) {
                    self._schema[itemtype] = schema || {'properties': {}};
                    self.setContent(content, callback);
                });
                return;
            }

            // populate fields
            var $root = $(this._rootEl);
            $root.html('');

            this._populateItemtypeSelector($root, parsed['itemtype']);

            var props = schema['properties'];
            var data = parsed['data'];
            var pnames = union([props, data]);
            for(var i = 0; i < pnames.length; i++) {
                var pname = pnames[i];
                this._populateField(pname, $root, props[pname], data[pname]);
            }

            this._populateBodyField($root, parsed['body']);
        },
        appendContent: function(content, callback) {
        },
        getContent: function() {
            var parsed = this._gatherData($(this._rootEl));
            return this._parser.generateBody(parsed);
        },
        _populateField: function(pname, $container, prop, values) {
            // Use default property if prop == undefined
            if(prop === undefined) {
                prop = {
                    "type": {
                        "label": pname,
                        "comment": pname,
                        "comment_plain": pname,
                        "domains": [],
                        "ranges": ["Text"],
                        "id": pname
                    },
                    "cardinality": [0, 0]
                };
            }

            // Make values array
            if(values && !$.isArray(values)) {
                values = [values];
            } else if(!values) {
                values = [];
            }

            // Filter out empty value
            values = values.filter(function(v) {return v !== '';});

            // Decide number of fields to populate
            var numOfFields = Math.max(prop['cardinality'][0], values.length);
            if(numOfFields === 0) return;

            // Generate fields
            var idPrefix = 'prop_' + prop['type']['id'];
            var sb = [];
            sb.push('<div class="prop prop-' + prop['type']['id'] + '" data-pname="' + prop['type']['id'] + '">');
            sb.push('   <label for="' + idPrefix + '_0">' + prop['type']['label'] + '</label>');
            sb.push('   <ol>');

            for(var i = 0; i < numOfFields; i++) {
                sb.push('       <li><input class="field" type="text" id="' + idPrefix + '_' + i + '" name="' + prop['type']['id'] + '" value="' + encodeHtmlEntity(values[i] || '') + '"></li>');
            }
            sb.push('   </ol>');
            sb.push('</div>');
            $container.append(sb.join('\n'));
        },
        _populateItemtypeSelector: function($container, itemtype) {
            var self = this;
            var sb = [];
            sb.push('<div class="prop prop-itemtype" data-pname="itemtype">');
            sb.push('   <label for="prop_itemtype">Item type</label>');
            sb.push('   <select class="field" id="prop_itemtype" name="prop_itemtype">');
            for(var i = 0; i < this._types.length; i++) {
                if(this._types[i] === itemtype) {
                    sb.push('      <option selected="selected" value="' + this._types[i] + '">' + this._types[i] + '</option>');
                } else {
                    sb.push('      <option value="' + this._types[i] + '">' + this._types[i] + '</option>');
                }
            }
            sb.push('   </select>');
            sb.push('</div>');
            $container.append(sb.join('\n'));

            $container.find('#prop_itemtype').on('change', function() {
                self.setContent(self.getContent());
            });
        },
        _populateBodyField: function($container, body) {
            var sb = [];
            sb.push('<div class="prop prop-wikibody" data-pname="wikibody">');
            sb.push('   <label for="prop_wikibody">Body</label>');
            sb.push('   <textarea class="field" id="prop_wikibody" name="prop_wikibody">' + encodeHtmlEntity(body) + '</textarea>');
            sb.push('</div>');
            $container.append(sb.join('\n'));

            this._wikibodyEditlet = TextEditlet.createInstance($container.find('#prop_wikibody')[0]);
        },
        _gatherData: function($container) {
            var result = {
                itemtype: '',
                data: {},
                body: ''
            };

            result['itemtype'] = $container.find('#prop_itemtype').val();

            var $props = $container.find('.prop');
            for(var i = 0; i < $props.length; i++) {
                var $prop = $($props[i]);
                var pname = $prop.data('pname');
                if(['itemtype', 'wikibody'].indexOf(pname) !== -1) continue;

                var $fields = $prop.find('li .field');
                var values = [];
                for(var j = 0; j < $fields.length; j++) {
                    var $field = $($fields[j]);
                    var value = $field.val();
                    if(value !== '') values.push(value);
                }
                if(values.length) {
                    result['data'][pname] = values.length === 1 ? values[0] : values;
                }
            }

            result['body'] = this._wikibodyEditlet.getContent();

            return result;
        }
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

    function encodeHtmlEntity(value) {
        return value.replace(/</g, '&lt;');
    }

    function union(arrayOfArray) {
        var result = [];
        for(var i = 0; i < arrayOfArray.length; i++) {
            var array = arrayOfArray[i];
            if($.isArray(array)) {
                for(var j = 0; j < array.length; j++) {
                    var value = array[j];
                    if(result.indexOf(value) !== -1) continue;
                    result.push(value);
                }
            } else {
                for(var key in array) {
                    if(result.indexOf(key) !== -1) continue;
                    result.push(key);
                }
            }
        }
        return result;
    }

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

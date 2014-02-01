var editor = (function($) {
    "use strict";

    var Editor = Class.extend({
        init: function(textarea, callback, typesLoader, schemaLoader) {
            var self = this;

            this._textarea = textarea;
            $(this._textarea.form).on('submit', function() {
                $(self._textarea).val(self.getContent());
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

                if(self._$root.hasClass('busy')) return;

                self.setActiveModeName($(this).parent().data('name'));
            });

            // Create content panes
            this._$root.append(
                '<ul class="mode-pane">' +
                '<li class="plain"></li>' +
                '<li class="structured" style="display: none;"></li>' +
                '</ul>'
            );

            this._plainEditMode = new PlainEditMode(this._$root.find('.mode-pane .plain')[0]);
            this._structEditMode = new StructuredEditMode(this._$root.find('.mode-pane .structured')[0], typesLoader, schemaLoader, this);
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
        },

        // StructuredEditMode callbacks
        onStartLoadTypes: function(mode) {
            this._$root.addClass('busy');
            this._$root.addClass('busy-loading-types');
        },
        onEndLoadTypes: function(mode) {
            this._$root.removeClass('busy');
            this._$root.removeClass('busy-loading-types');
        },
        onStartLoadSchema: function(mode) {
            this._$root.addClass('busy');
            this._$root.addClass('busy-loading-schema');
        },
        onEndLoadSchema: function(mode) {
            this._$root.removeClass('busy');
            this._$root.removeClass('busy-loading-schema');
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
        init: function(rootEl, typesLoader, schemaLoader, callback) {
            this._rootEl = rootEl;
            this._parser = new ContentParser();
            this._types = [];
            this._schema = {};
            this._wikibodyEditlet = null;
            this._typesLoader = typesLoader;
            this._schemaLoader = schemaLoader;
            this._callback = callback;

            $(this._rootEl).on('click', '.add-prop', this._onAddProp.bind(this));
            $(this._rootEl).on('click', '.add-field', this._onAddField.bind(this));
            $(this._rootEl).on('click', '.delete-field', this._onDeleteField.bind(this));
        },
        setContent: function(content, callback) {
            var self = this;

            // load types
            if(this._types.length === 0) {
                $(self._rootEl).find(':input').prop('disabled', true);
                if(this._callback.onStartLoadTypes) this._callback.onStartLoadTypes(this);

                this._typesLoader(function(types) {
                    self._types = types;
                    self.setContent(content, callback);

                    $(self._rootEl).find(':input').prop('disabled', false);
                    if(self._callback.onEndLoadTypes) self._callback.onEndLoadTypes(this);
                });
                return;
            }

            // load schema
            var parsed = this._parser.parseBody(content);
            var itemtype = parsed['itemtype'];
            var schema = this._schema[itemtype];
            if(schema === undefined) {
                $(self._rootEl).find(':input').prop('disabled', true);
                if(this._callback.onStartLoadSchema) this._callback.onStartLoadSchema(this);

                this._schemaLoader(itemtype, function(schema) {
                    self._schema[itemtype] = schema || {'properties': {}};
                    self.setContent(content, callback);

                    $(self._rootEl).find(':input').prop('disabled', false);
                    if(self._callback.onEndLoadSchema) self._callback.onEndLoadSchema(this);
                });
                return;
            }

            // populate fields
            var $root = $(this._rootEl);
            $root.html('');

            // 1. Itemtype selector
            this._populateItemtypeSelector(parsed['itemtype']);

            // 2. Properties
            var props = schema['properties'];
            var data = parsed['data'];
            var pnames = union([props, data]);

            for(var i = 0; i < pnames.length; i++) {
                var pname = pnames[i];
                this._populateProp(itemtype, pname, data[pname]);
            }

            // 3. Property selector
            this._populatePropertySelector(parsed['itemtype']);

            // 4. Wikibody
            this._populateBodyField(parsed['body']);
        },
        appendContent: function(content, callback) {
        },
        getContent: function() {
            var parsed = this._gatherData();
            return this._parser.generateBody(parsed);
        },
        _populateProp: function(itemtype, pname, values, forceAdd) {
            var $root = $(this._rootEl);

            // Create property container if there is not
            var $propList = $root.find('.props');
            if($propList.length === 0) {
                $propList = $('<ol class="props"></ol>');
                $root.append($propList);
            }

            // Do not create property if there already is
            if($propList.find('.prop-' + pname).length !== 0) return;

            var prop = this._getProperty(itemtype, pname);

            // Make values array
            if(values !== undefined && !$.isArray(values)) {
                values = [values];
            } else if(values === undefined) {
                values = [];
            }

            // Filter out empty value
            values = values.filter(function(v) {return v !== '';});

            // Decide number of fields to populate
            var numOfFields = Math.max(prop['cardinality'][0], values.length);
            if(forceAdd && numOfFields === 0) numOfFields = 1;

            if(numOfFields === 0) return;

            // Generate fields
            var idPrefix = 'prop_' + prop['type']['id'];
            var sb = [];
            sb.push('<div class="prop prop-' + prop['type']['id'] + '" data-pname="' + prop['type']['id'] + '">');
            sb.push('   <label for="' + idPrefix + '_0">' + prop['type']['label'] + '</label>');
            sb.push('   <ol></ol>');
            sb.push('   <a class="add-field" href="#">Add field</a>');
            sb.push('</div>');
            $propList.append(sb.join('\n'));

            for(var i = 0; i < numOfFields; i++) {
                this._addField(itemtype, pname, encodeHtmlEntity(values[i] || ''));
            }

            this._updateButtonsVisibility(itemtype, pname);
        },
        _populateItemtypeSelector: function(itemtype) {
            var self = this;
            var $root = $(this._rootEl);
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
            $root.append(sb.join('\n'));

            // repopulate fields if itemtype changes
            $root.find('#prop_itemtype').on('change', function() {
                self.setContent(self.getContent());
            });
        },
        _populatePropertySelector: function(itemtype) {
            var props = this._schema[itemtype]['properties'];
            var $root = $(this._rootEl);
            var sb = [];
            sb.push('<div class="prop prop-property" data-pname="property">');
            sb.push('    <label for="prop_property">Available properties</label>');
            sb.push('    <select class="field" id="prop_property" name="prop_property">');

            for(var pname in props) {
                sb.push('        <option value="' + pname + '">' + props[pname]['type']['label'] + '</option>');
            }
            sb.push('    </select>');
            sb.push('    <a class="add-prop" href="#">Add</a>');
            sb.push('</div>');
            $root.append(sb.join('\n'));
        },
        _populateBodyField: function(body) {
            var sb = [];
            var $root = $(this._rootEl);
            sb.push('<div class="prop prop-wikibody" data-pname="wikibody">');
            sb.push('   <label for="prop_wikibody">Body</label>');
            sb.push('   <textarea class="field" id="prop_wikibody" name="prop_wikibody">' + encodeHtmlEntity(body) + '</textarea>');
            sb.push('</div>');
            $root.append(sb.join('\n'));

            this._wikibodyEditlet = TextEditlet.createInstance($root.find('#prop_wikibody')[0]);
        },
        _gatherData: function() {
            var result = {
                itemtype: '',
                data: {},
                body: ''
            };
            var $root = $(this._rootEl);

            result['itemtype'] = $root.find('#prop_itemtype').val();

            var $props = $root.find('.prop');
            for(var i = 0; i < $props.length; i++) {
                var $prop = $($props[i]);
                var pname = $prop.data('pname');
                if(['itemtype', 'wikibody', 'property'].indexOf(pname) !== -1) continue;

                var $fields = $prop.find('li .field');
                var values = [];
                for(var j = 0; j < $fields.length; j++) {
                    var $field = $($fields[j]);
                    var value = this._parseDataValue($field);
                    if(value !== '') values.push(value);
                }
                if(values.length) {
                    result['data'][pname] = values.length === 1 ? values[0] : values;
                }
            }

            result['body'] = this._wikibodyEditlet.getContent();

            return result;
        },
        _parseDataValue: function($field) {
            var type = $field.data('type');

            if(['Number', 'Float'].indexOf(type) !== -1) {
                return +$field.val();
            } else if('Integer' === type) {
                return parseInt(+$field.val());
            } else if('Boolean' === type) {
                return $field.prop('checked');
            } else {
                return $field.val();
            }
        },
        _getProperty: function(itemtype, pname) {
            var schema = this._schema[itemtype] || {'properties': {}};
            return schema['properties'][pname] || {
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
        },
        _updateButtonsVisibility: function(itemtype, pname) {
            var $root = $(this._rootEl);
            var prop = this._getProperty(itemtype, pname);
            var numOfFields = $root.find('.prop-' + pname + ' li').length;

            var addButtonVisible =
                prop['cardinality'][1] == 0 ||
                prop['cardinality'][1] > numOfFields;
            $root.find('.prop-' + pname + ' .add-field')[addButtonVisible ? 'show' : 'hide']();

            var deleteButtonVisible =
                prop['cardinality'][0] < numOfFields;
            $root.find('.prop-' + pname + ' .delete-field')[deleteButtonVisible ? 'show' : 'hide']();
        },
        _addField: function(itemtype, pname, value) {
            var $root = $(this._rootEl);
            var $prop = $root.find('.prop-' + pname);
            var prop = this._getProperty(itemtype, pname);
            var i = $prop.find('li.fields').length;

            var sb = [];
            sb.push('<li class="fields">');
            sb.push(this._generateFieldHtml(pname, i, prop['type']['ranges'], prop['type']['enum'], value));
            sb.push('<a class="delete-field" href="#">Delete</a>');
            sb.push('</li>');
            $prop.find('ol').append(sb.join('\n'));

            return $prop.find('#prop_' + pname + '_' + i);
        },
        _generateFieldHtml: function(pname, index, ranges, enums, value) {
            // Decide type to use
            var priority = ['ISBN', 'URL', 'Date', 'DateTime', 'Time', 'Boolean', 'Integer', 'Float', 'Number', 'Text'];
            if($.isArray(ranges)) {
                for(var i = 0; i < priority.length; i++) {
                    if(ranges.indexOf(priority[i]) !== -1) return this._generateFieldHtml(pname, index, priority[i], enums, value);
                }
                return this._generateFieldHtml(pname, index, 'Text', enums, value);
            }

            // Render element according to target
            var sb = [];
            if(enums) {
                // Render <select> element for enums
                sb.push('<select class="field" data-type="' + ranges + '" id="prop_' + pname + '_' + index + '" name="' + pname + '">');
                enums.forEach(function(v) {
                    sb.push('<option value="' + v + '">' + v + '</option>');
                })
                sb.push('</select>');
            } else {
                // Render appropriate element
                if('ISBN' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="text" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if('URL' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="url" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if(['Text', 'DateTime', 'Time'].indexOf(ranges) !== -1) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="text" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if(['Number', 'Integer', 'Float'].indexOf(ranges) !== -1) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="number" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if('Boolean' === ranges) {
                    if(value) {
                        sb.push('<input class="field" data-type="' + ranges + '" type="checkbox" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="on" checked="checked">');
                    } else {
                        sb.push('<input class="field" data-type="' + ranges + '" type="checkbox" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="on">');
                    }
                } else if('Date' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="date" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else {
                    sb.push('<input class="field" data-type="' + ranges + '" type="text" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                }
            }
            return sb.join('\n');
        },
        _onAddProp: function(e) {
            e.preventDefault();
            e.stopPropagation();

            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $root.find('#prop_property').val();
            this._populateProp(itemtype, pname, [], true);

            $root.find('#prop_' + pname + '_0').focus();
        },
        _onAddField: function(e) {
            e.preventDefault();
            e.stopPropagation();

            var $prop = $(e.target).parents('.prop');
            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $prop.data('pname');

            var $addedField = this._addField(itemtype, pname, '');
            this._updateButtonsVisibility(itemtype, pname);

            $addedField.focus();
        },
        _onDeleteField: function(e) {
            e.preventDefault();
            e.stopPropagation();

            var $prop = $(e.target).parents('.prop');
            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $prop.data('pname');

            // Remove element
            $(e.target).parents('li.fields').remove();

            // Update id to fill removed index
            $prop.find('li.fields').each(function(i) {
                $(this).find('.field').attr('id', 'prop_' + pname + '_' + i);
            });

            this._updateButtonsVisibility(itemtype, pname);

            // Remove property if there's no fields
            if($prop.find('li.fields').length === 0) $prop.remove();
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
            var p_yaml = /(?:[ ]{4}|\t)#!yaml\/schema[\n\r]+(((?:[ ]{4}|\t).+[\n\r]+?)+)/;
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
            this._$textarea = $(this._textarea);
            this._needToResize = true;

            var triggerResize = this.triggerResize.bind(this);
            $(window).resize(triggerResize);
            $(window).on('orientationchange', triggerResize);
            this._$textarea.on('input', triggerResize);

            this.resizeToFit();
        },
        setContent: function(content) {
            this._$textarea.val(content);
        },
        getContent: function() {
            return this._$textarea.val();
        },
        triggerResize: function() {
            this._needToResize = true;
        },
        resizeToFit: function() {
            var resizeToFit = this.resizeToFit.bind(this);
            window.setTimeout(resizeToFit, 1000);
            if(!this._needToResize) return;

            this._$textarea.height(10);
            this._$textarea.height(this._$textarea.prop('scrollHeight') + 100);
            this._needToResize = false;
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
        return value.replace ? value.replace(/</g, '&lt;') : value;
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

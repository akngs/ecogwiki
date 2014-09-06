var editor = (function($) {
    "use strict";

    var Editor = Class.extend({
        init: function(textarea, callback, typesLoader, schemaLoader, pagename, userPage, userEmail) {
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

            var vars = {
                'thisPage': pagename || '',
                'userPage': userPage || '',
                'userEmail': userEmail || ''
            };
            vars['parentPage'] =  vars['thisPage'].substr(0, vars['thisPage'].lastIndexOf('/'));
            vars['userPage'] = vars['userPage'] || vars['userEmail'].substr(0, vars['userEmail'].indexOf('@'));

            this._plainEditMode = new PlainEditMode(this._$root.find('.mode-pane .plain')[0]);
            this._structEditMode = new StructuredEditMode(this._$root.find('.mode-pane .structured')[0], typesLoader, schemaLoader, this, vars);

            this.setActiveModeName('plain', callback);
        },
        setActiveModeName: function(newMode, callback) {
            var self = this;
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

            this.setContent($(this._textarea).val(), function() {
                self.getActiveMode().focus();
                if(callback) callback(self);
            });
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
        appendContent: function(content) {
            this.getActiveMode().appendContent(content);
        },
        setUploader: function(uploader) {
            this._uploader = uploader;
            this._$clickedLink = null;

            var self = this;
            this._uploader.setListener({
                onUploaderStateChanged: function(ready) {
                    if(ready) {
                        $('.upload-link').removeClass('disabled');
                    } else {
                        $('.upload-link').addClass('disabled');
                    }
                },
                onUploadPrepared: function() {},
                onUploaded: function(url, thumbnailUrl, mimeType) {
                    var fieldId = self._$clickedLink.data('field');
                    if(thumbnailUrl) {
                        url += '&thumbnailUrl=' + encodeURIComponent(thumbnailUrl);
                    }
                    if(fieldId) {
                        // update property
                        $('#' + fieldId).val(url);
                    } else {
                        // append to body
                        var embeddable = [
                            'image/jpg',
                            'image/jpeg',
                            'image/png',
                            'image/gif'
                        ];
                        if(embeddable.indexOf(mimeType) === -1) {
                            self.appendContent(url);
                        } else {
                            self.appendContent('![Image](' + url + ')');
                        }
                    }
                }
            });

            $(document).on('click', '.upload-link', function(e) {
                e.preventDefault();
                e.stopPropagation();

                if($(this).hasClass('disabled')) return;
                self._$clickedLink = $(this);
                $('#file').click();
            });

            $('#file').on('change', function() {
                self._uploader.performUpload(this.files[0]);
            });
        },

        // StructuredEditMode callbacks
        onStartLoadTypes: function() {
            this._$root.addClass('busy');
            this._$root.addClass('busy-loading-types');
        },
        onEndLoadTypes: function() {
            this._$root.removeClass('busy');
            this._$root.removeClass('busy-loading-types');
        },
        onStartLoadSchema: function() {
            this._$root.addClass('busy');
            this._$root.addClass('busy-loading-schema');
        },
        onEndLoadSchema: function() {
            this._$root.removeClass('busy');
            this._$root.removeClass('busy-loading-schema');
        }
    });


    var EditMode = Class.extend({
        focus: function() {},
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
        focus: function() {
            this._editlet.focus();
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
        appendContent: function(content) {
            this._editlet.appendContent(content);
        }
    });


    var StructuredEditMode = EditMode.extend({
        init: function(rootEl, typesLoader, schemaLoader, callback, variables) {
            this._rootEl = rootEl;
            this._parser = new ContentParser();
            this._types = [];
            this._schema = {};
            this._wikibodyEditlet = null;
            this._sectionEditlets = {};
            this._typesLoader = typesLoader;
            this._schemaLoader = schemaLoader;
            this._callback = callback;
            this._variables = variables || {};

            $(this._rootEl).on('click', '.add-prop', this._onAddProp.bind(this));
            $(this._rootEl).on('click', '.add-field', this._onAddField.bind(this));
            $(this._rootEl).on('click', '.delete-field', this._onDeleteField.bind(this));
        },
        focus: function() {
            this._wikibodyEditlet.focus();
        },
        setContent: function(content, callback) {
            var self = this;

            // load types
            if(this._types.length === 0) {
                $(self._rootEl).find(':input').prop('disabled', true);
                $(self._rootEl).find('a').addClass('disabled', true);
                if(this._callback.onStartLoadTypes) this._callback.onStartLoadTypes(this);

                this._typesLoader(function(types) {
                    self._types = types;

                    $(self._rootEl).find(':input').prop('disabled', false);
                    $(self._rootEl).find('a').removeClass('disabled', true);
                    if(self._callback.onEndLoadTypes) self._callback.onEndLoadTypes(this);

                    self.setContent(content, callback);
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

                    $(self._rootEl).find(':input').prop('disabled', false);
                    if(self._callback.onEndLoadSchema) self._callback.onEndLoadSchema(this);

                    self.setContent(content, callback);
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
            var sections = parsed['sections'];
            var pnames = union([props, data, sections]);

            for(var i = 0; i < pnames.length; i++) {
                var pname = pnames[i];
                var value = data[pname];

                // force type to LongText if the value is from section markup
                var forceType = undefined;
                if(sections[pname]) {
                    value = sections[pname];
                    forceType = 'LongText';
                }
                this._populateProp(itemtype, pname, value, false, forceType);
            }

            // 3. Property selector
            this._populatePropertySelector(parsed['itemtype']);

            // 4. Wikibody
            this._populateBodyField(parsed['body']);

            if(callback) callback();
        },
        appendContent: function(content) {
            this._wikibodyEditlet.appendContent(content);
        },
        getContent: function() {
            var parsed = this._gatherData();
            return this._parser.generateBody(parsed);
        },
        _populateProp: function(itemtype, pname, values, forceAdd, forceType) {
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
            sb.push('   <label for="' + idPrefix + '_0" title="' + encodeHtmlEntity(prop['type']['comment']) + '">' + prop['type']['label'] + '</label>');
            sb.push('   <ol></ol>');
            sb.push('   <a class="add-field" href="#">+ Add ' + prop['type']['label'] + '</a>');
            sb.push('</div>');
            $propList.append(sb.join('\n'));

            for(var i = 0; i < numOfFields; i++) {
                var required = i < prop['cardinality'][0];
                this._addField(itemtype, pname, encodeHtmlEntity(values[i] || ''), forceType, required);
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
                var type = this._types[i][0];
                var label = this._types[i][1];

                if(type === itemtype) {
                    sb.push('      <option selected="selected" value="' + type + '">' + label + '</option>');
                } else {
                    sb.push('      <option value="' + type + '">' + label + '</option>');
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
            sb.push('    <label for="prop_property">Additional properties</label>');
            sb.push('    <div class="field-row"><select class="field" id="prop_property" name="prop_property">');

            for(var pname in props) {
                sb.push('        <option value="' + pname + '">' + props[pname]['type']['label'] + '</option>');
            }
            sb.push('    </select></div>');
            sb.push('    <a class="add-prop" href="#">+ Add property</a>');
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
                body: '',
                sections: {}
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
                    var sectionsOrData = $fields[0].nodeName === 'TEXTAREA' ? 'sections' : 'data';
                    result[sectionsOrData][pname] = values.length === 1 ? values[0] : values;
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
            } else if('LongText' === type) {
                return this._sectionEditlets[$field.attr('id')].getContent();
            } else {
                return $field.val();
            }
        },
        _getProperty: function(itemtype, pname) {
            var schema = this._schema[itemtype] || {'properties': {}};
            var prop = schema['properties'][pname] || {
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
            prop['defaultValue'] = (schema['defaultValues'] && schema['defaultValues'][pname]) || '';

            for(var key in this._variables) {
                prop['defaultValue'] = prop['defaultValue'].replace('${' + key + '}', this._variables[key]);
            }

            return prop;
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
        _addField: function(itemtype, pname, value, forceType, required) {
            var $root = $(this._rootEl);
            var $prop = $root.find('.prop-' + pname);
            var prop = this._getProperty(itemtype, pname);
            var i = $prop.find('li.field-row').length;

            // use forced type if there is
            var type = forceType || prop['type']['ranges'];

            var sb = [];

            sb.push('<li class="field-row ' + (required ? 'required' : '') + '">');
            sb.push(this._generateFieldHtml(pname, i, type, prop['type']['enum'], value || prop['defaultValue']));
            sb.push('<a class="delete-field" href="#">&times;</a>');
            sb.push('</li>');
            $prop.find('ol').append(sb.join('\n'));

            var $field = $prop.find('#prop_' + pname + '_' + i);

            if($field.data('type') === "LongText") {
                $field.parent().addClass('field-row-longtext');
                this._sectionEditlets[$field.attr('id')] = TextEditlet.createInstance($field[0]);
            }

            return $field;
        },
        _generateFieldHtml: function(pname, index, ranges, enums, value) {
            // Decide type to use
            var priority = ['ISBN', 'EmbeddableURL', 'URL', 'Date', 'DateTime', 'Time', 'Boolean', 'Integer', 'Float', 'Number', 'LongText', 'Text'];
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
                    if(v === value) {
                        sb.push('<option value="' + v + '" selected="selected">' + v + '</option>');
                    } else {
                        sb.push('<option value="' + v + '">' + v + '</option>');
                    }
                });
                sb.push('</select>');
            } else {
                // Render appropriate element
                if('ISBN' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="text" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if('EmbeddableURL' === ranges) {
                    sb.push(
                        '<input class="field" data-type="' + ranges + '" type="url" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '"> ' +
                        '<a class="upload-link" href="#" data-field="prop_' + pname + '_' + index + '">Upload</a>'
                    );
                } else if('URL' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="url" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if('LongText' === ranges) {
                    sb.push('<textarea class="field" data-type="' + ranges + '" id="prop_' + pname + '_' + index + '" name="' + pname + '">' + value + '</textarea>');
                } else if(['Text', 'DateTime', 'Time'].indexOf(ranges) !== -1) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="text" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if('Integer' === ranges) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="number" step="1" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');
                } else if(['Number', 'Float'].indexOf(ranges) !== -1) {
                    sb.push('<input class="field" data-type="' + ranges + '" type="number" step="any" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="' + value + '">');

                } else if('Boolean' === ranges) {
                    if(value) {
                        sb.push('<input class="field" data-type="' + ranges + '" type="checkbox" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="on" checked="checked"> Yes');
                    } else {
                        sb.push('<input class="field" data-type="' + ranges + '" type="checkbox" id="prop_' + pname + '_' + index + '" name="' + pname + '" value="on"> Yes');
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
            if($(this).hasClass('disabled')) return;

            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $root.find('#prop_property').val();
            this._populateProp(itemtype, pname, [], true);

            $root.find('#prop_' + pname + '_0').focus();
        },
        _onAddField: function(e) {
            e.preventDefault();
            e.stopPropagation();
            if($(this).hasClass('disabled')) return;

            var $prop = $(e.target).parents('.prop');
            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $prop.data('pname');

            // If there is a field of this property, use type of the field
            var forceType = null;
            var $fields = $prop.find('.field');
            if($fields.length) {
                forceType = $fields.data('type');
            }

            var $addedField = this._addField(itemtype, pname, '', forceType);
            this._updateButtonsVisibility(itemtype, pname);

            $addedField.focus();
        },
        _onDeleteField: function(e) {
            e.preventDefault();
            e.stopPropagation();
            if($(this).hasClass('disabled')) return;

            var $prop = $(e.target).parents('.prop');
            var $root = $(this._rootEl);
            var itemtype = $root.find('#prop_itemtype').val();
            var pname = $prop.data('pname');

            // Remove element
            $(e.target).parents('li.field-row').remove();

            // Update id to fill removed index
            $prop.find('li.field-row').each(function(i) {
                $(this).find('.field').attr('id', 'prop_' + pname + '_' + i);
            });

            this._updateButtonsVisibility(itemtype, pname);

            // Remove property if there's no fields
            if($prop.find('li.field-row').length === 0) $prop.remove();
        }
    });


    var ContentParser = Class.extend({
        parseBody: function(body) {
            var dataAndBody = this.extractYaml(body);
            var data = dataAndBody['data'];
            var bodyWithoutYamlBlock = dataAndBody['body'];

            var lines = bodyWithoutYamlBlock.split('\n');

            var schema = this._extractOutSchema(lines);

            var sections = this._extractOutSections(lines);

            return {
                'body': lines.join('\n').trim(),
                'itemtype': schema,
                'data': data,
                'sections': sections
            };
        },
        _extractOutSchema: function(lines) {
            var schema = 'Article';
            for(var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if(line.indexOf('.schema ') !== 0) break;

                // save metadata
                var sep = line.indexOf(' ');
                if(sep !== -1) {
                    schema = line.substring(sep + 1).trim();
                }

                // remove this line
                lines.splice(i, 1);
                i--;
            }
            return schema;
        },
        _extractOutSections: function(lines) {
            var pSection = /^([^\s]+?)::---+$/;

            // skip body lines
            for(var i = 0; i < lines.length; i++) {
                if(lines[i].match(pSection)) break;
            }

            // collect sections
            var sections = {};
            var sectionName = null;
            var sectionLines = null;

            while(i < lines.length) {
                var m = lines[i].match(pSection);
                if(m) {
                    if(!sectionName) {
                        // Found first section. Start new one.
                        sectionName = m[1];
                        sectionLines = [];
                    } else {
                        // Found other section. Close current section and start new one
                        addToMultiDict(sections, sectionName, sectionLines.join('\n').trim());

                        sectionName = m[1];
                        sectionLines = [];
                    }
                } else {
                    // In section. Collect lines
                    sectionLines.push(lines[i]);
                }

                // remove this line
                lines.splice(i, 1);
            }

            if(sectionName) {
                addToMultiDict(sections, sectionName, sectionLines.join('\n').trim());
            }

            return sections;
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

            // sections
            var sections = data['sections'];
            for(var sectionName in sections) {
                var sectionValues = sections[sectionName];
                if(!$.isArray(sectionValues)) sectionValues = [sectionValues];
                sectionValues.forEach(function(value) {
                    if(!lines.length || lines[lines.length - 1] !== '') lines.push('');

                    lines.push(sectionName + '::---');
                    lines.push('');

                    lines.push(value);
                });
            }

            return lines.join('\n');
        },
        extractYaml: function(body) {
            var pYaml = /(?:[ ]{4}|\t)#!yaml\/schema[\n\r]+(((?:[ ]{4}|\t).+[\n\r]+?)+)/;
            var m = body.match(pYaml);
            if(m) {
                return {
                    'data': jsyaml.load((m[0])) || {},
                    'body': body.replace(pYaml, '')
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
        focus: function() {},
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
        focus: function() {
            this._textarea.focus();
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
                autofocus: false,
                mode: 'markdown',
                viewportMargin: Infinity
            });

            var getNextFocusTarget = this.getNextFocusTarget.bind(this);
            this._cm.addKeyMap({
                'Cmd-Enter': function() {getNextFocusTarget().focus();},
                'Ctrl-Enter': function() {getNextFocusTarget().focus();}
            });
        },
        focus: function() {
            this._cm.focus();
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
        return value.replace ? value.replace(/</g, '&lt;').replace(/"/g, '&quot;') : value;
    }

    function addToMultiDict(dict, key, value) {
        if(key in dict) {
            var cur = dict[key];
            if(!$.isArray(cur)) cur = [cur];
            cur.push(value);

            dict[key] = cur;
        } else {
            dict[key] = value;
        }
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
        'Editor': Editor,

        'EditMode': EditMode,
        'PlainEditMode': PlainEditMode,
        'StructuredEditMode': StructuredEditMode,

        'ContentParser': ContentParser,

        'TextEditlet': TextEditlet,
        'SimpleTextEditlet': SimpleTextEditlet,
        'CodeMirrorTextEditlet': CodeMirrorTextEditlet
    };
})($);

/*global describe, it, expect*/
describe('TextEditlet', function() {
    var sandbox;

    beforeEach(function() {
        sandbox = document.createElement('div');
        document.body.appendChild(sandbox);
    });

    describe('Factory', function() {
        var cm_backup;
        var textarea;

        beforeEach(function() {
            cm_backup = window['CodeMirror'];
            sandbox.innerHTML = '<form><textarea></textarea><input type="submit"></form>';
            textarea = sandbox.querySelector('textarea');
        });
        afterEach(function() {
            window['CodeMirror'] = cm_backup;
        });

        it('should create CodeMirrorEditlet if there is CodeMirror', function() {
            var editlet = editor.TextEditlet.createInstance(textarea);
            expect(editlet instanceof editor.CodeMirrorTextEditlet).toBeTruthy();
        });

        it('should create SimpleTextEditlet if there is no CodeMirror', function() {
            delete window['CodeMirror'];

            var editlet = editor.TextEditlet.createInstance(textarea);
            expect(editlet instanceof editor.SimpleTextEditlet).toBeTruthy();
        });
    });

    describe('SimpleTextEditlet', function() {
        var textarea;
        var editlet;

        beforeEach(function() {
            sandbox.innerHTML = '<form><textarea></textarea><input type="submit"></form>';
            textarea = sandbox.querySelector('textarea');
            editlet = new editor.SimpleTextEditlet(textarea);
        });

        it('should work with associated textarea', function() {
            editlet.setContent('Hello');
            expect(editlet.getContent()).toEqual('Hello');
            expect(textarea.value).toEqual('Hello');
        });

        it('should append text to current content', function() {
            editlet.setContent('Hello');
            editlet.appendContent('there?');
            expect(editlet.getContent()).toEqual('Hello\n\nthere?');
        });
    });

    describe('CodeMirrorTextEditlet', function() {
        var textarea;
        var editlet;

        beforeEach(function() {
            sandbox.innerHTML = '<form><textarea id="this"></textarea><p>Hello</p><input type="submit" id="target"></form>';
            textarea = sandbox.querySelector('textarea');
            editlet = new editor.CodeMirrorTextEditlet(textarea);
        });

        it('should work with associated textarea', function() {
            editlet.setContent('Hello');
            expect(editlet.getContent()).toEqual('Hello');
            expect(textarea.value).toEqual('Hello');
        });

        it('should append text to current content', function() {
            editlet.setContent('Hello');
            editlet.appendContent('there?');
            expect(editlet.getContent()).toEqual('Hello\n\nthere?');
        });
    });

    describe('CodeMirrorTextEditlet.getNextFocusTarget', function() {
        it('should find next form element', function() {
            sandbox.innerHTML = '<form><textarea id="this"></textarea><p>Hello</p><input type="submit" id="target"></form>';
            var textarea = sandbox.querySelector('textarea');
            var editlet = new editor.CodeMirrorTextEditlet(textarea);
            expect(editlet.getNextFocusTarget().getAttribute('id')).toEqual('target');
        });

        it('should select the first form element if the textarea is the last element', function() {
            sandbox.innerHTML = '<form><input type="text" id="target"><textarea id="this"></textarea></form>';
            var textarea = sandbox.querySelector('textarea');
            var editlet = new editor.CodeMirrorTextEditlet(textarea);
            expect(editlet.getNextFocusTarget().getAttribute('id')).toEqual('target');
        });
    });
});


describe('Editor', function() {
    var logs;
    var sandbox;
    var textarea;
    var ed;
    var $root;

    beforeEach(function() {
        logs = [];
        sandbox = document.createElement('div');
        document.body.appendChild(sandbox);

        sandbox.innerHTML = '<form><textarea></textarea></form>';
        textarea = sandbox.querySelector('textarea');
        ed = new editor.Editor(textarea, function() {
            logs.push('Editor.init() callback');
        }, function(callback) {
            callback([['Article', 'Article']]);
        }, function(itemtype, callback) {
            callback({'properties': {}});
        });
        $root = $(textarea).next();
    });

    it('should execute callback on init', function() {
        expect(logs).toEqual(['Editor.init() callback']);
    });

    it('should modify DOM', function() {
        // Attach div.ecogwiki-editor right after the original textarea
        expect($root.hasClass('ecogwiki-editor')).toBeTruthy();

        // Hide original textarea
        expect($(textarea).css('display')).toEqual('none');

        // Create tabs
        expect($root.find('ul.mode-tab > li').length).toEqual(2);
        expect($root.find('ul.mode-tab > li.active').hasClass('plain')).toBeTruthy();

        // Create content panes
        expect($root.find('ul.mode-pane > li').length).toEqual(2);
    });

    it('should start from plain mode', function() {
        expect(ed.getActiveModeName()).toEqual('plain');
    });

    it('should switch plain mode to structured modes', function() {
        $root.find('ul.mode-tab > li.structured > a').click();
        expect(ed.getActiveModeName()).toEqual('structured');
        expect(ed.getActiveMode() instanceof editor.StructuredEditMode).toBeTruthy();
        expect($root.find('ul.mode-tab > li.active').hasClass('structured')).toBeTruthy();
        expect($root.find('ul.mode-pane > li.plain').css('display')).toEqual('none');
    });

    it('should switch structured mode to plain modes', function() {
        $root.find('ul.mode-tab > li.plain > a').click();
        expect(ed.getActiveModeName()).toEqual('plain');
        expect(ed.getActiveMode() instanceof editor.PlainEditMode).toBeTruthy();
        expect($root.find('ul.mode-tab > li.active').hasClass('plain')).toBeTruthy();
        expect($root.find('ul.mode-pane > li.structured').css('display')).toEqual('none');
    });
});

describe('Edit mode', function() {
    var sandbox;

    beforeEach(function() {
        sandbox = document.createElement('div');
        document.body.appendChild(sandbox);
    });

    describe('Plain mode', function() {
        it('should create TextEditlet with given initial content', function() {
            var mode = new editor.PlainEditMode(sandbox);
            mode.setContent('Hello');
            var editlet = mode.getEditlet();
            expect(mode.getContent()).toEqual('Hello');
            expect(editlet.getContent()).toEqual('Hello');
        });

        it('should connected to TextEditlet', function() {
            var mode = new editor.PlainEditMode(sandbox);
            var editlet = mode.getEditlet();

            mode.setContent('Hello');
            expect(mode.getContent()).toEqual('Hello');
            expect(editlet.getContent()).toEqual('Hello');

            editlet.setContent('World');
            expect(mode.getContent()).toEqual('World');
            expect(editlet.getContent()).toEqual('World');
        });
    });

    describe('Structured mode', function() {
        var mode;
        var logs;
        var schema = {
            'Article': {
                "id": "Article",
                "label": "Article",
                "properties": {
                    "field1": {
                        "type": {
                            "label": "First field",
                            "comment": "First field of the article.",
                            "comment_plain": "First field of the article.",
                            "domains": ["Article"],
                            "ranges": ["Text"],
                            "id": "field1"
                        },
                        "cardinality": [1, 1]
                    },
                    "field2": {
                        "type": {
                            "label": "Second field",
                            "comment": "Second field of the article.",
                            "comment_plain": "Second field of the article.",
                            "domains": ["Article"],
                            "ranges": ["Text"],
                            "id": "field2"
                        },
                        "cardinality": [2, 3]
                    },
                    "field3": {
                        "type": {
                            "label": "Third field",
                            "comment": "Third field of the article.",
                            "comment_plain": "Third field of the article.",
                            "domains": ["Article"],
                            "ranges": ["Text"],
                            "id": "field3"
                        },
                        "cardinality": [0, 0]
                    },
                    "field4": {
                        "type": {
                            "label": "Fourth field",
                            "comment": "Fourth field of the article.",
                            "comment_plain": "Fourth field of the article.",
                            "domains": ["Article"],
                            "ranges": ["LongText"],
                            "id": "field4"
                        },
                        "cardinality": [0, 0]
                    }
                }
            },
            'Book': {
                "properties": {
                    "author": {
                        "type": {
                            "label": "Author",
                            "comment": "Author of the book.",
                            "comment_plain": "Author of the book.",
                            "domains": ["Book"],
                            "ranges": ["Text"],
                            "id": "author"
                        },
                        "cardinality": [1, 0]
                    }
                }
            },
            'Person': {
                "properties": {}
            }
        };

        beforeEach(function() {
            logs = [];
            mode = new editor.StructuredEditMode(sandbox, function(callback) {
                callback([['Article', 'Article label'], ['Book', 'Book label'], ['Person', 'Person label']]);
            }, function(itemtype, callback) {
                callback(schema[itemtype]);
            }, {
                onStartLoadTypes: function() {logs.push('onStartLoadTypes');},
                onEndLoadTypes: function() {logs.push('onEndLoadTypes');},
                onStartLoadSchema: function() {logs.push('onStartLoadSchema');},
                onEndLoadSchema: function() {logs.push('onEndLoadSchema');}
            });
            mode.setContent('', function() {});
        });

        it('should execute callbacks while loading', function() {
            expect(logs).toEqual(['onStartLoadTypes', 'onEndLoadTypes', 'onStartLoadSchema', 'onEndLoadSchema']);
        });

        it('should render itemtype selector', function() {
            var $itemtypeSelector = $(sandbox).find('#prop_itemtype');
            expect($itemtypeSelector.length).toEqual(1);
            expect($itemtypeSelector.val()).toEqual('Article');

            var $options = $itemtypeSelector.children();
            expect($options.length).toEqual(3);
            expect($($options[0]).val()).toEqual('Article');
            expect($($options[0]).text()).toEqual('Article label');
            expect($($options[1]).val()).toEqual('Book');
            expect($($options[1]).text()).toEqual('Book label');
            expect($($options[2]).val()).toEqual('Person');
            expect($($options[2]).text()).toEqual('Person label');
        });

        it('should render mandatory fields', function() {
            expect($(sandbox).find('.prop-field1').length).toEqual(1);
            expect($(sandbox).find('.prop-field2').length).toEqual(1);

            expect($(sandbox).find('#prop_field1_0').length).toEqual(1);
            expect($(sandbox).find('#prop_field2_0').length).toEqual(1);
            expect($(sandbox).find('#prop_field2_1').length).toEqual(1);
        });

        it('should render wikibody textarea', function() {
            expect($(sandbox).find('#prop_wikibody').length).toEqual(1);
        });

        it('should not render optional fields', function() {
            expect($(sandbox).find('.prop-field3').length).toEqual(0);
            expect($(sandbox).find('.prop-field4').length).toEqual(0);
        });

        it('should populate value of fields with content', function() {
            mode.setContent('    #!yaml/schema\n    field1: Hey\n    field2: ["Hello", "World"]\n    field3: ["Goodbye", "World"]\n\nHello\n\nfield4::---\n\nHey', function() {});

            expect($(sandbox).find('#prop_field1_0').val()).toEqual('Hey');
            expect($(sandbox).find('#prop_field2_0').val()).toEqual('Hello');
            expect($(sandbox).find('#prop_field2_1').val()).toEqual('World');
            expect($(sandbox).find('#prop_field3_0').val()).toEqual('Goodbye');
            expect($(sandbox).find('#prop_field3_1').val()).toEqual('World');
            expect($(sandbox).find('#prop_field4_0').val()).toEqual('Hey');
            expect($(sandbox).find('#prop_wikibody').val()).toEqual('Hello');
        });

        it('should not populate empty field', function() {
            // No values for field2 and empty value in field3
            mode.setContent('    #!yaml/schema\n    field1: Hey\n    field3: ["", "World"]\n', function() {});

            expect($(sandbox).find('#prop_field1_0').val()).toEqual('Hey');
            expect($(sandbox).find('#prop_field2_0').val()).toEqual('');
            expect($(sandbox).find('#prop_field2_1').val()).toEqual('');
            expect($(sandbox).find('#prop_field3_0').val()).toEqual('World');
        });

        it('should ignore empty field', function() {
            mode.setContent('    #!yaml/schema\n    field1: Hey\n    field2: ["Hello", "World"]\n    field3: ["Goodbye", "World"]\n', function() {});

            $(sandbox).find('#prop_field2_0').val('');
            $(sandbox).find('#prop_field2_1').val('');
            $(sandbox).find('#prop_field3_0').val('');
            $(sandbox).find('#prop_field3_1').val('World');

            expect(mode.getContent()).toEqual('    #!yaml/schema\n    field1: Hey\n    field3: World\n');
        });

        it('should populate fields for unknown values', function() {
            mode.setContent('.schema Person\n\n    #!yaml/schema\n    unknown1: Hey\n\nunknown2::---\n\nThere', function() {});
            expect($(sandbox).find('#prop_unknown1_0').val()).toEqual('Hey');
            expect($(sandbox).find('#prop_unknown2_0').val()).toEqual('There');
        });

        it('should retain unknown values', function() {
            mode.setContent('.schema Person\n\n    #!yaml/schema\n    unknown1: Hey\n\nunknown2::---\n\nThere', function() {});
            $(sandbox).find('#prop_unknown1_0').val('Hello');
            $(sandbox).find('#prop_unknown2_0').val('There');
            expect(mode.getContent()).toEqual('.schema Person\n\n    #!yaml/schema\n    unknown1: Hello\n\nunknown2::---\n\nThere');
        });

        it('should update content if fields updated', function() {
            mode.setContent('    #!yaml/schema\n    field1: "Hey"\n    field2:\n      - "Hello"\n      - "World"\n    field3:\n      - "Goodbye"\n      - "World"\n\nHello', function() {});
            $(sandbox).find('#prop_field1_0').val('Hey!');
            $(sandbox).find('#prop_field2_0').val('Hello!');
            $(sandbox).find('#prop_field2_1').val('World!');
            $(sandbox).find('#prop_field3_0').val('Goodbye!');
            $(sandbox).find('#prop_field3_1').val('World!');

            expect(mode.getContent()).toEqual('    #!yaml/schema\n    field1: "Hey!"\n    field2:\n      - "Hello!"\n      - "World!"\n    field3:\n      - "Goodbye!"\n      - "World!"\n\nHello');
        });

        it('should populate itemtype according to .schema', function() {
            mode.setContent('.schema Book', function() {});
            expect($(sandbox).find('#prop_itemtype').val()).toEqual('Book');
        });

        it('should update content if itemtype updated', function() {
            mode.setContent('.schema Book', function() {});
            $(sandbox).find('#prop_itemtype').val('Person');
            expect(mode.getContent()).toEqual('.schema Person\n');
        });

        it('should repopulate fields if itemtype updated', function() {
            mode.setContent('.schema Article', function() {});

            $(sandbox).find('#prop_itemtype').val('Book');
            // jquery doesn't automatically triggers change event
            $(sandbox).find('#prop_itemtype').trigger('change');

            expect($(sandbox).find('#prop_field1_0').length).toEqual(0);
            expect($(sandbox).find('#prop_author_0').length).toEqual(1);
        });

        it('should allow adding new field', function() {
            mode.setContent('', function() {});

            // Cardinality of field2 is [2, 3], so it should allow adding new field
            var $addField2 = $(sandbox).find('.prop-field2 .add-field:visible');
            expect($addField2.length).toEqual(1);

            // Add a feild
            $addField2.trigger('click');
            expect($(sandbox).find('#prop_field2_2').length).toEqual(1);

            // Now it should not allow adding more field
            $addField2 = $(sandbox).find('.prop-field2 .add-field:visible');
            expect($addField2.length).toEqual(0);
        });

        it('should prevent adding too much fields', function() {
            mode.setContent('', function() {});

            // cardinality of field1 is [1, 1], so it should not allow adding new field
            var $addField1 = $(sandbox).find('.prop-field1 .add-field:visible');
            expect($addField1.length).toEqual(0);
        });

        it('should allow deleting new field', function() {
            mode.setContent('    #!yaml/schema\n    field2: ["A", "B", "C"]\n', function() {});

            // cardinality of field2 is [2, 3], so it should allow deleting a field
            var $deleteField2 = $(sandbox).find('.prop-field2 .delete-field:visible');
            expect($deleteField2.length).toEqual(3);

            $($deleteField2[1]).click();
            $deleteField2 = $(sandbox).find('.prop-field2 .delete-field:visible');
            expect($deleteField2.length).toEqual(0);

            expect($(sandbox).find('#prop_field2_0').val()).toEqual("A");
            expect($(sandbox).find('#prop_field2_1').val()).toEqual("C");
            expect($(sandbox).find('#prop_field2_2').length).toEqual(0);
        });

        it('should prevent deleting too much fields', function() {
            mode.setContent('    #!yaml/schema\n    field2: ["A", "B"]\n', function() {});

            // cardinality of field1 is [2, 3], so it should not allow deleting more fields
            var $deleteField2 = $(sandbox).find('.prop-field2 .delete-field:visible');
            expect($deleteField2.length).toEqual(0);
        });

        it('should remove a property if there is no fields in it', function() {
            mode.setContent('    #!yaml/schema\n    field3: "A"\n', function() {});
            $(sandbox).find('.prop-field3 .delete-field:visible').click();

            expect($(sandbox).find('.prop-field3').length).toEqual(0);
        });

        it('should render property selector', function() {
            mode.setContent('.schema Article', function() {});
            var $propertySelector = $(sandbox).find('.prop-property');

            // Property selector
            expect($propertySelector.length).toEqual(1);

            // Add button
            expect($propertySelector.find('.add-prop').length).toEqual(1);

            // Should list all fields
            var $options = $propertySelector.find('option');
            expect($options.length).toEqual(4);
            expect($($options[0]).attr('value')).toEqual('field1');
            expect($($options[1]).attr('value')).toEqual('field2');
            expect($($options[2]).attr('value')).toEqual('field3');
            expect($($options[3]).attr('value')).toEqual('field4');
        });

        it('should allow to add new property', function() {
            mode.setContent('.schema Article', function() {});
            $(sandbox).find('#prop_property').val('field3');
            $(sandbox).find('.add-prop').click();

            expect($(sandbox).find('.prop-field3').length).toEqual(1);
            expect($(sandbox).find('#prop_field3_0').val()).toEqual('');
        });

        it('should not add property if there already is', function() {
            mode.setContent('.schema Article', function() {});
            $(sandbox).find('#prop_property').val('field3');

            // Add once...
            $(sandbox).find('.add-prop').click();
            // ...and twice
            $(sandbox).find('.add-prop').click();

            expect($(sandbox).find('.prop-field3').length).toEqual(1);
        });
    });

    describe('Structured mode data type', function() {
        var mode;
        var schema = {'Article': {"properties": {
            "url": {"cardinality": [0, 0], "type": { "label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "url", "ranges": ["URL"]
            }},
            "eurl": {"cardinality": [0, 0], "type": { "label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "eurl", "ranges": ["EmbeddableURL"]
            }},
            "text": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "text", "ranges": ["Text"]
            }},
            "longtext": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "longtext", "ranges": ["LongText"]
            }},
            "time": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "time", "ranges": ["Time"]
            }},
            "datetime": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "datetime", "ranges": ["DateTime"]
            }},
            "boolean": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "boolean", "ranges": ["Boolean"]
            }},
            "date": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "date", "ranges": ["Date"]
            }},
            "number": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "number", "ranges": ["Number"]
            }},
            "integer": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "integer", "ranges": ["Integer"]
            }},
            "float": {"cardinality": [0, 0], "type": {"label": "", "comment": "", "comment_plain": "", "domains": ["Article"],
                "id": "float", "ranges": ["Float"]
            }}
        }}};

        beforeEach(function() {
            mode = new editor.StructuredEditMode(sandbox, function(callback) {
                callback([['Article', 'Article']]);
            }, function(itemtype, callback) {
                callback(schema[itemtype]);
            }, {});
            mode.setContent('', function() {});
        });

        it('should render url field for url type', function() {
            expect(mode._generateFieldHtml('f', 0, ['URL'], null, 'http://x.com')).toEqual('<input class="field" data-type="URL" type="url" id="prop_f_0" name="f" value="http://x.com">');
        });

        it('should parse url as string', function() {
            mode.setContent('    #!yaml/schema\n    url: "http://x.com"\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    url: "http://x.com"\n');
        });

        it('should render url field for embeddable url type', function() {
            expect(mode._generateFieldHtml('f', 0, ['EmbeddableURL'], null, 'http://x.com')).toEqual(
                '<input class="field" data-type="EmbeddableURL" type="url" id="prop_f_0" name="f" value="http://x.com"> <a class="upload-link" href="#" data-field="prop_f_0">Upload</a>'
            );
        });

        it('should parse embeddable url as string', function() {
            mode.setContent('    #!yaml/schema\n    eurl: "http://x.com"\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    eurl: "http://x.com"\n');
        });

        it('should render text field for text type', function() {
            expect(mode._generateFieldHtml('f', 0, ['Text'], null, 'Hello')).toEqual('<input class="field" data-type="Text" type="text" id="prop_f_0" name="f" value="Hello">');
            expect(mode._generateFieldHtml('f', 0, ['Time'], null, 'Hello')).toEqual('<input class="field" data-type="Time" type="text" id="prop_f_0" name="f" value="Hello">');
            expect(mode._generateFieldHtml('f', 0, ['DateTime'], null, 'Hello')).toEqual('<input class="field" data-type="DateTime" type="text" id="prop_f_0" name="f" value="Hello">');
        });

        it('should render select field for enum text type', function() {
            expect(mode._generateFieldHtml('f', 0, ['Text'], ['A', 'B'], 'A')).toEqual('<select class="field" data-type="Text" id="prop_f_0" name="f">\n<option value="A" selected="selected">A</option>\n<option value="B">B</option>\n</select>');
        });

        it('should render textarea for longtext type', function() {
            expect(mode._generateFieldHtml('f', 0, ['LongText'], null, 'Hello')).toEqual('<textarea class="field" data-type="LongText" id="prop_f_0" name="f">Hello</textarea>');
        });

        it('should parse text as string', function() {
            mode.setContent('    #!yaml/schema\n    text: "Hello"\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    text: Hello\n');
        });

        it('should render checkbox for boolean type', function() {
            expect(mode._generateFieldHtml('f', 0, ['Boolean'], null, true)).toEqual('<input class="field" data-type="Boolean" type="checkbox" id="prop_f_0" name="f" value="on" checked="checked"> Yes');
            expect(mode._generateFieldHtml('f', 0, ['Boolean'], null, false)).toEqual('<input class="field" data-type="Boolean" type="checkbox" id="prop_f_0" name="f" value="on"> Yes');
        });

        it('should parse checkbox as boolean', function() {
            mode.setContent('    #!yaml/schema\n    boolean: true\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    boolean: true\n');

            var falses = ['FALSE', 'False', 'false'];
            for(var i = 0; i < falses.length; i++) {
                mode.setContent('    #!yaml/schema\n    boolean: ' + falses[i] + '\n', function() {});
                expect(mode.getContent()).toEqual('    #!yaml/schema\n    boolean: false\n');
            }
        });

        it('should render date field for date type', function() {
            expect(mode._generateFieldHtml('f', 0, ['Date'], null, '1979-03-27')).toEqual('<input class="field" data-type="Date" type="date" id="prop_f_0" name="f" value="1979-03-27">');
        });

        it('should render number field for number type', function() {
            expect(mode._generateFieldHtml('f', 0, ['Number'], null, 1.5)).toEqual('<input class="field" data-type="Number" type="number" id="prop_f_0" name="f" value="1.5">');
            expect(mode._generateFieldHtml('f', 0, ['Integer'], null, 1)).toEqual('<input class="field" data-type="Integer" type="number" id="prop_f_0" name="f" value="1">');
            expect(mode._generateFieldHtml('f', 0, ['Float'], null, 1.5)).toEqual('<input class="field" data-type="Float" type="number" id="prop_f_0" name="f" value="1.5">');
        });

        it('should parse number as number', function() {
            mode.setContent('    #!yaml/schema\n    number: 1.5\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    number: 1.5\n');

            mode.setContent('    #!yaml/schema\n    float: 1.5\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    float: 1.5\n');

            mode.setContent('    #!yaml/schema\n    integer: 1.5\n', function() {});
            expect(mode.getContent()).toEqual('    #!yaml/schema\n    integer: 1\n');
        });

        it('should prefer URL over Text', function() {
            expect(mode._generateFieldHtml('f', 0, ['Text', 'URL'], null, 'http://x.com')).toEqual('<input class="field" data-type="URL" type="url" id="prop_f_0" name="f" value="http://x.com">');

        });
    });

    describe('ContentParser', function() {
        var parser;

        beforeEach(function() {
            parser = new editor.ContentParser();
        });

        it('should parse empty body', function() {
            expect(parser.parseBody('')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'sections': {},
                'body': ''
            });
        });

        it('should parse .schema', function() {
            expect(parser.parseBody('.schema Hello')).toEqual({
                'itemtype': 'Hello',
                'data': {},
                'sections': {},
                'body': ''
            });
        });

        it('should parse simple text', function() {
            expect(parser.parseBody('Hello\nthere?')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'sections': {},
                'body': 'Hello\nthere?'
            });
        });

        it('should recognize itemtype', function() {
            expect(parser.parseBody('.schema Book\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': {},
                'sections': {},
                'body': 'Hello\nthere?'
            });
        });

        it('should retain other metadata', function() {
            expect(parser.parseBody('.schema Book\n.pub\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': [],
                'sections': {},
                'body': '.pub\n\nHello\nthere?'
            });
        });

        it('should recognize yaml block', function() {
            expect(parser.parseBody('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': {'author': 'AK'},
                'sections': {},
                'body': 'Hello\nthere?'
            });
        });

        it('should parse section block in body', function() {
            expect(parser.parseBody('Hey\n\nsection::---\nHello\nThere\n')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'sections': {'section': 'Hello\nThere'},
                'body': 'Hey'
            });
        });

        it('should parse two section blocks', function() {
            expect(parser.parseBody('s1::---\nHello\n\ns2::---\nThere\n')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'sections': {'s1': 'Hello', 's2': 'There'},
                'body': ''
            });
        });

        it('should parse two section blocks with the same name', function() {
            expect(parser.parseBody('s1::---\nHello\n\ns1::---\nThere\n')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'sections': {'s1': ['Hello', 'There']},
                'body': ''
            });
        });

        it('should generate empty string with default data', function() {
            var data = {
                'itemtype': 'Article',
                'data': {},
                'sections': {},
                'body': ''
            };
            expect(parser.generateBody(data)).toEqual('');
        });

        it('should generate simple text', function() {
            var data = {
                'itemtype': 'Article',
                'data': {},
                'sections': {},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('Hello\nthere?');
        });

        it('should generate schema metadata', function() {
            var data = {
                'itemtype': 'Book',
                'data': {},
                'sections': {},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('.schema Book\n\nHello\nthere?');
        });

        it('should generate yaml block', function() {
            var data = {
                'itemtype': 'Book',
                'data': {'author': 'AK'},
                'sections': {},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?');
        });

        it('should generate sections', function() {
            var data = {
                'itemtype': 'Article',
                'data': {'author': 'AK'},
                'sections': {'s1': 'Hello\nThere', 's2': 'Hey'},
                'body': 'Body goes here'
            };
            expect(parser.generateBody(data)).toEqual('    #!yaml/schema\n    author: AK\n\nBody goes here\n\ns1::---\n\nHello\nThere\n\ns2::---\n\nHey');
        });

        it('should generate sections array', function() {
            var data = {
                'itemtype': 'Article',
                'data': {'author': 'AK'},
                'sections': {'s1': ['Hello', 'There']},
                'body': 'Body goes here'
            };
            expect(parser.generateBody(data)).toEqual('    #!yaml/schema\n    author: AK\n\nBody goes here\n\ns1::---\n\nHello\n\ns1::---\n\nThere');
        });

        it('should roundtrip parse/generate', function() {
            var bodies = [
                '',
                'Hello\nthere?',
                '.schema Book\n\nHello\nthere?',
                '.schema Book\n.pub\n\nHello\nthere?',
                '.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?',
                '.schema Book\n.pub\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?',
                '.schema Book\n.pub\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?\n\ns1::---\n\nHello'
            ];
            for(var i = 0; i < bodies.length; i++) {
                var body = bodies[i];
                expect(parser.generateBody(parser.parseBody(body))).toEqual(body);
            }
        });
    });
});

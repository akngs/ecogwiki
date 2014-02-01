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
            callback(['Article']);
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
            mode = new editor.StructuredEditMode(sandbox, function(callback) {
                callback(['Article', 'Book', 'Person']);
            }, function(itemtype, callback) {
                callback(schema[itemtype]);
            });
            mode.setContent('', function() {});
        });

        it('should render itemtype selector', function() {
            var $itemtypeSelector = $(sandbox).find('#prop_itemtype');
            expect($itemtypeSelector.length).toEqual(1);
            expect($itemtypeSelector.val()).toEqual('Article');
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
        });

        it('should populate value of fields with content', function() {
            mode.setContent('    #!yaml/schema\n    field1: Hey\n    field2: ["Hello", "World"]\n    field3: ["Goodbye", "World"]\n\nHello', function() {});

            expect($(sandbox).find('#prop_field1_0').val()).toEqual('Hey');
            expect($(sandbox).find('#prop_field2_0').val()).toEqual('Hello');
            expect($(sandbox).find('#prop_field2_1').val()).toEqual('World');
            expect($(sandbox).find('#prop_field3_0').val()).toEqual('Goodbye');
            expect($(sandbox).find('#prop_field3_1').val()).toEqual('World');
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
            mode.setContent('.schema Person\n    #!yaml/schema\n    unknown: Hey\n', function() {});
            expect($(sandbox).find('#prop_unknown_0').val()).toEqual('Hey');
        });

        it('should retain unknown values', function() {
            mode.setContent('.schema Person\n\n    #!yaml/schema\n    unknown: Hey\n', function() {});
            $(sandbox).find('#prop_unknown_0').val('Hello');
            expect(mode.getContent()).toEqual('.schema Person\n\n    #!yaml/schema\n    unknown: Hello\n');
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
            expect($options.length).toEqual(3);
            expect($($options[0]).attr('value')).toEqual('field1');
            expect($($options[1]).attr('value')).toEqual('field2');
            expect($($options[2]).attr('value')).toEqual('field3');
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
            expect($(sandbox).find('#prop_field3_0').val()).toEqual('');
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
                'body': ''
            });
        });

        it('should parse .schema', function() {
            expect(parser.parseBody('.schema Hello')).toEqual({
                'itemtype': 'Hello',
                'data': {},
                'body': ''
            });
        });

        it('should parse simple text', function() {
            expect(parser.parseBody('Hello\nthere?')).toEqual({
                'itemtype': 'Article',
                'data': {},
                'body': 'Hello\nthere?'
            });
        });

        it('should recognize itemtype', function() {
            expect(parser.parseBody('.schema Book\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': {},
                'body': 'Hello\nthere?'
            });
        });

        it('should retain other metadata', function() {
            expect(parser.parseBody('.schema Book\n.pub\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': [],
                'body': '.pub\n\nHello\nthere?'
            });
        });

        it('should recognize yaml block', function() {
            expect(parser.parseBody('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?')).toEqual({
                'itemtype': 'Book',
                'data': {'author': 'AK'},
                'body': 'Hello\nthere?'
            });
        });

        it('should generate empty string with default data', function() {
            var data = {
                'itemtype': 'Article',
                'data': {},
                'body': ''
            };
            expect(parser.generateBody(data)).toEqual('');
        });

        it('should generate simple text', function() {
            var data = {
                'itemtype': 'Article',
                'data': {},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('Hello\nthere?');
        });

        it('should generate schema metadata', function() {
            var data = {
                'itemtype': 'Book',
                'data': {},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('.schema Book\n\nHello\nthere?');
        });

        it('should generate yaml block', function() {
            var data = {
                'itemtype': 'Book',
                'data': {'author': 'AK'},
                'body': 'Hello\nthere?'
            };
            expect(parser.generateBody(data)).toEqual('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?');
        });

        it('should roundtrip parse/generate', function() {
            var bodies = [
                '',
                'Hello\nthere?',
                '.schema Book\n\nHello\nthere?',
                '.schema Book\n.pub\n\nHello\nthere?',
                '.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?',
                '.schema Book\n.pub\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?'
            ];
            for(var i = 0; i < bodies.length; i++) {
                var body = bodies[i];
                expect(parser.generateBody(parser.parseBody(body))).toEqual(body);
            }
        });
    });
});

//    var types = [
//        'Article',
//        'Person'
//    ];
//    var person = {
//        "supertypes": ["Thing"],
//        "properties": {
//            "birthDate": {
//                "type": {
//                    "reversed_label": "%s Born",
//                    "label": "Birth Date",
//                    "comment": "Date of birth.",
//                    "domains": ["Person"],
//                    "ranges": ["Date"],
//                    "comment_plain": "Date of birth.",
//                    "id": "birthDate"
//                },
//                "cardinality": [0, 0]
//            },
//            "email": {
//                "type": {
//                    "reversed_label": "[%s] Email",
//                    "label": "Email",
//                    "comment": "Email address.",
//                    "domains": ["Person", "ContactPoint", "Organization"],
//                    "ranges": ["Text"],
//                    "comment_plain": "Email address.",
//                    "id": "email"
//                },
//                "cardinality": [1, 0]
//            },
//            "gender": {
//                "type": {
//                    "reversed_label": "[%s] Gender",
//                    "label": "Gender",
//                    "comment": "Gender of the person.",
//                    "domains": ["Person"],
//                    "ranges": ["Text"],
//                    "comment_plain": "Gender of the person.",
//                    "id": "gender"
//                },
//                "cardinality": [1, 1]
//            },
//            "parent": {
//                "type": {
//                    "reversed_label": "Children (%s)",
//                    "label": "Parent",
//                    "comment": "A parent of this person.",
//                    "domains": ["Person"],
//                    "ranges": ["Person"],
//                    "comment_plain": "A parent of this person.",
//                    "id": "parent"
//                },
//                "cardinality": [0, 0]
//            }
//        },
//        "comment": "",
//        "subtypes": ["Politician"],
//        "url": "http://schema.org/Person",
//        "label": "Person",
//        "ancestors": ["Thing"],
//        "comment_plain": "",
//        "id": "Person",
//        "plural_label": "People"
//    };

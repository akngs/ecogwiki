/*global describe, it, expect*/
describe('Editor.parseBody', function() {
    it('should parse empty body', function() {
        expect(editor.parseBody('')).toEqual({
            'itemtype': 'Article',
            'data': {},
            'body': ''
        });
    });

    it('should parse simple text', function() {
        expect(editor.parseBody('Hello\nthere?')).toEqual({
            'itemtype': 'Article',
            'data': {},
            'body': 'Hello\nthere?'
        });
    });

    it('should recognize itemtype', function() {
        expect(editor.parseBody('.schema Book\n\nHello\nthere?')).toEqual({
            'itemtype': 'Book',
            'data': {},
            'body': 'Hello\nthere?'
        });
    });

    it('should retain other metadata', function() {
        expect(editor.parseBody('.schema Book\n.pub\n\nHello\nthere?')).toEqual({
            'itemtype': 'Book',
            'data': [],
            'body': '.pub\n\nHello\nthere?'
        });
    });

    it('should recognize yaml block', function() {
        expect(editor.parseBody('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?')).toEqual({
            'itemtype': 'Book',
            'data': {'author': 'AK'},
            'body': 'Hello\nthere?'
        });
    });
});

describe('Editor.generateBody', function() {
    it('should generate empty string with default data', function() {
        var data = {
            'itemtype': 'Article',
            'data': {},
            'body': ''
        }
        expect(editor.generateBody(data)).toEqual('');
    });

    it('should generate simple text', function() {
        var data = {
            'itemtype': 'Article',
            'data': {},
            'body': 'Hello\nthere?'
        };
        expect(editor.generateBody(data)).toEqual('Hello\nthere?');
    });

    it('should generate schema metadata', function() {
        var data = {
            'itemtype': 'Book',
            'data': {},
            'body': 'Hello\nthere?'
        };
        expect(editor.generateBody(data)).toEqual('.schema Book\n\nHello\nthere?');
    });

    it('should generate yaml block', function() {
        var data = {
            'itemtype': 'Book',
            'data': {'author': 'AK'},
            'body': 'Hello\nthere?'
        };
        expect(editor.generateBody(data)).toEqual('.schema Book\n\n    #!yaml/schema\n    author: AK\n\nHello\nthere?');
    });
});


describe('Editor parse/generate roundtrip', function() {
    it('should work two-way', function() {
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
            expect(editor.generateBody(editor.parseBody(body))).toEqual(body);
        }
    });
});


describe('Editor.generateForm', function() {
    var types = [
        'Article',
        'Person'
    ];
    var person = {
        "supertypes": ["Thing"],
        "properties": {
            "birthDate": {
                "type": {
                    "reversed_label": "%s Born",
                    "label": "Birth Date",
                    "comment": "Date of birth.",
                    "domains": ["Person"],
                    "ranges": ["Date"],
                    "comment_plain": "Date of birth.",
                    "id": "birthDate"
                },
                "cardinality": [0, 0]
            },
            "email": {
                "type": {
                    "reversed_label": "[%s] Email",
                    "label": "Email",
                    "comment": "Email address.",
                    "domains": ["Person", "ContactPoint", "Organization"],
                    "ranges": ["Text"],
                    "comment_plain": "Email address.",
                    "id": "email"
                },
                "cardinality": [1, 0]
            },
            "gender": {
                "type": {
                    "reversed_label": "[%s] Gender",
                    "label": "Gender",
                    "comment": "Gender of the person.",
                    "domains": ["Person"],
                    "ranges": ["Text"],
                    "comment_plain": "Gender of the person.",
                    "id": "gender"
                },
                "cardinality": [1, 1]
            },
            "parent": {
                "type": {
                    "reversed_label": "Children (%s)",
                    "label": "Parent",
                    "comment": "A parent of this person.",
                    "domains": ["Person"],
                    "ranges": ["Person"],
                    "comment_plain": "A parent of this person.",
                    "id": "parent"
                },
                "cardinality": [0, 0]
            }
        },
        "comment": "",
        "subtypes": ["Politician"],
        "url": "http://schema.org/Person",
        "label": "Person",
        "ancestors": ["Thing"],
        "comment_plain": "",
        "id": "Person",
        "plural_label": "People"
    };

    it('should generate form', function() {
        expect(editor.generateForm(types, person)).toEqual(
            '<form>\n' +
            '<select id="sed_type">\n' +
            '<option>Article</option>\n' +
            '<option>Person</option>\n' +
            '</select>\n' +
            '<label for="prop_email">Email</label>\n' +
            '<input type="text" id="prop_email" name="prop_email" value="">\n' +
            '<label for="prop_gender">Gender</label>\n' +
            '<input type="text" id="prop_gender" name="prop_gender" value="">\n' +
            '</form>'
        );
    });
});

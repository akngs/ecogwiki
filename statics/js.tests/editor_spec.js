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

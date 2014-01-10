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

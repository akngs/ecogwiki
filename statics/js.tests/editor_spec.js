/*global describe, it, expect*/
describe("Editor.parseBody", function() {
    it("should parse empty body", function() {
        expect(editor.parseBody('')).toEqual({
            'itemtype': 'Article',
            'properties': [],
            'body': ''
        });
    });

    it("should parse simple text", function() {
        expect(editor.parseBody('Hello\nthere?')).toEqual({
            'itemtype': 'Article',
            'properties': [],
            'body': 'Hello\nthere?'
        });
    });

    it("should recognize itemtype", function() {
        expect(editor.parseBody('.schema Book\n\nHello\nthere?')).toEqual({
            'itemtype': 'Book',
            'properties': [],
            'body': 'Hello\nthere?'
        });
    });

    it("should retain other metadata", function() {
        expect(editor.parseBody('.schema Book\n.pub\n\nHello\nthere?')).toEqual({
            'itemtype': 'Book',
            'properties': [],
            'body': '.pub\n\nHello\nthere?'
        });
    });
});


describe("Editor.extractMetadata", function() {
    it("should extract nothing from empty string", function() {
        expect(editor.extractMetadata('', ['schema'])).toEqual({
            'body': '',
            'metadata': {}
        });
    });

    it("should extract key-only metadata", function() {
        expect(editor.extractMetadata('.pub', ['pub'])).toEqual({
            'body': '',
            'metadata': {'pub': true}
        });
    });

    it("should extract key-value metadata", function() {
        expect(editor.extractMetadata('.pub Test', ['pub'])).toEqual({
            'body': '',
            'metadata': {'pub': 'Test'}
        });
    });

    it("should extract multiple metadata", function() {
        expect(editor.extractMetadata('.pub Test\n.schema Book\n\nHello', ['schema'])).toEqual({
            'body': '.pub Test\n\nHello',
            'metadata': {'schema': 'Book'}
        });
    });
});

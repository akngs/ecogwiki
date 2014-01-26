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
            var editlet = editor2.TextEditlet.createInstance(textarea);
            expect(editlet instanceof editor2.CodeMirrorTextEditlet).toBeTruthy();
        });

        it('should create SimpleTextEditlet if there is no CodeMirror', function() {
            delete window['CodeMirror'];

            var editlet = editor2.TextEditlet.createInstance(textarea);
            expect(editlet instanceof editor2.SimpleTextEditlet).toBeTruthy();
        });
    });

    describe('SimpleTextEditlet', function() {
        var textarea;
        var editlet;

        beforeEach(function() {
            sandbox.innerHTML = '<form><textarea></textarea><input type="submit"></form>';
            textarea = sandbox.querySelector('textarea');
            editlet = new editor2.SimpleTextEditlet(textarea);
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
            editlet = new editor2.CodeMirrorTextEditlet(textarea);
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
            var editlet = new editor2.CodeMirrorTextEditlet(textarea);
            expect(editlet.getNextFocusTarget().getAttribute('id')).toEqual('target');
        });

        it('should select the first form element if the textarea is the last element', function() {
            sandbox.innerHTML = '<form><input type="text" id="target"><textarea id="this"></textarea></form>';
            var textarea = sandbox.querySelector('textarea');
            var editlet = new editor2.CodeMirrorTextEditlet(textarea);
            expect(editlet.getNextFocusTarget().getAttribute('id')).toEqual('target');
        });
    });
});


describe('Editor', function() {
    var sandbox;
    var textarea;
    var editor;
    var $root;

    beforeEach(function() {
        sandbox = document.createElement('div');
        document.body.appendChild(sandbox);

        sandbox.innerHTML = '<form><textarea></textarea></form>';
        textarea = sandbox.querySelector('textarea');
        editor = new editor2.Editor(textarea);
        $root = $(textarea).next();
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
        expect(editor.getActiveModeName()).toEqual('plain');
    });

    it('should switch plain mode to structured modes', function() {
        $root.find('ul.mode-tab > li.structured > a').click();
        expect(editor.getActiveModeName()).toEqual('structured');
        expect(editor.getActiveMode() instanceof editor2.StructuredEditMode).toBeTruthy();
        expect($root.find('ul.mode-tab > li.active').hasClass('structured')).toBeTruthy();
        expect($root.find('ul.mode-pane > li.plain').css('display')).toEqual('none');
    });

    it('should switch structured mode to plain modes', function() {
        $root.find('ul.mode-tab > li.plain > a').click();
        expect(editor.getActiveModeName()).toEqual('plain');
        expect(editor.getActiveMode() instanceof editor2.PlainEditMode).toBeTruthy();
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
            var mode = new editor2.PlainEditMode(sandbox, 'Hello');
            var editlet = mode.getEditlet();
            expect(mode.getContent()).toEqual('Hello');
            expect(editlet.getContent()).toEqual('Hello');
        });
        it('should connected to TextEditlet', function() {
            var mode = new editor2.PlainEditMode(sandbox, 'Hello');
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
    });
});

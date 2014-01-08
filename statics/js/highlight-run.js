var highlightRun = (function($) {
    "use strict";

    $('pre > code').each(function(i, e) {
        var re = /^#!(sh|csharp|c\+\+|css|coffeescript|diff|html|xml|json|java|javascript|makefile|markdown|objectivec|php|perl|python|ruby|sql)\s/;
        if(re.test(this.innerHTML)) {
            this.innerHTML = this.innerHTML.replace(re, '');
			hljs.highlightBlock(e);
        }
    });
});

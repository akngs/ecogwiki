var jumlyRun = (function($) {
    "use strict";

    $('pre > code').each(function() {
        if(this.innerHTML.indexOf('#!uml\n') === 0) {
            var $parent = $(this.parentNode);
            JUMLY.eval($(this), {'into': $parent});
            var $diagram = $parent.find('div.diagram');
            $parent.replaceWith($diagram);
            $diagram.height($diagram.prop('scrollHeight'));
        }
    });
});

$(function() {
    "use strict";

    function main() {
        registerSeditor();

        $('.editor-tab').on('click', '.tab > a', function(e) {
            var $this = $(this);
            // do nothing if it's already active
            if($this.parent().hasClass('active')) {
                e.preventDefault();
                return;
            }

            // make it active
            $('.editor-tab .tab.active').removeClass('active');
            $('.editor-content .content.active').removeClass('active');

            $this.parent().addClass('active');
            var name = $this.parent().data('name');
            $('.editor-content .content.' + name).addClass('active');
        });
    }

    function registerSeditor() {
        $('.editor-tab').append('<li class="tab struct" data-name="struct"><a href="#struct">Structured</a></li>');
        $('.editor-content').append('<li class="content struct" data-name="struct">...</li>');
    }

    main();
});


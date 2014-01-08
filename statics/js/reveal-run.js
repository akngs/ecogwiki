/* converts plain HTML into reveal.js recognizible one */
var revealRun = (function($) {
    "use strict";

    // find top level elements
    var $tops = $('article .body > *');

    // prepare containers
    $('body').append('<div class="reveal">');
    $('body .reveal').append('<div class="slides">');
    var $slides = $('body .reveal .slides');

    // move top levels into slides
    var $slide = null;
    $tops.each(function() {
        if(this.nodeName.toLowerCase() == 'h1') {
            $slide = $('<section>').appendTo($slides);
        }
        if($slide) $slide.append(this);
    });

    // move edit link to nav bar
    $('<li>').appendTo('nav ul').append($('header .edit_menu'));

    // done
    Reveal.initialize({
        'rollingLinks': false,
        'center': false,
        'transition': 'none',
        'transitionSpeed': 'fast',
        'controls': false,
        'history': true
    });
});

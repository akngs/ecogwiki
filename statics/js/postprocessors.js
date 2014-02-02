/*global head*/
var postprocessors = (function($) {
    "use strict";

    var PostProcessor = Class.extend({
        init: function(rootEl) {
            this._rootEl = rootEl;
        },
        check: function() {return false;},
        runBeforeDependencies: function() {},
        run: function() {},
        dependencies: function() {return [];},

        hasMetadata: function(key) {
            var el = this._rootEl.querySelector('.page-metadata .key-' + key);
            return !!el;
        },
        hasHashbang: function(key) {
            var lis = this._rootEl.querySelectorAll('.page-hashbang li');
            for(var i = 0; i < lis.length; i++) {
                if(lis[i].innerHTML === key) return true;
            }
            return false;
        }
    });


    var RevealProcessor = PostProcessor.extend({
        check: function() {
            var inPreview = document.getElementById('wikibody_preview');
            return !inPreview && this.hasMetadata('pt');
        },
        dependencies: function() {
            return [
                '/statics/css/vendor/reveal.css',
                '/statics/css/vendor/reveal-theme-simple.css',
                '/statics/js/reveal.js'
            ];
        },
        run: function() {
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
            window['Reveal'].initialize({
                'rollingLinks': false,
                'center': false,
                'transition': 'none',
                'transitionSpeed': 'fast',
                'controls': false,
                'history': true
            });
        }
    });


    var HighlightProcessor = PostProcessor.extend({
        init: function(rootEl) {
            this._super(rootEl);
            this._langs = [
                'sh', 'csharp', 'c++', 'css', 'coffeescript', 'diff', 'html',
                'xml', 'json', 'java', 'javascript', 'makefile', 'markdown',
                'objectivec', 'php', 'perl', 'python', 'ruby', 'sql'
            ];
        },
        check: function() {
            var codes = this._rootEl.querySelectorAll('pre > code');
            for(var i = 0; i < codes.length; i++) {
                if(this._isSupportedCodeBlock(codes[i])) return true;
            }
            return false;
        },
        dependencies: function() {
            return [
                'http://yandex.st/highlightjs/8.0/styles/default.min.css',
                'http://yandex.st/highlightjs/8.0/highlight.min.js'
            ];
        },
        run: function() {
            var codes = this._rootEl.querySelectorAll('pre > code');
            var re = /^#!.+?(\n|\r)/;
            for(var i = 0; i < codes.length; i++) {
                if(!this._isSupportedCodeBlock(codes[i])) continue;

                codes[i].innerHTML = codes[i].innerHTML.replace(re, '');
                window['hljs'].highlightBlock(codes[i]);
            }
        },
        _isSupportedCodeBlock: function(codeEl) {
            var html = codeEl.innerHTML;
            for(var i = 0; i < this._langs.length; i++) {
                if(html.indexOf('#!' + this._langs[i]) === 0) return true;
            }
            return false;
        }
    });


    var VizProcessor = PostProcessor.extend({
        check: function() {
            return this.hasHashbang('dot') || this.hasHashbang('dot/s');
        },
        dependencies: function() {
            return ['/statics/js/viz.js'];
        },
        run: function() {
            this.processInlineElements();
            this.processBlockElements();
        },
        processInlineElements: function() {
            $('code').each(function() {
                if(this.parentNode.nodeName.toLowerCase() === 'pre') return;
                if(this.innerHTML.indexOf('#!dot/s;') === 0) {
                    var prefix = [
                        'digraph {',
                        '    edge [fontsize=9, penwidth=0.5, arrowsize=0.5, color="#444444", labeldistance=1.2];',
                        '    node [shape="rect", fillcolor="#EEEEEE", color="#444444", style="rounded,filled", fontname="NanumGothic", fontsize=9, penwidth=0.5, width="0.1", height="0"];',
                        '    rankdir="LR"; pad="0.02"; nodesep="0.06";'
                    ].join('\n');
                    var postfix = '}';

                    var code = prefix + $(this).text().substr(8) + postfix;
                    var codeWithExtraWhiteSpace = code + new Array(code.length).join(' ');
                    var result = Viz(codeWithExtraWhiteSpace, 'svg');
                    $(this).replaceWith('<span class="inlinegraph">' + result + '</span>');
                }
            });
        },
        processBlockElements: function() {
            $('pre > code').each(function() {
                var code;

                if(this.innerHTML.indexOf('#!dot\n') === 0) {
                    code = $(this).text();
                } else if(this.innerHTML.indexOf('#!dot/s\n') === 0) {
                    var prefix = [
                        'digraph {',
                        '    edge [fontsize=9, penwidth=0.5, arrowsize=0.5, color="#444444", labeldistance=1.2];',
                        '    node [shape="rect", fillcolor="#EEEEEE", color="#444444", style="rounded,filled", fontname="NanumGothic", fontsize=9, penwidth=0.5, width="0.2" height="0.2"];',
                        '    nodesep="0.06";'
                    ];
                    // if screen width is broad enough, make it horizontally wide
                    if($(this._rootEl).width() > 500) {
                        prefix.push('    rankdir="LR";');
                    } else {
                        prefix.push('    rankdir="TB";');
                    }
                    prefix = prefix.join('\n');

                    var postfix = '}';

                    code = prefix + $(this).text().substr(8) + postfix;
                } else {
                    return;
                }

                // Add extra SP to deal with unicode bug
                var extraWhitespace = code + new Array(code.length).join(' ');
                $(this.parentNode).replaceWith(Viz(extraWhitespace, 'svg'));
            });
        }
    });


    var JumlyProcessor = PostProcessor.extend({
        check: function() {
            return this.hasHashbang('uml');
        },
        dependencies: function() {
            return [
                '/statics/css/vendor/jumly.css',
                '/statics/js/coffee-script.js',
                '/statics/js/jumly.min.js'
            ];
        },
        run: function() {
            $('pre > code').each(function() {
                if(this.innerHTML.indexOf('#!uml\n') !== 0) return;

                var $parent = $(this.parentNode);
                window['JUMLY'].eval($(this), {'into': $parent});
                var $diagram = $parent.find('div.diagram');
                $parent.replaceWith($diagram);
                $diagram.height($diagram.prop('scrollHeight'));
            });
        }
    });


    var MathjaxProcessor = PostProcessor.extend({
        check: function() {
            return this.hasHashbang('mathjax');
        },
        dependencies: function() {
            return ['http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'];
        },
        runBeforeDependencies: function() {
            if('MathJax' in window) return;

            window['MathJax'] = {
                displayAlign: "left"
            };
        },
        run: function() {
            MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
        }
    });


    var loadedDependencies = [];

    function run(rootEl) {
        var procs = [
            new RevealProcessor(rootEl),
            new VizProcessor(rootEl),
            new HighlightProcessor(rootEl),
            new MathjaxProcessor(rootEl),
            new JumlyProcessor(rootEl)
        ];
        var procsToRun = [];
        var dependencies = [];

        // Load dependencies
        procs.forEach(function(p) {
            if(!p.check()) return;

            procsToRun.push(p);
            p.dependencies().forEach(function(d) {
                // do not load the same resource more than once
                if(loadedDependencies.indexOf(d) !== -1) return;

                dependencies.push(d);
                loadedDependencies.push(d);
            });
        });

        // Run codes before loading dependencies
        procsToRun.forEach(function(p) {
            p.runBeforeDependencies();
        });

        // Load dependencies and run()
        if(dependencies.length) {
            head.load(dependencies, function() {
                procsToRun.forEach(function(p) {
                    p.run();
                });
            });
        } else {
            procsToRun.forEach(function(p) {
                p.run();
            });
        }
    }

    return {
        'run': run,

        'RevealProcessor': RevealProcessor,
        'VizProcessor': VizProcessor,
        'HighlightProcessor': HighlightProcessor,
        'MathjaxProcessor': MathjaxProcessor,
        'JumlyProcessor': JumlyProcessor
    };
})($);

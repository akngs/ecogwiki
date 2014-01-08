var vizRun = (function($) {
    "use strict";

    // process inline elements
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
            code += new Array(code.length).join(' ');
            var result = Viz(code, 'svg');
            $(this).replaceWith('<span class="inlinegraph">' + result + '</span>');
        }
    });

    // process block elements
    $('pre > code').each(function() {
        if(this.innerHTML.indexOf('#!dot\n') === 0) {
            var code = $(this).text();
            code += new Array(code.length).join(' ');
            var result = Viz(code, 'svg');
            $(this.parentNode).replaceWith(result);
        } else if(this.innerHTML.indexOf('#!dot/s\n') === 0) {
            var prefix = [
                'digraph {',
                '    edge [fontsize=9, penwidth=0.5, arrowsize=0.5, color="#444444", labeldistance=1.2];',
                '    node [shape="rect", fillcolor="#EEEEEE", color="#444444", style="rounded,filled", fontname="NanumGothic", fontsize=9, penwidth=0.5, width="0.2" height="0.2"];',
                '    nodesep="0.06";'
            ];
            // if screen width is broad enough, make it horizontally wide
            if($(document.body).width() > 500) {
                prefix.push('    rankdir="LR";');
            } else {
                prefix.push('    rankdir="TB";');
            }
            prefix = prefix.join('\n');

            var postfix = '}';

            var code = prefix + $(this).text().substr(8) + postfix;
            code += new Array(code.length).join(' ');
            var result = Viz(code, 'svg');
            $(this.parentNode).replaceWith(result);
        }
    });
});

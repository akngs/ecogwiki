$(function() {
    // Render score graph
    (function() {
        $('span.score').each(function() {
            var $this = $(this);
            var percent = (+$this.text() * 100) + '%';
            var $replace = $('<span>').addClass('scorebar');
            $('<span>').appendTo($replace).addClass('bar').css('width', percent);
            $this.replaceWith($replace);
        })
    })();

    // Localize datetime
    (function() {
        $('time').each(function() {
            // if there are multiple children it means it's a wikilink
            if(this.childNodes.length > 1) return;

            var date = new Date(this.getAttribute('datetime'));
            var month = '0' + (date.getMonth() + 1);
            var day = '0' + date.getDate();
            var hour = '0' + date.getHours();
            var min = '0' + date.getMinutes();
            var result;
            if(this.innerHTML.length == 11) {
                result = month.substr(month.length - 2) + '-' +
                    day.substr(day.length - 2) + ' ' +
                    hour.substr(hour.length - 2) + ':' +
                    min.substr(min.length - 2);
            } else {
                var year = '' + date.getFullYear();
                result = year + '-' +
                    month.substr(month.length - 2) + '-' +
                    day.substr(day.length - 2) + ' ' +
                    hour.substr(hour.length - 2) + ':' +
                    min.substr(min.length - 2);
            }
            this.innerHTML = result;
        });
    })();

    // Make strong>em elements to quotable
    (function() {
        var url = $('link[rel="canonical"]').attr('href');
        $('strong > em').wrap(function() {
            var text = $(this).text();
            var twitter = $('meta[name="twitter:site"]').attr('content').substring(1);
            return '<a class="quotable" href="https://twitter.com/intent/tweet?via=' + twitter + '&url=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(text) + '" />';
        });
    })();

    // Search box
    (function() {
        var $search = $('#searchbox');
        if ($search.length === 0) return;

        $($search[0].form).on('submit', function() {
            var value = $search.val();
            if(value) {
                document.cookie = 'ecogwiki_search_query=' + value;
                location.href = '/' + value;
            }
            return false;
        })
    })();

    // Shortcut keys
    (function() {
        var $editor = $('.editform, .preferencesform');

        // not in editor mode
        if ($editor.length) return;

        var $caret_targets = $('.caret-target');
        var caret_index = 0;
        if($caret_targets.length) navigateFocus(caret_index, true);

        // shortcuts
        var shortcuts = [];
        $('.shortcut').each(function() {
            shortcuts.push($(this).data('shortcut').toUpperCase());
        });

        $(window).on('keydown', function(e) {
            if(e.metaKey || e.ctrlKey) return true;

            var keyCode = e.keyCode;
            var key = String.fromCharCode(keyCode);

            if ($('#searchbox').is(':focus')) {
                if(27 === keyCode) {
                    $('#searchbox').blur();
                    return false;
                } else {
                    return true;
                }
            }

            if(shortcuts.indexOf(key) != -1) {
                $('#shortcut_' + key).focus();
                return false;
            } else if(69 === keyCode) {
                // [E]
                $('#edit').focus();
                return false;
            } else if(191 === keyCode || 83 === keyCode) {
                // [/] or [S]earch
                $('#searchbox').focus();
                return false;
            } else if(74 === keyCode) {
                // J for down
                $caret_targets = $('.caret-target');

                if($caret_targets.length) {
                    caret_index++;
                    if(caret_index >= $caret_targets.length) caret_index = 0;
                    navigateFocus(caret_index, false);
                }
                return false;
            } else if(75 === keyCode) {
                // K for up
                $caret_targets = $('.caret-target');

                if($caret_targets.length) {
                    caret_index--;
                    if(caret_index < 0) caret_index = $caret_targets.length - 1;
                    navigateFocus(caret_index, false);
                }
                return false;
            } else {
                return true;
            }
        });

        function navigateFocus(index, isFirstTime) {
            $('.vcaret').removeClass('vcaret');
            $('.vcaret-parent').removeClass('vcaret-parent');

            var $target = $($caret_targets[index]);
            $target.addClass('vcaret').focus();
            if(isFirstTime) return;

            var $parent = $target.parent();
            if($parent[0].nodeName === 'TD') {
                $parent = $parent.parent();
            }

            $parent
                .addClass('vcaret-parent')
                .on('transitionend', function() {
                    $(this).removeClass('vcaret-parent');
                }
            );
        }
    })();

    // Embed wikiquery results
    (function() {
        $('a.wikiquery').each(function() {
            var $this = $(this);
            if(this.parentNode.firstChild === this && this.parentNode.lastChild === this) {
                if(this.parentNode.nodeName == 'P') {
                    // P cannot contain block-level elements so replace it with div
                    var $container = $('<div>');
                    $container.addClass('wikiquery-container');
                    $(this.parentNode).replaceWith($container);
                    $container.load($this.attr('href') + '?view=bodyonly .wrap');
                } else {
                    // Other block-level elements can contain block-level elements so use it as a parent
                    $(this.parentNode).addClass('wikiquery-container').load($this.attr('href') + '?view=bodyonly .wrap');
                }
            } else {
                // Do nothing for now (I don't know what should be happened here, yet)
            }
        });
    })();

    // Checkbox
    (function() {
        var selector = 'article input[type="checkbox"]';

        if($('#edit').length === 0) {
            $(selector).prop('disabled', true);
            return;
        }

        $(document).on('change', selector, function() {
            var $this = $(this);
            var checked = $(this).is(':checked') ? '1' : '0';
            var revision = parseInt($('.revision').text());
            var index = $this.index(selector);

            $(selector).prop('disabled', true);
            $.post('?_method=PUT&partial=checkbox[' + index + ']', {'body': checked, 'revision': revision}, function(data) {
                $('.revision').text(data['revision']);
            }).fail(function() {
                alert('Failed to update content. Please refresh the page.');
            }).done(function() {
                $(selector).prop('disabled', false);
            });
        });
    })();

    // Close button
    (function() {
        $(document).on('click', '.message .close', function() {
            $(this.parentNode).hide();
        });
    })();

    
    var loadingIndicator = '<div class="loading-indicator">' +
        '<div class="blockG" id="rotateG_01"></div>' +
        '<div class="blockG" id="rotateG_02"></div>' +
        '<div class="blockG" id="rotateG_03"></div>' +
        '<div class="blockG" id="rotateG_04"></div>' +
        '<div class="blockG" id="rotateG_05"></div>' +
        '<div class="blockG" id="rotateG_06"></div>' +
        '<div class="blockG" id="rotateG_07"></div>' +
        '<div class="blockG" id="rotateG_08"></div>' + '</div>';

    // Pagination
    (function() {
        $('.next-page').on('click', function(e) {
            e.preventDefault();
            if($(this).hasClass('loading')) return;

            
            var url = $(this).attr('href');
            var $container = $('<table></table>');
            var $target = $('.pagelist tbody');

            $(this).addClass('loading');
            $('.next-page').hide();
            $('.next-page').after(loadingIndicator);
            $container.load(url + '&view=bodyonly .wrap', function() {
                $('.loading-indicator').remove()
                $('.next-page').show();
                var $this = $(this);
                var $rows = $this.find('tr.page');
                if($rows.length) {
                    $rows.each(function() {$target.append(this);});
                    $('.next-page')
                        .attr('href', $this.find('.next-page').attr('href'))
                        .removeClass('loading');
                } else {
                    $('.next-page').remove();
                }
            });
        });
    })();

    // Track outbound links
    (function() {
        var host = window.location.host;
        $('article').on('click', 'a:not(.wikipage)', function() {
            var url = String(this.href);
            if(url.indexOf('http://' + host) === 0 ||
               url.indexOf('https://' + host) === 0 ||
               url.indexOf('/') === 0) return true;
            ga('send', 'event', 'Outbound links', url);
        });
    })();
});

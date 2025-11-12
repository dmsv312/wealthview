(function ($) {
    // block = #articles_block
    // url = '/articles/lazy_load_articles/'

    $('#lazyLoadLink').on('click', function () {
        let link = $(this);
        let block = link.data("block");
        let page = link.data('page');
        let url = link.data('url');
        $.ajax({
            type: 'post',
            url: url,
            data: {
                'page': page,
                'csrfmiddlewaretoken': window.CSRF_TOKEN // from index.html
            },
            success: function (data) {
                // if there are still more pages to load,
                // add 1 to the "Load More Posts" link's page data attribute
                // else hide the link
                if (data.has_next) {
                    link.data('page', page + 1);
                } else {
                    link.hide();
                }
                // append html to the posts div
                $(block).append(data.instances_html);
            },
            error: function (xhr, status, error) {
                // shit happens friends!
                // alert(":(");
            }
        });
    });
}(jQuery));
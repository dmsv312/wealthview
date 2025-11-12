let selector = ".review_filter_field";

$(function () { // Shorthand for $(document).ready(function() {
    save_checkboxes();
    process_single_filters();
    process_sort_select_box();
});

function process_sort_select_box() {
    let url = new URLSearchParams(window.location.search).toString();
    let args = url.split("&").filter(token => token_predicate(token, "order_by")).map(token => token.replace("order_by=", ""));
    args.forEach(function (value) {
        let str = $("#sort_selector_" + value).html();
        $("#main_sort_selector").html(str);
    });
}

function process_single_filters() {
    let url = new URLSearchParams(window.location.search).toString();
    let args = url.split("&").filter(token => token_predicate(token, "status")).map(token => token.replace("status=", ""));
    args.forEach(function (value) {
        $("#single_filter_" + value).toggleClass("active");
    });
}

function token_predicate(token, pattern) {
    return token.toString().includes(pattern)
}

function save_checkboxes() {
    // Load previous values
    // checkbox
    $(selector + ':checkbox').each(function () {
        $(this).prop('checked', localStorage.getItem(this.id) === 'true');
    });
    // radio
    $(selector + ':radio').each(function () {
        $(this).prop('checked', localStorage.getItem(this.id) === 'true');
    });
    // Save current values
    $(selector).click(function () {
        // checkbox
        $(selector + ':checkbox').each(function () {
            localStorage.setItem(this.id, $(this).prop('checked'));
        });
        // radio
        $(selector + ':radio').each(function () {
            localStorage.setItem(this.id, $(this).prop('checked'));
        });
    });
}
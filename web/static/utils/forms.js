/***************************************************************/
$(".readonly").on('keydown paste', function (e) {
    e.preventDefault();
});

/***************************************************************/
$(".clear_validity").click(function (e) {
    e.preventDefault();
    $(".show_validity").removeClass("show_validity");
});
/***************************************************************/
$("[type='submit']").click(function () {
    validate_dates();
    if ($(":invalid").length) {
        $(this).parents("form").addClass("show_validity");
    }
});

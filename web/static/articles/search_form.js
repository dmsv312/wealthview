$(function () {
    $("#search_btn").bind("click", function () {
        if ($("#search_input").val() !== "") {
            $(".search_form").submit();
        }
    })
});
$(function () {
    $(".type_select").bind("click", function () {
        let selected_type = $(this).attr("id");
        $("#id_type").val(selected_type);
    })
});
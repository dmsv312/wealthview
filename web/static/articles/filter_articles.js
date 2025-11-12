function select_option_by_text(select_block, text) {
    // console.log($(select_block).find('option:selected').text());
    $(select_block).find('option:selected').prop("selected", false);
    $(select_block + " option").filter(function () {
        return $(this).text() === text;
    }).prop("selected", true);
    // console.log($(select_block).find('option:selected').text());
}

$(function () {
    let filter_switcher = "#id_category";
    // Print current category
    let selected = $(filter_switcher).find('option:selected');
    if (selected.val() > 0) {
        // document.title = "Статьи: " + selected.text();
        let selected_category = "<p style='font-size: 14px; margin-top: 10px'><b>Категория:</b> " + selected.text() + "</p>";
        let reset_button = "<a href='/articles' class='reset_filter_btn blue_btn' style='color:#fff;' >Сбросить фильтр</a>";
        $(".selected_filter").append(selected_category).append(reset_button);
    } else {
        $(".selected_filter").html("");
    }
    // Search by Clicked Filter
    $(".nav-link").bind("click", function () {
        // Get filter ID
        let new_filter = $(this).find(".subcategory_title").attr("id");
        // Fill option
        select_option_by_text(filter_switcher, new_filter);
        // Submit form
        $("#form_switcher").submit()
    });

    $("#articles_select").on('change', function (e) {
        let select = document.getElementById("articles_select");
        window.location.replace(window.location.origin + "/articles/" + select.options[select.options.selectedIndex].id.toString());
    });
});
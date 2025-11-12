// ToDo удалить если не используется
/*$('.show_comment').on('click', function() {
    alert("CLICK!");
    $(this).toggleClass('active');
    $(this).find('i').toggleClass('rotate180');
    $(this).parent().parent().find('.comments_block').slideToggle();
});*/

// ToDo удалить если не используется
// For dynamically add
// $(document).ready(function () {
//     $(document).on("click", ".show_comment", function () {
//         let src = $(this).data('src');
//         let review = get_review(this, src);
//
//         let slider = review.find(".comment_slider");
//         slider.toggleClass('active');
//         slider.find('img').toggleClass('rotate180');
//
//         review.find('.comments_block').slideToggle();
//     });
// });

function get_review(element, source) {
    switch (source) {
        case "slider":
            return $(element).parent().parent();
        case "counter":
            return $(element).parent().parent().parent().parent();
    }
    return null;
}

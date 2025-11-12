$(document).ready(function () {
    $(document).on("click", ".user_review", function (e) {
        e.preventDefault();
    });

    $(document).on("click", ".rateable", function (e) {
        e.preventDefault();
        let link = $(this);
        let url = link.data('url');

        let rate_block = link.parent();
        let like_btn = rate_block.find(".like_btn");
        let like_counter = like_btn.find(".col_idea");
        let like_active = "m_green";

        let dislike_btn = rate_block.find(".dislike_btn");
        let dislike_counter = dislike_btn.find(".col_idea");
        let dislike_active = "m_red";

        $.ajax({
            type: 'post',
            url: url,
            data: {
                'csrfmiddlewaretoken': window.CSRF_TOKEN // from index.html
            },
            success: function (data) {
                // Change like state
                if (data.liked_delta !== 0) {
                    like_btn.toggleClass(like_active);  // change like push
                    like_counter.html(parseInt(like_counter.html()) + data.liked_delta);    // change like counter
                }
                // Change dislike state
                if (data.disliked_delta !== 0) {
                    dislike_btn.toggleClass(dislike_active);    // change dislike push
                    dislike_counter.html(parseInt(dislike_counter.html()) + data.disliked_delta); // change dislike counter
                }
                // Notify if rating sort
                if (data.is_rating_sort) {
                    let message_block = $(".messages_block");
                    if (message_block.find(".alert").length === 0) {
                        let message = "Требуется перезагрузка страницы для перерасчета рейтинга";
                        let message_DOM = "<div class='alert success'><span class='closebtn'>&times;</span>" + message + "</div>";

                        message_block.append(message_DOM);
                    }
                }
            },
            error: function (xhr, status, error) {
                console.log("Ошибка во время оценивания отзыва! Попробуйте позже")
            }
        });
    });
});
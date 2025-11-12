$(document).ready(function () {
    //скролл в анализе портфеля
    let url = window.location.href;
        if (url.toString().indexOf("analyze_portfolio") !== -1) {
            $('html, body').animate({
                scrollTop: $('#analyze_href').offset().top
            });
        }

    // alert($('body').width());
    if ($('body').width() > 1200) {
        if ($("*").is(".left_cat_sidebar")) {

            lsh = $('.left_cat_sidebar').offset().top;

            $(document).scroll(function () {
                if ($(this).scrollTop() > lsh) {
                    $('.left_cat_sidebar>div').addClass('lcs_fix');
                } else {
                    $('.left_cat_sidebar>div').removeClass('lcs_fix');
                }
            });

        }
    }

    // ToDo разобраться что делает скрипт
    $('.toogle_link').on('click', function () {
        $(this).parent().find('.sub_toggle').slideToggle();
        $(this).find('.rotate90').toggleClass('true');
    });

    $('.modal_close').on('click', function () {
        $(this).parent().hide('');
    });

    $('.error_backtest').on('click', function () {
        $.magnificPopup.close();
    });

    $('.table_line>i').on('click', function () {
        $(this).toggleClass('active');
    });

    $(".selectBox ul[data-name='operation_type'], .selectBox ul[data-name='asset_class']").on('click', 'li.option', function () {
        let $p = $(this).parent().parent().find('p.valueTag');
        $p.text($(this).text());
        $p.attr("data-value", $(this).data("value"));
        let asset_class = $("p[data-name='asset_class']").text();
        let operation_type = $("p[data-name='operation_type']").text();
        if ($p.attr("data-name") === 'asset_class') {
            updateOperationTypes(asset_class);
            $("#add_operation input[name='asset']").val("");
        } else if ($p.attr("data-name") === 'operation_type') {
            updateFormFields(asset_class, operation_type);
        }
        resetAddOperationFormValues();
    });

    $('.selectBox').on('click', function () {
        // if (!$(this).hasClass('сurrency')) {
        if ($(this).hasClass('bblr')) {
            $(this).find('.selectMenuBox').slideToggle();
            $(this).toggleClass('bblr');
        } else {
            $(this).parents('body').find('.selectMenuBox').hide();
            $(this).parents('body').find('.bblr').removeClass('bblr');
            $(this).find('.selectMenuBox').slideToggle();
            $(this).toggleClass('bblr');
        }
        // }
    });

    //navigation left sidebar
    $('.js-sidebar_item_title').on('click', function () {
        if ($(this).hasClass('active')) {
            $(this).parent().parent().find('.js-sidebar_item_title.active').removeClass('active');
            // $(this).parent().parent().find('.sub_sidebar_item.open').slideToggle().removeClass('open');
        } else {
            $(this).parent().parent().find('.js-sidebar_item_title.active').removeClass('active');
            // $(this).parent().parent().find('.sub_sidebar_item.open').slideToggle().removeClass('open');
            $(this).addClass('active');
        }
    });

    $('.js-sidebar_item_dropdown').on('click', function () {
        $(this).parent().find('.sub_sidebar_item').slideToggle().addClass('open');
        $(this).toggleClass('active');
    });

    $('.js-sidebar_item_dropdown.active').on('click', function () {
        $(this).addClass('show');
    });
    // end navigation left sidebar

    $('.acc_title').on('click', function () {
        if ($(this).hasClass('active')) {
            $(this).parent().parent().find('.acc_title.active').removeClass('active');
            $(this).parent().parent().find('.sub_acc_item.open').slideToggle().removeClass('open');
            $(this).find('img').removeClass('true');
        } else {
            $(this).parent().parent().find('.acc_title.active').removeClass('active');
            $(this).parent().parent().find('.sub_acc_item.open').slideToggle().removeClass('open');
            $(this).parent().parent().find('img').removeClass('true');
            $(this).addClass('active');
            $(this).find('img').addClass('true');
            $(this).parent().find('.sub_acc_item').slideToggle().addClass('open');
        }

    });

    /***************************************** *************************************/
    /************************************ DATEPICKER BLOCK ***************************/
    /***************************************** ************************************/
    $(function () {
        let date = new Date();
        let end_year = date.getFullYear();
        let year_range = "1999" + ":" + String(end_year);
        var today = new Date();
        let start_date = new Date(1999, 10, 31);
        // backtest datepicker
        $("#end_date, #start_date").datepicker({
            // disable non working days
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            },
            minDate: start_date,
            maxDate: today,
            firstDay: 1,
            yearRange: year_range,
            changeYear: true,
            changeMonth: true,
            selectOtherMonths: true,
            showOtherMonths: true,
            dateFormat: "dd-mm-yy",
            dayNames: ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
            dayNamesShort: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
            dayNamesMin: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
            monthNames: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
            monthNamesShort: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
        });

        // account datepicker (add operation)
        $("#operation_date, #add_portfolio_operation_date").datepicker({
            // disable non working days
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            },
            minDate: start_date,
            maxDate: today,
            firstDay: 1,
            yearRange: year_range,
            changeYear: true,
            changeMonth: true,
            selectOtherMonths: true,
            showOtherMonths: true,
            dateFormat: "dd-mm-yy",
            dayNames: ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
            dayNamesShort: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
            dayNamesMin: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
            monthNames: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
            monthNamesShort: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
        });

        let url = window.location.href;
        if (url.toString().indexOf("analyze_portfolio") === -1) {
            $("#start_date").datepicker("setDate", -210); // last day for which information
            $("#end_date").datepicker("setDate", -2); // optimal period for calculating all possible information4
        }
        // $account.datepicker("setDate", -32); // optimal period for calculating all possible information TODO: change after library update
    });


    // добавляем/показываем меню авторизации пользователя на мобилах
    $(function () {
        $('.js-av-auth-show').click(function (e) {
            e.preventDefault();
            $(this).toggleClass('active');
            $('.header_hamburger').removeClass('show');
            $('.header_hamburger .mobile_menu_btn').show();
            $('.header_hamburger .mobile_menu_btn_close').hide();
            $.magnificPopup.close();
        });
    });

    // на мобиле добавляю класс для фиксирования body
    $(window).on('load ready resize', function () {
        if ($(window).width() < '768') {
            $(document).on('click', '.js-av-auth-show', function(e) {
                e.preventDefault();
                $('body').removeClass('body-fixed');
            });
            $(document).on('click', '.js-av-auth-show.active', function(e) {
                e.preventDefault();
                $('body').addClass('body-fixed');
            });
        }
    });

    $('.js-tooltip').tooltipster({
        contentCloning: true,
        animation: 'fade',
        delay: 0,
        theme: 'tooltipster-shadow b-tooltip-menu',
        contentAsHTML: true,
        interactive: true,
        distance: 13,
        maxWidth: '400',
        trigger: 'custom',
        triggerOpen: {
            mouseenter: true,
            tap: true
        },
        triggerClose: {
            mouseleave: true,
            tap: true
        },
        side:  ['bottom', 'top'],
        // trigger: 'ontouchstart' in window || navigator.maxTouchPoints ? 'click' : 'hover'
    });

    // взрываем модальное окно справа
    // авторизация - регистрация и пр
    $(function() {
        var startWindowScroll = 0;
        $('.js-modal').magnificPopup({
            type: 'inline',
            removalDelay: 300,
            midClick: true,
            mainClass: 'b-modal',
            fixedContentPos: true,
            fixedBgPos: true,
            overflowY: 'auto',
            closeBtnInside: true,
            showCloseBtn: true,
            callbacks: {
                beforeOpen: function () {
                    startWindowScroll = $(window).scrollTop();
                },
                open: function () {
                    if ($('.mfp-content').height() < $(window).height()) {
                        $('body').on('touchmove', function (e) {
                            e.preventDefault();
                        });
                    }
                },
                close: function () {
                    $(window).scrollTop(startWindowScroll);
                    $('body').off('touchmove');
                }
            }
        });
    });

    // взрываем мобильное меню
    $(function() {
        var startWindowScroll = 0;
        $('.js-modal-menu').magnificPopup({
            type: 'inline',
            midClick: true,
            mainClass: 'b-modal-menu',
            fixedContentPos: true,
            fixedBgPos: true,
            overflowY: 'auto',
            closeBtnInside: true,
            showCloseBtn: false,
            callbacks: {
                beforeOpen: function () {
                    startWindowScroll = $(window).scrollTop();
                },
                open: function () {
                    if ($('.mfp-content').height() < $(window).height()) {
                        $('body').on('touchmove', function (e) {
                            e.preventDefault();
                        });
                    }
                },
                close: function () {
                    $(window).scrollTop(startWindowScroll);
                    $('body').off('touchmove');
                    $('.header_hamburger').removeClass('show');
                    $('.header_hamburger .mobile_menu_btn').show();
                    $('.header_hamburger .mobile_menu_btn_close').hide();
                }
            }
        });
    });

    $(document).on('click', '.js-modal-menu-close', function(e) {
        e.preventDefault();
        $.magnificPopup.close();
        $('.header_hamburger').removeClass('show');
    });

    // взрываем модальное окно по центру
    $(function() {
        var startWindowScroll = 0;
        $('.js-modal-inner').magnificPopup({
            type: 'inline',
            midClick: true,
            mainClass: 'b-modal-inner',
            fixedContentPos: true,
            fixedBgPos: true,
            overflowY: 'auto',
            closeBtnInside: true,
            showCloseBtn: true,
            callbacks: {
                beforeOpen: function () {
                    startWindowScroll = $(window).scrollTop();
                },
                open: function () {
                    if ($('.mfp-content').height() < $(window).height()) {
                        $('body').on('touchmove', function (e) {
                            e.preventDefault();
                        });
                    }
                },
                close: function () {
                    $(window).scrollTop(startWindowScroll);
                    $('body').off('touchmove');
                }
            }
        });
    });

    //открываю меню гамбургера
    $('.mobile_menu_btn').on('click', function (e) {
        e.preventDefault();
        $(this).hide();
        $('.js-av-auth-show').removeClass('active');
        $('.header_hamburger .mobile_menu_btn_close').show();
    });

    //закрываю меню гамбургера
    $('.mobile_menu_btn_close').on('click', function (e) {
        e.preventDefault();
        $('.header_hamburger .mobile_menu_btn').show();
        $('.header_hamburger .mobile_menu_btn_close').hide();
    });

    //для бэграунда когда меню гамбургера открыто
    $('.header_hamburger').on('click', function (e) {
        e.preventDefault();
        $(this).toggleClass('show');
    });

    //при открытом меню гамбургера переход
    //в личный кабинет
    $('.mobile_menu_btn_out').on('click', function (e) {
        e.preventDefault();
        $('.header_hamburger .mobile_menu_btn').show();
        $('.header_hamburger .mobile_menu_btn_close').hide();
        $('.header_hamburger').removeClass('show');
    });

});

function start_preloader (){
    $.magnificPopup.close();
    let preloader = $("#page-preloader");
    preloader.removeClass("hide");
}

function stop_preloader (){
    let preloader = $("#page-preloader");
    preloader.addClass("hide");
}
$(function () {
    //устанавливаем маски для дат
    $('#start_date').mask('99-99-9999');
    $('#end_date').mask('99-99-9999');

    //смена даты
    $("#start_date").on('change', function (e) {
        e.preventDefault();
        let id = "start_date";
        if (validate_date(id)) {
            $(this).css({'border' : '1px solid red'});
        }
        else {
            $(this).css({'border' : '1px solid #686c7a'});
        }
    });

    $("#end_date").on('change', function (e) {
        e.preventDefault();
        let id = "end_date";
        if (validate_date(id)) {
            $(this).css({'border' : '1px solid red'});
        }
        else {
            $(this).css({'border' : '1px solid #686c7a'});
        }
    });
    /***************************************** ************************************/
    /************************************ ADD ASSET *******************************/
    /***************************************** ************************************/
    // From common.js
    $(document).on('click', '.add_activs', function (e) {
        console.log("клик");
        e.preventDefault();
        let fields_amount = $(".assets_fields .zoom_line").length;
        let me = this;
        if (fields_amount < 16) {         // If amount of fields not more than 50
            $.ajax({
                type: 'post',
                url: '/backtest/ajax/add_asset/',
                data: {
                    'csrfmiddlewaretoken': window.CSRF_TOKEN // from index.html
                },
                success: function (data) {
                    $(".assets_fields").append(data.asset);
                    $(".shares_fields").append(data.share);

                    if ($(".assets_fields .zoom_line").length >= 16) {
                        $(me).hide();
                    }
                },
            });
        }

    });
    /***************************************** ************************************/
    /************************************ REMOVE ASSET ****************************/
    /***************************************** ************************************/
    $(document).on("click", '.sd_line_3 .zoom_line img.remove_asset', function () {
        let fields_amount = $(".assets_fields .zoom_line").length;
        if (fields_amount > 1) {         // If exist more than one asset field
            // Get asset and corresponding share fields
            let asset_field = $(this).parent();
            let index = asset_field.index();
            let share_field = asset_field.parents(".sd_line_3").find(".shares_fields").children().eq(index);
            // Remove share value from total
            let share_value = share_field.find("input").val();
            let total_share = $("#total_share");
            total_share.val(parseFloat(total_share.val()) - share_value).trigger("change");
            // Remove fields
            remove(asset_field);
            remove(share_field);
        }

        $(".add_activs").show();
    });

    function remove(element) {
        element.hide("slow");
        setTimeout(function () {
            element.remove()
        }, 500);
    }

    /***************************************** ************************************/
    /************************************ SELECT ASSET ****************************/
    /***************************************** ************************************/
    let source_input = null;
    let cache_options = get_options();

    function get_options() {
        let results = null;
        $.ajax({
            async: false,
            type: 'get',
            url: "/backtest/ajax/select_box/",
            data: {
                'csrfmiddlewaretoken': window.CSRF_TOKEN, // from index.html
            },
            success: function (data) {
                results = data
            },
        });
        return results;
    }

    // Set source_input to fill
    function set_source_input(element) {
        source_input = element;
    }

    // Открытие модального окна для выбора актива через поиск
    $(document).on("click", '.zoom_line img.search_asset', function () {
        // hide currency selector
        $.magnificPopup.open({
                        mainClass: 'b-modal-inner',
                        items: {
                            src: '#modal_add_active'
                        },
                        type: 'inline'
                    }, 0);
        let currency_selector = $("#currency_selectBox");
        if (currency_selector.hasClass("bblr")) {
            currency_selector.trigger('click');
        }
        // set source input
        let input = $(this).parent().find("input");
        set_source_input(input);
        // modal settings
        let modal = $('#modal_add_active');
        modal.find("p.valueTag").html("Тип актива");    // reset valueTag
        modal.find("input").val("").data("type", input.data("type"));   // set input-type and reset input.val
        $("#select_assets").empty().append(cache_options[input.data("type")]);  // append data for selectBox
    });

    // Открытие модального окна для сравнения актива
    $(document).on("click", '#compare_pointer', function () {
        // hide currency selector
        let currency_selector = $("#currency_selectBox");
        if (currency_selector.hasClass("bblr")) {
            currency_selector.trigger('click');
        }
        // set source input
        let input = $(this).parent().find("input");
        set_source_input(input);
        // modal settings
        let modal = $('#modal_compare_asset');
        modal.find("p.valueTag").html("Тип актива");    // reset valueTag
        modal.find("input").val("").data("type", "assets");   // set input-type and reset input.val
        $("#select_assets").empty().append(cache_options["assets"]);  // append data for selectBox
    });

    // ajax выбор актива для сравнения
    $("#modal_compare_button").click(function (e) {
        e.preventDefault();
        // submit selection
        let selected_asset = document.getElementById("compare_search_input");

        //Получаем данные с глобальной переменной backtest_analyze_data для сравнения выбранного актива
        let benchmark = backtest_analyze_data.benchmark_ticker;
        let exchange = backtest_analyze_data.benchmark_exchange;
        let start_date = backtest_analyze_data.input_start_date;
        let end_date = backtest_analyze_data.input_end_date;
        let currency = backtest_analyze_data.currency;
        let asset = selected_asset.value;
        let data_pk = selected_asset.getAttribute("data-pk");

        if (asset) {
            let data = {"benchmark": benchmark,
                    "exchange": exchange,
                    "data_pk": data_pk,
                    "start_date": start_date,
                    "end_date": end_date,
                    "currency": currency,};

            $.ajax({
                async: true,
                type: "GET",
                url: '/backtest/ajax/ajax_compare/',
                data: data,
                contentType: 'json',
                beforeSend: function(){
                     start_preloader();
                },
                success: function (data) {
                    if (data.is_success) {
                        stop_preloader();
                        document.getElementById("compare_asset").innerText = data.asset;
                        document.getElementById("gagr").innerText = data.gagr;
                        document.getElementById("vol").innerText = data.vol;
                        document.getElementById("sharp").innerText = data.sharp;
                        document.getElementById("alpha").innerText = data.alpha;
                        document.getElementById("beta").innerText = data.beta;
                        document.getElementById("cor").innerText = data.cor;
                        document.getElementById("r_square").innerText = data.r_square;
                        success();
                    }
                    else {
                        stop_preloader();
                        document.getElementById("error_backtest_p").innerText = data.error_text;
                        document.getElementById("error_backtest_title").innerText = "Ошибка при анализе актива";
                        $.magnificPopup.open({
                            mainClass: 'b-modal-inner',
                            items: {
                                src: '#error_backtest_modal'
                            },
                            type: 'inline'
                        }, 0);
                        success();
                    }
                }
            });
            function success (){
                let compare_error_div = document.getElementById("compare_error_div");
                let compare_error_span = document.getElementById("compare_error_span");
                document.getElementById("compare_search_input").style.border = "1px solid #686c7a";
                let compare_error_input = document.getElementById("compare_search_input");
                compare_error_div.innerHTML = "";
                compare_error_div.appendChild(compare_error_span);
                compare_error_div.appendChild(compare_error_input);
                document.getElementById("compare_error_message").style.display = "none";
                selected_asset.setAttribute("data-pk", "");
                selected_asset.value = "";
                selected_asset.setAttribute("data-filter", "");
            }
        }
        else {
            let compare_error_div = document.getElementById("compare_error_div");
            let compare_error_span = document.getElementById("compare_error_span");
            document.getElementById("compare_search_input").style.border = "1px solid #c62f43";
            let compare_error_input = document.getElementById("compare_search_input");
            compare_error_div.innerHTML = "";
            compare_error_div.appendChild(compare_error_span);
            compare_error_div.appendChild(compare_error_input);
        }
    });

    $("#compare_close_btn").on('click', function (e) {
        document.getElementById("compare_error_message").style.display = "none";
    });

    // Switch to input
    $('.modal_content .selectBox').on('click', function () {
        let link = $(this);
        let input = link.parents(".modal_content").find("input");

        if (link.hasClass("bblr")) {
            input.prop('disabled', true);
        } else {
            input.prop('disabled', false);
        }
    });

    // Выбор типа актива в модальных окнах сравнения и выбора актива
    $(document).on('click', ".modal_add_active li.option", function () {
        let link = $(this);
        let $p = link.parent().parent().find('p.valueTag');
        let input = link.parents(".modal_content").find("input");
        $p.text($(this).text());
        input.attr("data-filter", link.data("value"));
        input.val("");
    });

    // Выбор актива в модальном окне выбора актива
    $("#modal_add_active #modal_submit_button").on('click', function (e) {
        e.preventDefault();
        // submit selection
        let selected_asset = $(this).parent().parent().find("input");
        if (selected_asset.attr("data-pk")) {
            source_input[0].setCustomValidity("");
            source_input.data("pk", selected_asset.attr("data-pk"));
            source_input.val(selected_asset.val());
            if (selected_asset.val() !== "")
                enable_share_field(source_input.parent()[0]);
        }
        // clean form, close modal
        selected_asset.data("pk", "");
        selected_asset.val("");
        selected_asset.attr("data-filter", "");
        $.magnificPopup.close();
    });

    //блокирования поля доли, если соответствующее ему поле актива стало пустой
    $("input[name='asset']").blur(function () {
        if ($(this)[0].value == "")
            disable_share_field($(this).parent()[0]);
    });

    //смена бенчмарка при смене валюты
    $(".currency_option").on('click', function () {
        let benchmark_select = $('.benchmarks_data')
        let benchmark_input = $('#benchmark_input');
        let benchmark_value;
        if ($(this).html() == "RUB")
            benchmark_value = "MOEX Russia Index";
        else
            benchmark_value= "S&P 500 TR (Total Return)";

        for (let i=0; i<benchmark_select.length; i++){
            if (benchmark_value == benchmark_select[i].innerText)
            {
                benchmark_input.val(benchmark_value);
                benchmark_input.attr("data-pk", benchmark_select[i].getAttribute("data-pk"));
                $('#benchmark_p').html(benchmark_value);
            }
        }
    });

    //смена значений бенчмарка
    $(".change_portfolio li.option").on('click', function () {
        let link = $(this);
        let input = link.parent().parent().find("input");
        let p = link.parent().parent().find("p");
        p.html(link.html());
        input.attr("data-pk", link.attr("data-pk"));
        input.val(link.text());
    });

    //смена значений валюты и ребалансировки
    $(".sd_line_1 li.option").on('click', function () {
        let link = $(this);
        let input = link.parent().parent().find("input");
        let p = link.parent().parent().find("p");
        p.text(link.html());
        if (link.parent().parent()[0].id === "rebalancing_selectBox")
            input.val(link[0].id.toString());
        else
            input.val(link.html());
    });
});

//Добавление id бенчмарка к форме бэктеста
function validate_submit_backtest() {
    let form = $("#sd_form");
    let benchmark_value = form.find("input[name='benchmark']").attr("data-pk");
    let benchmark = $("<input>")
        .attr("type", "hidden")
        .attr("name", "benchmark").val(benchmark_value);
    form.append(benchmark);
    let assets_input = document.getElementsByName("asset");
    for (let i=0; i<assets_input.length; i++) {
        if (assets_input[i].value==="") {
            assets_input[i].setAttribute("disabled", "true");
            assets_input[i].value="";
        }
    }
    return true;
}

function validate_date(id) {
    let date = $("#"+id.toString()).datepicker("getDate");
    let now = new Date();
    let tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate()+1);
    return (date>=tomorrow);
}

function enable_share_field(source_div) {
    let input = find_share_field(source_div);
    input.classList.remove("opacity");
    input.classList.remove("disabled-input");
    input.setAttribute("required", "true");
    input.removeAttribute("disabled");
}

function disable_share_field(source_div) {
    let input = find_share_field(source_div);
    input.classList.add("opacity");
    input.classList.add("disabled-input");
    input.setAttribute("required", "false");
    input.setAttribute("disabled", "true");
    input.value = "";
    let sum = sum_shares();
    $("#total_share").val(sum).trigger("change");
}

function find_share_field(source_div) {
    let asset_fields = document.getElementsByClassName("custom");
    let asset_index = 0;
    for (let i=0; i<asset_fields.length; i++) {
        if (source_div === asset_fields[i])
            asset_index = i;
    }
    let share_fields = document.getElementsByClassName("share_field");
    return share_fields[asset_index].children[0];
}

function risk_profile_colors() {
    let risk_profile_number = backtest_analyze_data.risk_profile_number;
    for (let i=1; i<parseInt(risk_profile_number)+1; i++) {
                    document.getElementById("circle" + i.toString()).setAttribute("stroke", "url(#linear-gradient6)");
                }
}
risk_profile_colors();
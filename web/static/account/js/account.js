function updateOperationTypes(asset_class) {
    var $operation_types;
    let $operation_type = $("ul[data-name='operation_type']");
    $operation_type.find("li").css("display", "none");
    let $p = $operation_type.parent().find('p.valueTag');
    let $asset_field = $("input[name='asset']");
    if (asset_class === "денежные средства") {
        $operation_types = $operation_type.find("li[data-type='cash']");
        $operation_types.css("display", "block");
        let active_operation = $operation_types.first();
        $p.text(active_operation.text());
        $p.attr("data-value", active_operation.attr("data-value"));
        if (active_operation === "пополнение" || active_operation === "вывод") {
            $asset_field.attr("data-filter", "CS");
        } else if (active_operation === "покупка" || active_operation === "продажа") {
            $asset_field.attr("data-filter", "FX");
        }

    } else {
        $operation_types = $operation_type.find("li[data-type='asset']");
        $operation_types.css("display", "block");
        $p.text($operation_types.first().text());
        $p.attr("data-value", $operation_types.first().attr("data-value"));
        if (asset_class === "акция") {
            $asset_field.attr("data-filter", "ST");
        } else if (asset_class === "ETF") {
            $asset_field.attr("data-filter", "ET");
        }
    }
    updateFormFields(asset_class, $operation_types.first().text())
}

function resetAddOperationFormValues() {
    $("#add_operation input[name='count']").val("");
    $("#add_operation input[name='cost']").val("");
    $("#add_operation input[name='price']").val("");
}


$(document).ready(function () {
    $('#operation_date').mask('99-99-9999');
    $('#add_portfolio_operation_date').mask('99-99-9999');

    //функция сейчас неиспользуется, т.к. поменяли функционал анализа, но пусть останется здесь
    function validate_operation_date() {
        let date = $("#operation_date").datepicker("getDate");
        let date_now = new Date().setHours(0, 0, 0, 0);
        let difference_days = ((date_now - date) / 1000) / 86400;
        let date_valid = difference_days >= 32;
        set_validity($("#operation_date")[0], date_valid, "Невозможно проанализировать портфель с периодом существования менее 1 месяца. ");
    }

    //ajax запрос для получения сведений о портфеле при открытии окна настроек портфеляя
    $("#myTab_bags a i.change").on('click', function (e) {
        e.preventDefault();
        let portfolio = $(this).parent("a").data("portfolio");
        let data = {"csrfmiddlewaretoken": window.CSRF_TOKEN,
                    "portfolio": portfolio,};
        $.ajax({
            async: false,
            type: "GET",
            url: '/account/ajax/get_portfolio_params/',
            data: data,
            contentType: 'json',
            success: function (data) {
                $("input[id='change_portfolio_name']").val(data.portfolio_name);
                $("#change_portfolio_currency_p").html(data.currency);
                $("#change_portfolio_currency_input").val(data.currency);

                $("#change_portfolio_benchmark_p").html(data.benchmark_name);
                $("#change_portfolio_benchmark_input").val(data.benchmark_name);
                $("#change_portfolio_benchmark_input").attr("data-pk", data.benchmark_pk);

                $("input[id='change_portfolio_pk']").val(data.portfolio_pk);
            }
        });
    });

    //Нажатие кнопки нет в модальном окне удаления операции
    $("#no_delete_operation").on('click', function (e) {
        $.magnificPopup.close();
    });

    //удаление портфеля
    $("#portfolio_delete_href").on('click', function (e) {
        let button = $("#portfolio_delete_href");
        if (!button.attr("disabled")) {
            e.preventDefault();
            let portfolio = $("input[id='change_portfolio_pk']").val();
            let url = window.location.origin + "/account/portfolios/" + portfolio + "/delete/";
            let data = {"csrfmiddlewaretoken": window.CSRF_TOKEN};
            $.post(url, data, function () {
                window.location.replace(window.location.origin + '/account/');
            })
        }
        start_preloader();
    });

    //Заполнение модального окна с подверждением удаления операции
    $("i[data-name='operation_history']").click(function (e) {
        e.preventDefault();
        let id = $(this).data("id");
        $('#delete_operation_confirm_href').attr("data-pk", id.toString());
    });

    //удаление операции ajax
    $("#delete_operation_confirm_href").click(function (e) {
        e.preventDefault();
        let id = $('#delete_operation_confirm_href').attr("data-pk");
        let data = {"csrfmiddlewaretoken": window.CSRF_TOKEN,
                    "operation_id":id};
        let portfolio = $("#myTab_bags li.active a").data("portfolio");
        $('#delete_operation_confirm_modal').hide();
        $.ajax({
            async: true,
            type: "GET",
            url: '/account/ajax/ajax_delete_operation/',
            data: data,
            contentType: 'json',
            beforeSend: function(){
                start_preloader();
            },
            success: function (data) {
                if (data.delete_error) {
                    document.getElementById("error_delete").innerHTML = data.delete_error.toString();
                    stop_preloader();
                    $.magnificPopup.open({
                        mainClass: 'b-modal-inner',
                        items: {
                            src: '#delete_operation_modal'
                        },
                        type: 'inline'
                    }, 0);
                }
                else {
                    window.location.replace(window.location.origin + "/account/portfolios/" + portfolio + "/operations/");
                }
            }
        });
    });

    //автоматическое заполнение поля стоимость в окне добавления транзакции
    $("input[name='count'], input[name='price']").change(function () {
        let count = $("input[name='count']").val();
        let price = $("input[name='price']").val();
        if (count && price) {
            let cost = count * price;
            $("input[name='cost']").val(cost.toFixed(4))
        }
    });

    //переход на страницу анализа портфеля
    $('#tab2-tab_bag_1').on('click', function (e) {
        e.preventDefault();
        let portfolio = $("#myTab_bags li.active a").data("portfolio");
        window.location.href = window.location.origin + "/account/portfolios/" + portfolio + "/analyze/";
    });

    //валидация даты (подсвечивание красным) при смене значения даты
    $("#operation_date, #add_portfolio_operation_date").on('change', function (e) {
        e.preventDefault();
        let id = $(this)[0].id.toString();
        let parent = $(this).parent("div");
        if (!account_validate_date(id)) {
            parent.css({'border' : '1px solid red'});
        }
        else {
            parent.css({'border' : '1px solid #686c7a'});
        }
    });

    //смена значений бенчмарка и валюты в окнах добавления и изменения портфеля
    $(".change_portfolio li.option").on('click', function () {
        let link = $(this);
        let input = link.parent().parent().find("input");
        let p = link.parent().parent().find("p");
        p.html(link.html());
        //если выбираем бенчмарк, то дополнительно необходимо добавить атрибут data-pk в скрытый инпут
        if (link.parent().parent()[0].id === "benchmark_selectBox")
            input.attr("data-pk", link.attr("data-pk"));
        input.val(link.text());
    });

    //смена бенчмарка при смене валюты
    $(".currency_option").on('click', function () {
        let form = $(this).parent().parent().parent().parent();
        let benchmark_input = form.find("input[name='benchmark']")
        let benchmark_p;

        if (form.attr("id")=="change_portfolio_form")
            benchmark_p = $('#change_portfolio_benchmark_p');
        else
            benchmark_p = $('#add_portfolio_benchmark_p');

        let benchmark_select = $('.benchmarks_data')
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
                benchmark_p.html(benchmark_value);
                break;
            }
        }
    });
});

//функция валидации даты
function account_validate_date(id) {
    let date = $("#"+id.toString()).datepicker("getDate");
    let now = new Date();
    let tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate()+1);
    let start = new Date(1999, 11, 31);
    return (date<tomorrow && date>start);
}

function add_portfolio_validate_cost() {
    let cost = $("#add_portfolio_asset_cost");
    if (cost.val() === "") {
        cost[0].style.border = "1px solid red";
        return false;
    }
    else {
        cost[0].style.border = "1px solid #686c7a";
        return true;
    }
}

//обновление полей при смене типа операции
function updateFormFields(asset_class, operation_type) {
    let $count = $("#add_operation input[name='count']");
    let $price = $("#add_operation input[name='price']");
    let $cost = $("#add_operation input[name='cost']");
    let asset = $("p[data-name='asset_class']").text();
    if (operation_type === "пополнение" || operation_type === "вывод" || operation_type === "дивиденд") {
        if (asset === "денежные средства") {
            $("input[name='asset']").attr("data-filter", "CS");
            if ($("input[name='asset']").val() == "USDRUB (FOREX: USDRUB)") {
                $("input[name='asset']").val("");
            }
        }
        $cost.attr("disabled", false);
        $price.attr("disabled", true);
        $count.attr("disabled", true);
        $price.addClass("disabled-input opacity");
        $count.addClass("disabled-input opacity");
        $cost.removeClass("disabled-input", false);
    } else {
        if (asset === "денежные средства") {
            $("input[name='asset']").attr("data-filter", "FX");
            if ($("input[name='asset']").val() == "Russian Ruble (FOREX: RUB)" ||
            $("input[name='asset']").val() == "United States Dollar (FOREX: USD)") {
                $("input[name='asset']").val("");
            }
        }
        $cost.attr("disabled", true);
        $price.attr("disabled", false);
        $count.attr("disabled", false);
        $price.removeClass("disabled-input opacity");
        $count.removeClass("disabled-input opacity");
        $cost.addClass("disabled-input");
    }
}

//Валидация формы добавления операции
function validate_add_operation () {
    let $form = $("#add_operation");
    let count = $("input[name='count']").val();
    let price = $("input[name='price']").val();
    let cost = $("input[name='cost']").val();
    let asset = $("input[name='asset']").val();
    let date = $("input[name='date']").val();
    let invalid = "false";
    let operation_type = $("#operation_type").html();
    if (operation_type === "пополнение" || operation_type === "вывод" || operation_type === "дивиденд") {
        if (asset!=="" && cost!=="" && date!=="" && account_validate_date("operation_date")){
            invalid = "true";
        }
    }
    else
    {
        if (asset!=="" && cost!=="" && count!=="" && price!=="" && date!=="" && account_validate_date("operation_date")){
            invalid = "true";
        }
    }
    if (invalid === "true") {
        let operation_type_value = $form.find("p[data-name='operation_type']").data("value");
        let asset_value = $form.find("input[name='asset']").attr("data-pk");
        let portfolio_value = $("#myTab_bags li.active a").data("portfolio");
        let operation_type = $("<input>")
            .attr("type", "hidden")
            .attr("name", "operation_type").val(operation_type_value);
        let portfolio = $("<input>")
            .attr("type", "hidden")
            .attr("name", "portfolio").val(portfolio_value);
        let asset = $("<input>")
            .attr("type", "hidden")
            .attr("name", "asset").val(asset_value);
        $form.find("input[name='asset']").attr("disabled", "disabled");
        $form.find("input[name='cost']").attr("disabled", false);
        $form.append(operation_type);
        $form.append(portfolio);
        $form.append(asset);
        start_preloader();
        return true;
    }
    else return false;
}

//Валидация формы добавления портфеля
function validate_add_portfolio () {
    let date = $("#add_portfolio_operation_date").val();
    let cost = $("#add_portfolio_asset_cost").val();
    let parent = $("#add_portfolio_operation_date").parent("div");

    function add_benchmark_id_to_form() {
        let form = $("#add_portfolio_form");
        let benchmark_value = form.find("input[name='benchmark']").attr("data-pk");
        let benchmark = $("<input>")
            .attr("type", "hidden")
            .attr("name", "benchmark").val(benchmark_value);
        form.append(benchmark);
        let button = form.find(".blue_btn");
        button.attr("disabled", "true");
        button[0].style.opacity = 0.4;
    }

    if (date!=="" || cost!=="") {
        if (date === "") {
            parent.css({'border' : '1px solid red'});
            return false;
        }
        if (add_portfolio_validate_cost() && account_validate_date("add_portfolio_operation_date")) {
            add_benchmark_id_to_form();
            start_preloader();
            return true;
        }
        else return false;
    }
    else {
        add_benchmark_id_to_form();
        parent.css({'border': '1px solid #686c7a'});
        $("#add_portfolio_asset_cost").css({'border': '1px solid #686c7a'});
        start_preloader();
        return true;
    }
}

//Валидация формы изменения портфеля
function validate_change_portfolio() {
    let form = $("#change_portfolio_form");
    let benchmark_value = form.find("input[name='benchmark']").attr("data-pk");
    let benchmark = $("<input>")
        .attr("type", "hidden")
        .attr("name", "benchmark").val(benchmark_value);
    form.append(benchmark);
    let button = form.find(".blue_btn");
    button.attr("disabled", "true");
    button[0].style.opacity = 0.4;
    button[1].style.opacity = 0.4;
    start_preloader();
    return true;
}
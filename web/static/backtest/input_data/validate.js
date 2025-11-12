/**************************** ELEMENTS **********************/
let total_share = $("#total_share");
let input_share = "input[name='share']";

/**************************** VALIDATORS *******************/
// SHARES
function    validate_shares() {
    let are_valid_shares = parseFloat(total_share.val()) > 0 && parseFloat(total_share.val()) <= 100;
    set_validity(total_share[0], are_valid_shares, "Суммарная доля активов должна больше 0 и меньше 100");
}

// DATES
function validate_dates() {
    let date_1 = $( "#start_date" ).datepicker( "getDate" );
    let date_2 =  $( "#end_date" ).datepicker( "getDate" );
    let date_now = Date.now();
    let difference_days = ((date_now - date_2) / 1000) / 86400;
    let period_length = ((date_2 - date_1) / 1000) / 86400;
    let are_valid_dates = date_2 >= date_1 && difference_days > 2 && period_length > 32;
    set_validity($("#end_date")[0], are_valid_dates, "Конечная дата должна быть больше начальной даты и меньше даты сегодняшнего дня. Минимальная длина периода - 1 месяц");
}

/**************************** WATCHERS *********************/

// SHARES
function watch_shares() {
    // If share changes
    $(document).on("change", input_share, function () {
        let sum = sum_shares();
        $("#total_share").val(sum).trigger("change");
    });
}

function sum_shares() {
    let sum = 0;
    $(input_share).each(function () {
        let val = parseFloat($(this).val());
        if (val > 0 && Number.isInteger(val * 100)) {
            sum += val;
        }
    });
    return sum;
}

// TOTAL SHARE
function watch_total_share() {
    $(document).on("change", "#total_share", function () {
        validate_shares();
    });
}

/******************* BASE BLOCK: VALIDATE FORM ************/
$(function () {
    watch_shares();
    watch_total_share();
});

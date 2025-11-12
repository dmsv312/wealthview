$("input:radio").click(function () {
    var previousValue = $(this).attr('previousValue');

    if (previousValue === 'checked') {
        $(this).prop('checked', false);
        $(this).attr('previousValue', false);
    } else {
        $("input:radio").attr('previousValue', false);
        $(this).attr('previousValue', 'checked');
    }
});
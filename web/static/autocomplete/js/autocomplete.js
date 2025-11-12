/*let suggestions = [
    {"value": "test_name ETF(test)", "data": "a"},
    {"value": "SPDR Portfolio Growth ETF(SPYG)", "data": "b"},
    {"value": "SPDR Portfolio Hight Div ETF(SPYD)", "data": "c"},
    {"value": "SPDR Buyback ETF(SPYB)", "data": "d"},
];
let availableTags = [
    "SPDR S&P 500 (SPY)",
    "SPDR Portfolio S&P 500 Growth ETF (SPYG)",
    "SPDR Portfolio S&P 500 Growth ETF (SPYG)",
    "SPDR Portfolio S&P 500 Growth ETF (SPYG)",
    "SPDR Portfolio S&P 500 Growth ETF (SPYG)"
];
let arr = [
    {value: 'Apple', data: 'AP'},
    {value: 'Xiaomi', data: 'XI'},
    {value: 'Huawei', data: 'HW'},
    {value: 'Microsoft', data: 'MS'},
    {value: 'Nvidia', data: 'NV'},
    {value: 'Google', data: 'GL'}
];

var tags = [
    "ActionScript",
    "AppleScript",
    "Asp",
    "BASIC",
    "C",
    "C++",
    "Clojure",
    "COBOL",
    "ColdFusion",
    "Erlang",
    "Fortran",
    "Groovy",
    "Haskell",
    "Java",
    "JavaScript",
    "Lisp",
    "Perl",
    "PHP",
    "Python",
    "Ruby",
    "Scala",
    "Scheme"
];*/

/*$('#autocomplete').autocomplete({
    // lookup: arr,
    serviceUrl: '/backtest/autocomplete/assets/all',
    onSelect: function (suggestion) {
        console.log('You selected: ' + suggestion.value + ', ' + suggestion.data);
    }
});*/

function toggleCurrencySelect(input) {
    if (input.attr("name") === "currency") {
        let $select = input.parent();
        $select.toggleClass('bblr');
    }
}


$(function () {
    $(document).on('click', '.ui-menu-item', (e) => {
        let input = document.activeElement;
        if (input.classList.contains("asset_input")){
            enable_share_field(input.parentNode);
        }
    });
    // https://github.com/devbridge/jQuery-Autocomplete
    // https://www.devbridge.com/sourcery/components/jquery-autocomplete/
    $(document).on('focus', ".tags", _onFocus);

    $(document).on('click', '.arrow.openAutocompele', (e) => {
        let input = $(e.currentTarget).next('.tags');
        $(input).val('');
        $(input).focus();
        input.autocomplete(get_options(input)).autocomplete("search", input.val());
    });

    $(document).on('click', '.select_line_wrapper_img', (e) => {
        let input = $(e.currentTarget).next('.tags');
        $(input).val('');
        $(input).focus();
        input.autocomplete(get_options(input)).autocomplete("search", input.val());
    });

    function _onFocus() {
        let input = $(this);
        // toggleCurrencySelect(input);
        $(input).val('');
        input.autocomplete(get_options(input)).autocomplete("search", input.val());
    }

    function get_options(input) {
        let keyword = get_keyword(input.data("type"));
        let field_type = input.data("type");
        let MAX_RESULTS = 30;
        return {
            // autoFocus: true,
            autoSelectFirst: true,
            source: function (request, response) {
                let results;
                if (field_type === "installed_benchmark") {
                    results = $.ui.autocomplete.filter(get_source_backtest(input), request.term);
                }
                if (field_type === "portfolio_currencies") {
                    results = $.ui.autocomplete.filter(get_source_portfolio(input), request.term);
                } else {
                    results = $.ui.autocomplete.filter(get_source_backtest(input), request.term);
                }

                response(results.slice(0, MAX_RESULTS));
            },
            minLength: 0,
            appendTo: input.parents(".autocomplete_body"),
            change: function (event, ui) {
                if (ui.item === null) {
                    // $(this).val('');
                    input.data("pk", "");
                    input[0].setCustomValidity("Выберите " + keyword + " из списка");
                } else {
                    input.attr('data-pk', ui.item.data);
                    input[0].setCustomValidity("");
                }
            },
        };
    }

    function set_active() {
        $(".ui-menu-item-wrapper.ui-state-active").css("background", "#1a1d2b");
        $(".ui-menu-item-wrapper.ui-state-active").parent().css("background", "#1a1d2b");
    }

    function get_keyword(data) {
        if (data === "assets") {
            return "актив";
        } else if (data === "benchmarks") {
            return "бенчмарк";
        } else {
            return "элемент";
        }
    }

    function get_source_backtest(input) {
        let source = [];
        let keyword = input.attr("data-filter");
        let url = "/backtest/ajax/autocomplete/";
        let instance_type = input.data("type");
        let term = input.val();
        $.ajax({
            async: false,
            type: "GET",
            url: url,
            data: {
                instance_type: instance_type,
                keyword: keyword,
                term: term,
            },
            cache: true,
            contentType: 'json',
            success: function (data) {
                source = data;
            }
        });
        return source["suggestions"];
    }

    function get_source_portfolio(input) {
        let source = [];
        let keyword = input.attr("data-filter");
        let url = "/account/ajax/autocomplete/";
        let instance_type = input.data("type");
        let term = input.val();
        $.ajax({
            async: false,
            type: "GET",
            url: url,
            data: {
                instance_type: instance_type,
                keyword: keyword,
                term: term,
            },
            cache: true,
            contentType: 'json',
            success: function (data) {
                source = data;
            }
        });
        return source["suggestions"];
    }
}
);

$('.tags').autocomplete({
    maxShowItems: 6
});
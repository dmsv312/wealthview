//Переменные для добавления функционала к кнопкам

//Рабочий div для сокращения доступа к элементам через querySelector
var main_div = document.getElementById("main_div");
//Тут ищутся кнопки в предыдущем найденном main_div
var btn_start = document.getElementById("btn_start"); //Следующий вопрос
var btn_next = document.getElementById("btn_next"); //Следующий вопрос
var btn_previous = document.getElementById("btn_previous"); //Предыдущий вопрос
var btn_end_test = document.getElementById("btn_end_test"); //Завершить тест
var start_again_risk_profile = document.getElementById("start_again_risk_profile"); //Пройти заново
var div_next = document.getElementById("next_div");
var div_end_test = document.getElementById("end_div");
var progress_rectangle = document.getElementById("progress_rectangle");
var progress = 124;

function paint_table(){
    let risk_matrix = document.getElementById("risk_table");
    let colors = [["#46B9F6", "#46B9F6", "#46B9F6", "#46B9F6", "#46B9F6"],
    ["#46B9F6", "#6A9DED", "#6A9DED", "#6A9DED", "#6A9DED"],
    ["#46B9F6", "#6A9DED", "#A177E8", "#A177E8", "#A177E8"],
    ["#46B9F6", "#6A9DED", "#A177E8", "#C162E6", "#C162E6"],
    ["#46B9F6", "#6A9DED", "#A177E8", "#C162E6", "#D752D8"]];
    for (let i=2; i < risk_matrix.rows.length; i++){
        risk_matrix.rows[i].cells[5].style.opacity = "1";
    }
    document.getElementById("main_td").classList.remove("bg_td_dark");
    for (let i=1; i <= risk_matrix.rows.length-1; i++){
        for (let j=0; j < risk_matrix.rows[i].cells.length-1; j++) {
            risk_matrix.rows[i].cells[j].style.background = colors[i-2][j];
        }
    }
}

function create_chart(){
    var analysis_data = document.getElementById("test_chart").innerHTML;
    //{{ cash_by_asset_type | safe }};
    var cash_by_asset_type = JSON.parse(analysis_data);
    var count = Object.keys(cash_by_asset_type).length;
    var base = "#039dd0";
    var pieColors = (function () {
        var colors = [],
            i;

        for (i = 0; i < count; i += 1) {
            // Start out with a darkened base color (negative brighten), and end
            // up with a much brighter color
            colors.push(Highcharts.color(base).brighten((i - 3) / (count + 10)).get());
        }
        return colors;
    }());
    Highcharts.chart('cash_by_asset_type', {
        colors: pieColors,
        chart: {
            height: 350,
            plotBackgroundColor: "#22273A",
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie',
            backgroundColor: "#22273A",
        },
        title: {
            text: 'Распределение по классам активов',
            style: {
                textTransform: "uppercase",
                color: "#ffffff",
                fontSize: "12px",
                fontFamily: "OpenSans-Semibold, sans-serif",
                width: "100%",
                textAlign: "center"

            }
        },
        tooltip: {
            pointFormat: '<b>{point.percentage:.1f}%</b>'
        },
        accessibility: {
            point: {
                valueSuffix: '%'
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                borderWidth: 0,
                cursor: 'pointer',
                dataLabels: {
                    distance: "20",
                    borderWidth: 0,
                    enabled: true,
                    format: "{point.name}: <br>{point.percentage:.1f} %</br>",
                    style: {
                        fontWeight: "normal",
                        fontSize: "10px",
                        textOutline: null,
                        color: "#ffffff",
                        fontFamily: "OpenSans-Regular, sans-serif",

                    }
                },

            }
        },
        series: [{
            name: 'Активы',
            colorByPoint: true,
            data: cash_by_asset_type
            ,
        }],
        exporting: {
            enabled: false,
        }
    });
}



var question = 1;
div_end_test.remove();
paint_table();
document.getElementById("question1").style.display = "block";

//Проверка ответил или нет пользователь на вопросы
//(если нет - выводим предупреждение и не пускаем в следующий или предыдущий вопрос)
function not_empty(answers) {
    for (let i=0; i<answers.length; i++) {
        if (answers[i].checked == true) return true;
    }
    return false;
}

//Получение номера ответа
function get_answer(answers) {
    for (let i=0; i<answers.length; i++) {
        if (answers[i].checked == true) return (i+1).toString();
    }
}

btn_start.addEventListener("click", function(){
    document.getElementById("start_page").style.display = "none";
    document.getElementById("test_page").style.display = "block";
    document.getElementById("icon_test").classList.remove("cg");
    document.getElementById("progress_line").classList.remove("sd_circle_line");
});

//Кнопка предыдущий вопрос
btn_previous.addEventListener("click", function(){
    
    //Получаем все ответы на вопрос и проверяем отмечен ли ответ
    var answers = document.getElementsByName("q" + question.toString());
    if (not_empty(answers)) {
        progress = progress - 124;
        progress_rectangle.setAttribute("width", progress.toString());
        //Прячем кнопку предыдущий вопрос, если текущий вопрос второй
        if (question == 2) {
            btn_previous.style.display = "none";
        }
        //Прячем кнопку завершить тест и отображаем кнопку следующий вопрос, если текущий вопрос последний
        if (question == 6) {
            div_end_test.remove();
            document.getElementById("progress-bar-ctn__wrap").appendChild(div_next);
        }
        //Прячем error_label после предыдущего ответа (я думаю быстрее так, чем добавлять отдельный error_label для каждого diva с вопросами
        document.getElementById("error_label").style.display = "none";
        //Получаем номер ответа и записываем его в скрытый input для дальнейшего получения в бэкенде
        document.getElementById("a" + question.toString()).value = get_answer(answers);
        //прячем текущий div
        document.getElementById("question" + question.toString()).style.display = "none";
        //открываем предыдущий div
        document.getElementById("question" + (question-1).toString()).style.display = "block";
        //присваиваем переменной question следующее значение
        question = question - 1;
    }
    //Если ответ не отмечен, выводим предупреждение и не меняем текущий вопрос
    else {
        document.getElementById("error_label").style.display = "block";
    }
    btn_previous.blur();
});

//Кнопка следующий вопрос
btn_next.addEventListener("click", function(){
    //Получаем все ответы на вопрос и проверяем отмечен ли ответ
    var answers = document.getElementsByName("q" + question.toString());
    if (not_empty(answers)) {
        progress = progress + 124;
        progress_rectangle.setAttribute("width", progress.toString());
        //Отображаем кнопку предыдущий вопрос, если текущий вопрос первый
        if (question == 1) {
            btn_previous.style.display = "inline-block";
        }
	    //Прячем кнопку следующий вопрос и отображаем кнопку завершить тест, если текущий вопрос последний
        if (question == 5) {
            // btn_next.style.display = "none";
            div_next.remove();
            document.getElementById("progress-bar-ctn__wrap").appendChild(div_end_test);
            btn_end_test.style.display = "inline-block";
        }
        //Прячем error_label после предыдущего ответа (я думаю быстрее так, чем добавлять отдельный error_label для каждого diva с вопросами
        document.getElementById("error_label").style.display = "none";
        //Получаем номер ответа и записываем его в скрытый input для дальнейшего получения в бэкенде
        document.getElementById("a" + question.toString()).value = get_answer(answers);
        //прячем текущий div
        document.getElementById("question" + question.toString()).style.display = "none";
        //открываем следующий div
        document.getElementById("question" + (question+1).toString()).style.display = "block";
        //присваиваем переменной question следующее значение
        question = question + 1;
    }
    //Если ответ не отмечен, выводим предупреждение и не меняем текущий вопрос
    else {
        document.getElementById("error_label").style.display = "block";
    }
    btn_next.blur();
});

//Ответ на последний вопрос, обработка и отправка ответов в бэкенд, получение ответа ajax
btn_end_test.addEventListener("click", function(){
    btn_end_test.blur();
    let data = {};
    //Обрабатываем последний вопрос
    var answers = document.getElementsByName("q" + question.toString())
    var result = "";
    if (not_empty(answers)) {
        //Прячем error_label после предыдущего ответа (я думаю быстрее так, чем добавлять отдельный error_label для каждого diva с вопросами
        document.getElementById("error_label").style.display = "none";
        //Получаем номер ответа и записываем его в скрытый input для дальнейшего получения в бэкенде
        document.getElementById("a" + question.toString()).value = get_answer(answers);
        //прячем текущий div
        document.getElementById("question" + question.toString()).style.display = "none";

        //Проходимся по всем скрытым инпутам и получаем значения ответов
        for (let i=1; i<(question+1); i++) {
            result = result + document.getElementById("a" + i.toString()).value;
        }
        //Открываем div для результатов
        document.getElementById("result_div").style.display = "block";
        console.log(result);
        data["answers"] = result;
            //Обрабатываем его в ajax
        $.ajax({
            async: false,
            type: "GET",
            url: '/risk_profile/ajax/risk_profile_result/',
            data: data,
            contentType: 'json',
            success: function (data) {
                for (let i=1; i<parseInt(data.profile_number)+1; i++) {
                    document.getElementById("circle" + i.toString()).setAttribute("stroke", "url(#linear-gradient6)");
                }
                document.getElementById("profile_number").innerHTML = data.profile_number;
                document.getElementById("profile_name").innerHTML = data.profile_name;
                document.getElementById("profile_description").innerHTML = data.profile_description;
                document.getElementById("profile_tolerance").innerHTML = data.profile_tolerance;
                document.getElementById("profile_capacity").innerHTML = data.profile_capacity;
                document.getElementById("profile_year").innerHTML = data.profile_year;
                document.getElementById("portfolio_description").innerHTML = data.portfolio_description;

                let risk_matrix = document.getElementById("risk_table");
                
                risk_matrix.rows[parseInt(data.profile_indexRC)+2].cells[parseInt(data.profile_indexRT)].style.opacity = "1";

                document.getElementById("test_chart").innerHTML = data.profile_portfolio;
                create_chart();
            }
        });
        document.getElementById("test_page").style.display = "none";
        document.getElementById("result_page").style.display = "block";
        document.getElementById("icon_result").classList.remove("cg");
        document.getElementById("progress_line").classList.add("save_rezult_circle_line");
    }
    //Если ответ не отмечен, выводим предупреждение и не меняем текущий вопрос
    else {
        document.getElementById("error_label").style.display = "block";
    }

});

start_again_risk_profile.addEventListener("click", function(){
    document.getElementById("start_page").style.display = "none";
    document.getElementById("test_page").style.display = "block";
    document.getElementById("result_page").style.display = "none";
    progress = 124;
    question = 1;
    document.getElementById("question1").style.display = "block";
    btn_previous.style.display = "none";
    div_end_test.remove();
    document.getElementById("progress-bar-ctn__wrap").appendChild(div_next);
    document.getElementById("result_div").style.display = "none";
    for (let i=1; i<6; i++) {
        document.getElementById("circle" + i.toString()).setAttribute("stroke", "#ccc");
    }
    let risk_matrix = document.getElementById("risk_table");
    risk_matrix.rows[parseInt(risk_profile_data.profile_indexRC)+2].cells[parseInt(risk_profile_data.profile_indexRT)].style.opacity = "0.4";
});

function fill_risk_profile() {
    for (let i=1; i<parseInt(risk_profile_data.profile_number)+1; i++) {
        document.getElementById("circle" + i.toString()).setAttribute("stroke", "url(#linear-gradient6)");
    }
    document.getElementById("profile_number").innerHTML = risk_profile_data.profile_number;
    document.getElementById("profile_name").innerHTML = risk_profile_data.profile_name;
    document.getElementById("profile_description").innerHTML = risk_profile_data.profile_description;
    document.getElementById("profile_tolerance").innerHTML = risk_profile_data.profile_tolerance;
    document.getElementById("profile_capacity").innerHTML = risk_profile_data.profile_capacity;
    document.getElementById("profile_year").innerHTML = risk_profile_data.profile_year;
    document.getElementById("portfolio_description").innerHTML = risk_profile_data.portfolio_description;

    let risk_matrix = document.getElementById("risk_table");

    risk_matrix.rows[parseInt(risk_profile_data.profile_indexRC)+2].cells[parseInt(risk_profile_data.profile_indexRT)].style.opacity = "1";

    document.getElementById("test_chart").innerHTML = risk_profile_data.profile_portfolio;
    create_chart();
    document.getElementById("start_page").style.display = "none";
    document.getElementById("test_page").style.display = "none";
    document.getElementById("result_page").style.display = "block";
}

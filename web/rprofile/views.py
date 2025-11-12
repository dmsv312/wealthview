from django.shortcuts import render
from django.template.context_processors import csrf
from .models import Answer, Question, RTestResult, RiskProfileVersion
from django.http import JsonResponse
from algorithm.risk_profile import risk_profile, get_risk_matrix
import json
from core.views import catch_error


# Create your views here.
@catch_error
def start(request):
    questions = Question.objects.order_by("number")
    risk_matrix = get_risk_matrix()

    quiz_information = {}
    i = 0
    for question in questions:
        all_answers = Answer.objects.filter(question=question)
        filtered_answers = all_answers.order_by("number")
        quiz_information[i] = {
            "question": question,
            "answers": filtered_answers,
        }
        i = i + 1

    context = {
        "quiz_information": quiz_information.values(),
        "risk_matrix": risk_matrix,
    }

    return render(request, "risk-profile/start.html", context)


@catch_error
def risk_profile_result(request):
    if not request.is_ajax():
        return render(request, "risk-profile/start.html")

    result = risk_profile(get_risk_profile_answers(request))
    portfolio = get_risk_profile_model_portfolio(result)

    if request.user.is_authenticated:
        r_test_result = create_risk_profile(request, result, portfolio)
        return user_risk_profile_context(r_test_result)

    return risk_profile_context(result, portfolio)


def create_risk_profile(request, result, portfolio):
    new_risk_profile = RTestResult.objects.create(
        user=request.user, profile=request.user.profile, result_data=result,
        version=RiskProfileVersion.get_current_version(),
        result_name=str(result['Название риск-профиля']),
        number=str(result['№ профиля']), description=str(result['Описание']),
        tolerance=str(int(result['Отношение к риску'])) + "/5",
        capacity=str(int(result['Возможность принятия риска'])) + "/5",
        acceptable_risk_value=str(result['Допустимое значение риска, 1 год']),
        portfolio_description=str(result['Модельный портфель']['Комментарии']),
        portfolio=portfolio,
        indexRT=(int(result['Отношение к риску']) - 1),
        indexRC=(int(result['Возможность принятия риска']) - 1)
    )
    request.user.profile.actual_r_test = new_risk_profile
    request.user.profile.save()
    return new_risk_profile


def get_risk_profile_answers(request):
    # Баллы за ответы и на тип ответа на первом месте первого элемента массива
    questions = Question.objects.order_by("number")
    # Формируем массив с ответами (на первом месте в каждой строке - тип вопроса)
    scores = {}
    i = 0
    for question in questions:
        scores[i] = {}
        # Добавляем в первый элемент строки тип вопроса
        scores[i][0] = int(question.type)
        j = 1
        all_answers = Answer.objects.filter(question=question)
        answers = all_answers.order_by("number")
        for answer in answers:
            scores[i][j] = answer.score
            j = j + 1
        i = i + 1

    # Получаем ответы из скрытого input'a
    value = request.GET.get("answers", None)
    # Записываем их в массив
    answers = list(value)
    # проходимся циклом по ответам и сопоставляем ответ - количество баллов
    my_scores = {}
    i = 0
    for answer in answers:
        # Получаем баллы и тип ответа из масссива с баллами
        my_scores[i] = {
            "type": scores[i][0],
            "value": scores[i][int(answer)],
        }
        i = i + 1
    return my_scores


def get_risk_profile_model_portfolio(result):
    cash_by_asset_type = [{"name": "Краткосрочные облигации и депозиты", "y": int(result['Модельный портфель']
                                                            ['Краткосрочные облигации и депозиты'])},
                          {"name": "Облигации", "y": int(result['Модельный портфель']['Облигации'])},
                          {"name": "Акции", "y": int(result['Модельный портфель']['Акции'])}, ]
    cash_by_asset_type = [i for i in cash_by_asset_type if i["y"] != 0]
    portfolio = json.dumps(cash_by_asset_type)
    return portfolio


def user_risk_profile_context(r_test_result):
    return JsonResponse({'profile_number': r_test_result.number,
                         'profile_name': r_test_result.result_name,
                         'profile_description': r_test_result.description,
                         'profile_tolerance': r_test_result.tolerance,
                         'profile_capacity': r_test_result.capacity,
                         'profile_year': r_test_result.acceptable_risk_value,
                         'portfolio_description': r_test_result.portfolio_description,
                         'profile_portfolio': r_test_result.portfolio,
                         'profile_indexRT': str(r_test_result.indexRT),
                         'profile_indexRC': str(r_test_result.indexRC), })


def risk_profile_context(result, portfolio):
    return JsonResponse({'profile_number': str(result['№ профиля']),
                         'profile_name': str(result['Название риск-профиля']),
                         'profile_description': str(result['Описание']),
                         'profile_tolerance': str(int(result['Отношение к риску'])) + "/5",
                         'profile_capacity': str(int(result['Возможность принятия риска'])) + "/5",
                         'profile_year': str(result['Допустимое значение риска, 1 год']),
                         'portfolio_description': str(result['Модельный портфель']['Комментарии']),
                         'profile_portfolio': portfolio,
                         'profile_indexRT': str(int(result['Отношение к риску']) - 1),
                         'profile_indexRC': str(int(result['Возможность принятия риска']) - 1), })

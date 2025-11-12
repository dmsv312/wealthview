from django.db import models


# Create your models here.
class Question(models.Model):
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    type = models.CharField(max_length=30, help_text="Тип вопроса. 1 или 2")
    question_text = models.CharField(max_length=300, help_text="Текст вопроса")
    number = models.IntegerField(help_text="Номер вопроса")

    def __str__(self):
        return "{number}. {question_text}".format(number=self.number, question_text=self.question_text)


class Answer(models.Model):
    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'

    text = models.CharField(max_length=300, help_text="Текст ответа")
    score = models.IntegerField(help_text="Баллы за ответ")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, help_text="Вопрос")
    number = models.IntegerField(help_text="Вариант ответа")

    def __str__(self):
        return "#{0} ({1})...".format(self.id, self.text[:30])


class RiskProfileVersion(models.Model):
    class Meta:
        verbose_name = 'Версия риск-профиля'
        verbose_name_plural = 'Версии риск-профиля'
    current_version = models.IntegerField(help_text="Текущая версия")

    @classmethod
    def get_current_version(cls):
        current_version_obj = cls.objects.first()
        if not current_version_obj:
            current_version_obj = cls.objects.create(current_version=1)
        return current_version_obj.current_version


class RTestResult(models.Model):
    user = models.ForeignKey('auth.User', related_name='r_test_results', on_delete=models.CASCADE)
    profile = models.ForeignKey('account.Profile', related_name='r_test_results', on_delete=models.CASCADE)
    version = models.IntegerField(help_text="Версия риск-профиля")

    result_name = models.CharField(max_length=250, help_text="Название профиля")
    result_data = models.JSONField()

    number = models.CharField(max_length=20, help_text="Номер профиля")
    description = models.TextField(help_text="Описание")
    tolerance = models.CharField(max_length=20, help_text="Отношение к риску")
    capacity = models.CharField(max_length=20, help_text="Возможность принятия риска")
    acceptable_risk_value = models.CharField(max_length=20, help_text="Допустимое значение риска, 1 год")
    portfolio_description = models.TextField(help_text="Описание модельного портфеля")
    portfolio = models.TextField(help_text="Модельный портфель")
    indexRT = models.IntegerField(help_text="Индекс tolerance")
    indexRC = models.IntegerField(help_text="Индекс capacity")

    notification_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.profile} - {self.result_name} от {self.created_at}'



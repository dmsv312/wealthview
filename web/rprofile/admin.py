from django.contrib import admin
from .models import *


# Register your models here.
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'type', 'number',)


class AnswerAdmin(admin.ModelAdmin):
    list_display = ('text', 'score', 'question', 'number',)


class RTestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'profile', 'result_name', 'created_at',)


class RiskProfileVersionAdmin(admin.ModelAdmin):
    list_display = ("current_version",)


admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(RTestResult, RTestResultAdmin)
admin.site.register(RiskProfileVersion, RiskProfileVersionAdmin)

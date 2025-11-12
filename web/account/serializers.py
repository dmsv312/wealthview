import datetime
from django.forms.models import model_to_dict


class ModelToCacheSerializer():

    @classmethod
    def dumps(cls, obj):
        obj_dict = model_to_dict(obj)
        for key, value in obj_dict.items():
            if isinstance(value, datetime.date):
                obj_dict[key] = value.strftime("%d-%m-%Y")
            if value is None:
                obj_dict[key] = ""
        return obj_dict

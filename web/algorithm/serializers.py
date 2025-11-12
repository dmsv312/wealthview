import json

from numpy import ndarray, asarray


class CustomJsonEncoder(json.JSONEncoder):
    """Json serializer which can dumps numpy array"""
    def default(self, obj):
        if isinstance(obj, ndarray):
            return {
                '__type__': '__ndarray__',
                'object': obj.tolist()
            }
        else:
            return json.JSONEncoder.default(self, obj)


def custom_decoder(obj):
    if '__type__' in obj:
        if obj['__type__'] == '__ndarray__':
            return asarray(obj["object"])
    return obj


# encoder
def custom_dumps(obj):
    return json.dumps(obj, cls=CustomJsonEncoder)


# decoder
def custom_loads(obj):
    return json.loads(obj, object_hook=custom_decoder)
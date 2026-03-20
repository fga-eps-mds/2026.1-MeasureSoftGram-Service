from django.db import models


def is_the_same_call(current_call: dict, prev_call: dict):
    prev_kwargs = [(k, set(v)) for k, v in prev_call['kwargs'].items()]
    prev_kwargs.sort()

    current_kwargs = [(k, set(v)) for k, v in current_call['kwargs'].items()]
    current_kwargs.sort()

    return (
        prev_call['model_name'] == current_call['model_name']
        and prev_call['function_name'] == current_call['function_name']
        and prev_call['args'] == current_call['args']
        and prev_kwargs == current_kwargs
    )


class CacheManager(models.Manager):
    """
    Esse cached manager foi feito pensando específicamente para as
    supported entities, pois essas tabelas mudam com quase nenhuma frequencia
    e são muito solicitadas.

    Usar esse cached manager com outras models certamente irá levar a bugs de
    difícil detecção. Como por exemplo queryset de filtros incorretos.
    """

    last_call = {
        'function_name': None,
        'args': None,
        'kwargs': {},
        'return': None,
        'model_name': None,
    }

    def filter(self, *args, **kwargs):
        call = {
            'function_name': 'filter',
            'args': args,
            'kwargs': kwargs,
            'model_name': self.model.__name__,
        }

        if is_the_same_call(call, CacheManager.last_call):
            return self.last_call['return']

        qs = super().filter(*args, **kwargs)

        call['return'] = qs
        CacheManager.last_call = call

        return qs

import os
import random


class IResponse:
    def __init__(
        self,
        _json: dict,
        _status_code: int = 200,
    ) -> None:
        self._json = _json
        self._status_code = _status_code

    @property
    def ok(self):
        return 200 <= self._status_code < 300

    @property
    def status_code(self):
        return self._status_code

    def json(self):
        return self._json


class Mocks:
    @staticmethod
    def calculate_entity(params, entity_name):
        _status_code = int(os.getenv('RESPONSE_HTTP_STATUS_CODE', '200'))
        _json = {
            entity_name: [
                {'key': entity['key'], 'value': random.random()}
                for entity in params[entity_name]
            ]
        }
        return IResponse(_json=_json, _status_code=_status_code)

    @staticmethod
    def calculate_measure(params):
        return Mocks.calculate_entity(params, 'measures')

    @staticmethod
    def calculate_subcharacteristic(params):
        return Mocks.calculate_entity(params, 'subcharacteristics')

    @staticmethod
    def calculate_characteristic(params):
        return Mocks.calculate_entity(params, 'characteristics')

    @staticmethod
    def calculate_tsqmi(params):
        _status_code = int(os.getenv('RESPONSE_HTTP_STATUS_CODE', '200'))
        _json = {'value': random.random()}
        return IResponse(_json, _status_code)

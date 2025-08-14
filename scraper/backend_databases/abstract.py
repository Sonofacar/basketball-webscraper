from abc import ABC, abstractmethod
from functools import wraps

def pass_none_location(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if getattr(self, 'location', None) is not None:
            return func(self, *args, **kwargs)
    return wrapper

class database(ABC):
    def __init__(self, location):
        self.location = location

    @abstractmethod
    def save_data(self, data, table):
        pass

    @abstractmethod
    def get_data(self, table):
        pass

    @abstractmethod
    def execute(self, command):
        pass

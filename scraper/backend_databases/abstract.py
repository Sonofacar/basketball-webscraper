# backend_databases/abstract.py
#
# Copyright (C) 2025 Carson Buttars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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

    @abstractmethod
    def give_connection(self):
        pass

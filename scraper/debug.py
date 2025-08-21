# debug.py
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

from abc import ABC

class debug(ABC):
    def debug(title, message):
        print('[ ' + title + " ]:\t" + message)

    def debug_error(self, soup, location, field, return_type, info = '', default = None):
        if not (isinstance(return_type, type) or return_type == None):
            raise TypeError

        output = 0

        try:
            url = soup.find('link', {'rel': 'canonical'}).attrs['href']
            href = url.replace('https://www.basketball-reference.com', '')
        except:
            href = 'This comes from the most recent page that was requested.'

        print("[   Error    ]:\t" + location + "(" + field + "): Could not fill the field.\t" + href)
        if info != '':
            print("\t\tCONTEXT: " + info)

        if default != None:
            output = default
            return output

        if return_type == int:
            output = 0
        elif return_type == str:
            output = ''
        elif return_type == bool:
            output = False
        elif return_type == list:
            output = []
        elif return_type == None:
            output = return_type

        return output

    def error_wrap(location = '', field = '', return_type = '', info = '', default = None):
        def decorator(function):
            def wrapper(self, *args, **kwargs):
                try:
                    return function(self, *args, **kwargs)
                except:
                    return self.debug_error(self.soup, location, field, return_type, info, default)
            return wrapper
        return decorator

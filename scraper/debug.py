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

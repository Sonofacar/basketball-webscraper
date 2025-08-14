from abc import ABC, abstractmethod

class pager(ABC):
    def __init__(self, cache_size, base_url):
        self.cache_size = cache_size
        self.base_url = base_url

    @abstractmethod
    def get(self, href, cache = True):
        pass

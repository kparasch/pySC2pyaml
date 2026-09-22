from abc import ABCMeta, abstractmethod

class ACatalog(metaclass=ABCMeta):
    @abstractmethod
    def resolve(self, key: str):
        pass
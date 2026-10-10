from abc import ABC, abstractmethod

class BaseDatabase(ABC):
    """
    Abstract base class for database operations.
    """

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def create_session(self):
        pass

    @abstractmethod
    def create_tables(self):
        pass
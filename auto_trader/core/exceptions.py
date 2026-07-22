"""Application exception hierarchy."""


class AutoTraderError(Exception):
    pass


class IngestionError(AutoTraderError):
    pass


class StorageError(AutoTraderError):
    pass

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class GetLogResponse(object):
    log: dict

class LoggerClient(ABC):
    """Client to obtain logs from a USS."""

    timestamp_start: str
    timestamp_end: str

    def __init__(self, timestamp_start: str, timestamp_end: str):
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

    @abstractmethod
    def get_log(self, timestamp_start:str, timestamp_end:str) -> GetLogResponse:
        raise NotImplementedError()

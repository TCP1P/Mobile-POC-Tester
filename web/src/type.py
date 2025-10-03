from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable
from enum import Enum

class Status(Enum):
    PENDING_QUEUE = 'PENDING_QUEUE'
    INITIALIZING = 'INITIALIZING'
    INSTALLING_POC = 'INSTALLING_POC'
    RUNNING_CHALLENGE = 'RUNNING_CHALLENGE'
    RUNNING_POC = 'RUNNING_POC'
    TAKING_SCREENSHOT = 'TAKING_SCREENSHOT'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


@dataclass
class Client:
    PACKAGE_NAME: str
    CHALLENGE_NAME: str = ""
    TIMEOUT: int = 300
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        if not self.PACKAGE_NAME:
            raise ValueError("PACKAGE_NAME is required")

@dataclass
class Queue:
    id: str
    status: Status
    client: Client
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def update_status(self, status: Status):
        if status == Status.INITIALIZING:
            self.started_at = datetime.now()

        self.status = status
        self.updated_at = datetime.now()

    def mark_completed(self):
        self.completed_at = datetime.now()
        self.status = Status.COMPLETED
    
    def mark_error(self, error_message: str):
        self.error = error_message
        self.status = Status.ERROR
        self.completed_at = datetime.now()
    
    @property
    def is_completed(self) -> bool:
        return self.status in [Status.COMPLETED, Status.ERROR]
    
    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

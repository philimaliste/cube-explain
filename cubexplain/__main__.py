import json

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import start_session
from .atotiwatcher import AtotiWatcher

session = start_session()
print(f"Session running at http://localhost:{session.port}")
observer = PollingObserver()
observer.schedule(AtotiWatcher(session), './')
observer.start()
session.wait()

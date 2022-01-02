import json

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import start_session
from .atotiwatcher import AtotiWatcher

input_path = "/Users/philippecoumbassa/data/dataprocessor_input/"
session = start_session(input_path)
print(f"Session running at http://localhost:{session.port}")
observer = PollingObserver()
observer.schedule(AtotiWatcher(session), input_path)
observer.start()
session.wait()

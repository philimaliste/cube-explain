import json

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import start_session
from .atotiwatcher import AtotiWatcher

f = open("./cube_properties.json")
cube_config = json.load(f)
input_path = cube_config["path_input"]
session = start_session()
print(f"Session running at http://localhost:{session.port}")
observer = PollingObserver()
observer.schedule(AtotiWatcher(session), input_path)
observer.start()
session.wait()

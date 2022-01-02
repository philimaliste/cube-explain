import json

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import start_session
from .atotiwatcher import AtotiWatcher

import sys


def main():
    input_path = "./"
    if len(sys.argv) > 2:
        print("Loading files in ", sys.argv[1])
        input_path = sys.argv[1]
    session = start_session(input_path)
    print(f"Session running at http://localhost:{session.port}")
    observer = PollingObserver()
    observer.schedule(AtotiWatcher(session), input_path)
    observer.start()
    session.wait()

import json

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from . import start_session
from .atotiwatcher import AtotiWatcher

import sys


def main():
    input_path = "./"
    print(len(sys.argv))
    if len(sys.argv) > 1:
        print("Loading files in ", sys.argv[1])
        input_path = sys.argv[1]
    print("input_path", input_path)
    session = start_session(input_path)
    print(f"Session running at http://localhost:{session.port}")
    observer = PollingObserver()
    observer.schedule(AtotiWatcher(session), input_path)
    observer.start()
    session.wait()

from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler

from .dataprocessor import DataProcessor


class AtotiWatcher(FileSystemEventHandler):
    def __init__(self, session) -> None:
        self.session = session

    def on_created(self, event: FileCreatedEvent):
        try:
            print("Loading ", event.src_path)
            dataprocessor = DataProcessor()
            src_path = event.src_path
            if "ScenarioDate" in src_path:
                df = dataprocessor.read_explain_file(src_path)
                tablename = "Explain"
            else:
                df = dataprocessor.read_var_file(src_path)
                tablename = "Var"
            with self.session.start_transaction():
                self.session.tables[tablename].load_pandas(df)
        except Exception as error:
            print(error)

    def on_deleted(self, event: FileCreatedEvent):
        try:
            print("Unloading ", event.src_path)
            dataprocessor = DataProcessor()
            src_path = event.src_path
            print("file deleted", src_path)
            if "ScenarioDate" in src_path:
                tablename = "Explain"
            else:
                tablename = "Var"
            with self.session.start_transaction():
                self.session.tables[tablename].drop({"Pathfile": src_path})
        except Exception as error:
            print(error)

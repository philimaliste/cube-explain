from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler

from .dataprocessor import DataProcessor


class AtotiWatcher(FileSystemEventHandler):
    def __init__(self, session) -> None:
        self.session = session

    def on_created(self, event: FileCreatedEvent):
        try:
            dataprocessor = DataProcessor()
            src_path = event.src_path
            if "EDEN.csv" in src_path[-10:]:
                var_df = dataprocessor.read_var_file(src_path)
                self.session.tables["Var"].load_pandas(var_df)
            if "ScenarioDate" in src_path:
                explain_df = dataprocessor.read_explain_file(src_path)
                self.session.tables["Explain"].load_pandas(explain_df)
        except Exception as error:
            print(error)

    def on_deleted(self, event: FileCreatedEvent):
        try:
            dataprocessor = DataProcessor()
            src_path = event.src_path
            print("file deleted", src_path)
            if "EDEN.csv" in src_path[-10:]:
                self.session.tables["Var"].drop({"Pathfile": src_path})
            if "ScenarioDate" in src_path:
                self.session.tables["Explain"].drop({"Pathfile": src_path})
        except Exception as error:
            print(error)

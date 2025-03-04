from __future__ import annotations

import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event) -> None:
        tmp = 10
        # print(event)
        pass  # Placeholder for handling any event

    def on_modified(self, event) -> None:
        tmp = 10
        # print(event)
        pass  # Placeholder for handling modified events

    def on_created(self, event) -> None:
        # print('triggered')
        # print(event)
        # print(event.event_type)
        if not event.src_path.endswith(".swp"):
            # print(event.src_path)
            with Path(save_path).open(mode="a") as fid:
                fid.write(f"{event.src_path}\n")
        # print(event.is_directory)


def main(participant_id: str, read_path: str, save_path: str) -> None:
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, read_path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    participant_id = sys.argv[1]
    read_path = sys.argv[2]
    save_path = sys.argv[3]
    main(participant_id, read_path, save_path)

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        tmp=10
        #print(event)
    def on_modified(self, event):
        tmp=10
        #print(event)
    
    def on_created(self, event):
        #print('triggeered')
        #print(event)
        #print(event.event_type)
        if not event.src_path.endswith('.swp'):
            print(event.src_path)
        #print(event.is_directory)


if __name__ == "__main__":
    path = "/home/akv/FLASH_PO1/check_events"
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

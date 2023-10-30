import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

famid = sys.argv[1]
read_path = sys.argv[2]
save_path = sys.argv[3]

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
            #print(event.src_path)
            fid = open(save_path,'a')
            fid.write(event.src_path+'\n')
            fid.close()
            
        #print(event.is_directory)


if __name__ == "__main__":
    path = read_path #"/home/akv/FLASH_PO1/check_events"
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

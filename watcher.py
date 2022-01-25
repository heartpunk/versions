import hashlib
import pywatchman
from functools import reduce
from glob import glob
from sys import argv
from pathlib import Path
from uuid import uuid4
import types
from watcher_onto import *


path = argv[1]
snapshot_path = str(Path.home() / '.snapshots')
try:
    os.mkdir(snapshot_path)
except FileExistsError:
    pass



def update_handler(update):
    if 'files' in update:
        uuid = str(uuid4())
        thing = Snapshot(uuid)
        thing.uuid4.append(uuid)

        for key, value in update.items():
            with onto:
                if type(value) in owlready_builtin_datatypes:
                    property_type(key, Snapshot, type(value))
                    #print("setattr(%s, %s, %s)" % (thing, key, value))
                    getattr(thing, key).append(value)
                elif type(value) == list and key == 'files':
                    for i, item in enumerate(value):
                        if type(item) == dict:
                            file_uuid = str(uuid4())
                            file = File(file_uuid)
                            file.uuid4.append(file_uuid)
                            
                            sha256 = update_file_handler(item)
                            if type(sha256) != str:
                                continue
                            property_type('sha256', Thing, str)
                            file.sha256.append(sha256)
                            thing.files.append(file)
                
                            for subkey, subval in item.items():
                                #setattr(getattr(thing, key), 'append', file)
                                #print("setattr(%s, %s, %s)" % (file, subkey, subval))
                                setattr(file, ('filename' if (subkey == "name") else subkey), subval)
                        else:
                            print("files should only contain dicts shouldn't it? %s" % item)
                else:
                    print("value for key %s is of unsupported type %s" % (key, type(value)))
                default_world.save()
    else:
        print("update with no 'files' entry ", update)


def update_file_handler(file):
    try:
        with open(path + '/' + file['name'], 'r') as f:
            contents = f.read().encode('utf8')

            print(hashlib.sha256(contents).hexdigest(), file)

            with open(snapshot_path + hashlib.sha256(contents).hexdigest(), 'wb') as new_file:
                new_file.write(contents)

            return hashlib.sha256(contents).hexdigest()
    except IsADirectoryError:
        pass
    except UnicodeDecodeError:
        pass
    except FileNotFoundError:
        pass


if __name__ == '__main__':
    with pywatchman.client() as c:
        c.query("watch-project", path)
        c.query("subscribe", path, "foooo", {'fields': ['name', 'exists', 'cclock', 'oclock', 'ctime', 'ctime_ms', 'ctime_us', 'ctime_ns', 'ctime_f', 'mtime', 'mtime_ms', 'mtime_us', 'mtime_ns', 'mtime_f', 'size', 'mode', 'uid', 'gid', 'ino', 'dev', 'nlink', 'new', 'type', 'symlink_target', 'content.sha1hex']})
        while True:
            try:
                update = c.receive()
                if update:
                    update_handler(update)
            except pywatchman.SocketTimeout:
                pass

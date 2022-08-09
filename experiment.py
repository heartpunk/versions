import multiprocessing
import pywatchman
import os
from owlready2.sparql.endpoint import *
from owlready2 import *
import watcher_onto
import werkzeug.serving
import flask

SESSION_UUID = watcher_onto.start_session()

# start an owlready sparql endpoint in another process
def start_endpoint(sqlite_file_path):
    app = flask.Flask("Owlready_sparql_endpoint")
    endpoint = EndPoint(default_world)
    app.route("/sparql", methods = ["GET"])(endpoint)
    werkzeug.serving.run_simple("localhost", 5000, app)


# an update handler to be executed inside the watchman_loop
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

# a function to run the watchman query loop
def watchman_loop(path, update_handler=update_handler, *args, **kwargs):
    # pretty print the index and type of each argument
    for i, arg in enumerate(args):
        print("arg %d: %s" % (i, type(arg)))
    for key, value in kwargs.items():
        print("kwarg %s: %s" % (key, type(value)))

    with pywatchman.client() as c:
        c.query("watch-project", path)
        # subscribe to the watchman query above, request all fields in the response
        c.query("subscribe", path, "foooo", {
            'fields': ['name', 'exists', 'cclock', 'oclock', 'ctime', 'ctime_ms', 'ctime_us', 'ctime_ns', 'ctime_f',
                       'mtime', 'mtime_ms', 'mtime_us', 'mtime_ns', 'mtime_f', 'size', 'mode', 'uid', 'gid', 'ino',
                       'dev', 'nlink', 'new', 'type', 'symlink_target', 'content.sha1hex']})
        while True:
            try:
                update = c.receive()
                if update:
                    update_handler(update)
            except pywatchman.SocketTimeout:
                pass

if __name__ == '__main__':
    # get the path to watch from the first command line argument
    path = sys.argv[1]
    # create a process to run the watchman client
    watcher = multiprocessing.Process(target=watchman_loop, args=(path))
    watcher.start()
    # start the sparql endpoint in another process
    server = multiprocessing.Process(target=start_endpoint, args=(watcher_onto.sqlite_path(SESSION_UUID),))
    server.start()

    # join the watcher and server processes
    watcher.join()
    server.join()
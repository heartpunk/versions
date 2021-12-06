from uuid import uuid4
from owlready2 import *
from pathlib import Path

owlready_builtin_datatypes = [int, float, bool, str]
onto = get_ontology("https://github.com/heartpunk/versions/ontology.owl")
session_uuid = str(uuid4())


def property_type(name, d, r):
    with onto:
        klass = types.new_class(name, ((d >> r),))
        default_world.save()
        return klass

with onto:
    class File(Thing):
        pass
    class Snapshot(Thing):
        pass
    default_world.set_backend(filename = str(Path.home() / ".watcher") + session_uuid + ".sqlite3", exclusive=False)
    default_world.save()

property_type('files', Snapshot, File)
property_type('uuid4', Thing, str)

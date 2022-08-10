from uuid import uuid4
from owlready2 import *
from pathlib import Path

owlready_builtin_datatypes = [int, float, bool, str]
onto = get_ontology("https://github.com/heartpunk/versions/ontology.owl")



def property_type(name, d, r):
    with onto:
        klass = types.new_class(name, ((d >> r),))
        default_world.save()
        return klass

def sqlite_path(session_uuid):
    return str(Path.home() / ".watcher" / session_uuid) + ".sqlite3"

class File(Thing):
    pass
class Snapshot(Thing):
    pass

def python_owlready_entity_classes():
    property_type('files', Snapshot, File)
    property_type('uuid4', Thing, str)

def start_session():
    python_owlready_entity_classes()
    session_uuid = str(uuid4())
    default_world.set_backend(filename=sqlite_path(session_uuid), exclusive=False)
    default_world.save()
    return session_uuid

from owlready2 import *
default_world.set_backend(filename = "/Users/heartpunk/.watcher/a5ba9a0e-1345-47b0-96c8-f7d146b51aaa.sqlite3", exclusive=False)

if __name__ == '__main__':
    from watcher_onto import *
    from owlready2.sparql.endpoint import *
    import werkzeug.serving
    import flask

    app = flask.Flask("Owlready_sparql_endpoint")
    endpoint = EndPoint(default_world)
    app.route("/sparql", methods = ["GET"])(endpoint)

    print(app.url_map)
    # Run the server with Werkzeug; you may use any other WSGI-compatible server
    werkzeug.serving.run_simple("localhost", 5000, app)

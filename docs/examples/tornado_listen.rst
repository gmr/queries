Tornado LISTEN/NOTIFY Example
=============================
The following example shows how Queries can be used with Tornado to create an
asynchronous long-polling LISTEN/NOTIFY web service.

.. code:: python

    import json
    import logging
    from tornado import gen, ioloop, web
    import queries

    LOGGER = logging.getLogger(__name__)


    class ListenHandler(web.RequestHandler):

        def initialize(self):
            self.channel = None
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self, *args, **kwargs):

            # Keep what channel is being used in case the conn is abruptly closed
            self.channel = kwargs['channel']

            # The app will asynchronously block, allowing other requests to process
            yield self.session.listen(self.channel, self.on_notification)

            # Remove channel assignment to keep on_connection_close from unlistening
            self.channel = None

            # Close the connection
            self.finish()

        def on_connection_close(self):
            if self.channel:
                self.session.unlisten(self.channel)
                self.channel = None

        @gen.coroutine
        def on_notification(self, channel, pid, payload):

            # If a stop payload is sent, stop the listening, get() will close & exit
            if payload == "stop":
                yield self.session.unlisten('test')
            else:

                # Write JSON encoded data to the connection
                self.write(json.dumps({"channel": channel,
                                       "pid": pid,
                                       "payload": payload}) + "\n")

                # Flush the output
                yield gen.Task(self.flush)


    if __name__ == "__main__":
        logging.basicConfig(level=logging.DEBUG)
        application = web.Application([
            (r"/(?P<channel>[a-z_0-9]+)", ListenHandler)
        ]).listen(8888)
        ioloop.IOLoop.instance().start()

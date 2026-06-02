from itertools import count
import logging

import orjson

from starlette.datastructures import Headers

from camelot.core.qt import QtCore, Qt

from ..view.requests import AbstractRequest, AbstractClientConnection
from ..view.responses import Ready

LOGGER = logging.getLogger(__name__)

_backend = None
_window = None

def get_root_backend():
    """
    Get the root backend that is used to communicate between python and C++/QML.
    """
    global _backend
    if _backend is None:
        app = QtCore.QCoreApplication.instance()
        _backend = app.findChild(QtCore.QObject, 'cpp_root_backend')
        assert _backend
    return _backend

def get_window():
    """
    Get the QQuickView that was created in C++.
    """
    global _window
    if _window is None:
        _window = get_root_backend().window()
        assert _window
    return _window

def cpp_action_step(gui_context_name, name, step=QtCore.QByteArray()):
    response = get_root_backend().action_step(gui_context_name, name, step)
    return orjson.loads(response.data())


connection_counter = count()

class PythonConnection(QtCore.QObject, AbstractClientConnection):
    """Use python to connect to a server, this is done by using
    the PythonRootBackend, and listen for signals from the action runner
    and the dgc.  As any instance of this class listens to requests for the
    server, only one instance of this class should exist, to avoid sending
    multiple responses for the same request to the client.
    """

    def __init__(self):
        assert next(connection_counter) == 0, "Only one instance of PythonConnection should be created"
        super().__init__()
        self.backend = get_root_backend()
        self.dgc = self.backend.distributed_garbage_collector()

    def __enter__(self):
        self.dgc.request.connect(self.on_request)
        # queued, to allow the python code to store the returned gui_run of the action before
        # the actual action step results are sent back
        self.backend.action_runner().request.connect(self.on_request, Qt.ConnectionType.QueuedConnection)
        # as this connection is used for testing, don't provide a hint for an action to start
        # running, to keep the testing code in control of when actions start running
        self.send_response(Ready(action_name=None))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.backend.action_runner().waitForCompletion()
        self.dgc.request.disconnect(self.on_request)
        self.backend.action_runner().request.disconnect(self.on_request)
        return False

    @classmethod
    def _execute_serialized_request(cls, serialized_request, connection: AbstractClientConnection):
        try:
            AbstractRequest.handle_request(
                serialized_request, connection
            )
        except Exception as e:
            LOGGER.error('Unhandled exception in model process', exc_info=e)
            import traceback
            traceback.print_exc()
        except SystemExit:
            LOGGER.debug('Terminating')
            raise
        except:
            LOGGER.error('Unhandled event in model process')

    @QtCore.qt_slot(QtCore.QByteArray)
    def on_request(self, request):
        self._execute_serialized_request(request.data(), self)

    @classmethod
    def send_response(cls, response):
        backend = get_root_backend()
        action_runner = backend.action_runner()
        action_runner.onResponse(QtCore.QByteArray(response._to_bytes()))

    @classmethod
    def send_action_step(cls, gui_context_name, step):
        return cpp_action_step(gui_context_name, type(step).__name__, step._to_bytes())

    def has_cancel_request(self):
        return False
    
    def headers(self):
        return Headers()

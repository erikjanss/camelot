'''
Created on Sep 12, 2009

@author: tw55413
'''

import logging
logger = logging.getLogger('camelot.view.model_thread.no_thread_model_thread')

from PyQt4 import QtCore
from signal_slot_model_thread import AbstractModelThread, setup_model
from camelot.view.controls.exception import register_exception

class NoThreadModelThread( AbstractModelThread ):

    def __init__(self, setup_thread = setup_model ):
        super(NoThreadModelThread, self).__init__()
        self.responses = []
        AbstractModelThread.__init__(self, setup_thread = setup_model )

    def start(self):
        try:
            self._setup_thread()
        except Exception, e:
            name, trace = register_exception(logger, 'Exception when setting up the NoThreadModelThread', e)
            self.setup_exception_signal.emit(name, trace)

    def post( self, request, response = None, exception = None ):
        try:
            result = request()
            response( result )
        except Exception, e:
            if exception:
                logger.error( 'exception caught in model thread while executing %s'%self._name, exc_info = e )
                import traceback, cStringIO
                sio = cStringIO.StringIO()
                traceback.print_exc(file=sio)
                traceback_print = sio.getvalue()
                sio.close()
                exception_info = (e, traceback_print)
                exception(exception_info)

    def wait_on_work(self):
        app = QtCore.QCoreApplication.instance()
        i = 0
        # only process events 10 times to avoid dead locks
        while app.hasPendingEvents() and i < 10:
            app.processEvents()
            i += 1
            
    def isRunning(self):
        return True

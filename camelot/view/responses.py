from dataclasses import dataclass
import logging
import typing

from ..core.naming import CompositeName
from ..core.serializable import NamedDataclassSerializable

LOGGER = logging.getLogger('camelot.view.responses')


@dataclass
class AbstractResponse(NamedDataclassSerializable):
    """
    Serialiazable Responses the model can send to the UI
    """
    pass


@dataclass
class Ready(AbstractResponse):
    """
    This indicates the server is ready to start executing actions.
    This differs from the socket being connected, as it indicates
    end-to-end readiness.  It also provides a hint to the client
    for the name of the first action to run.
    """
    action_name: typing.Optional[CompositeName]
    model_context: typing.Optional[CompositeName]


@dataclass
class Busy(AbstractResponse):
    busy: bool


@dataclass
class ActionStepped(AbstractResponse):
    run_name: CompositeName
    gui_run_name: CompositeName
    # @todo : blocking should be a correlation id instead of a bool, so
    # the server can validate if the response is for the correct step
    blocking: bool
    step: NamedDataclassSerializable


@dataclass
class ActionStopped(AbstractResponse):
    run_name: CompositeName
    gui_run_name: CompositeName
    exception: typing.Any

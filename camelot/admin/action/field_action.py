#  ============================================================================
#
#  Copyright (C) 2007-2016 Conceptive Engineering bvba.
#  www.conceptive.be / info@conceptive.be
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#      * Neither the name of Conceptive Engineering nor the
#        names of its contributors may be used to endorse or promote products
#        derived from this software without specific prior written permission.
#  
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  ============================================================================

"""ModelContext, GuiContext and Actions that are used in the context of
editing a single field on a form or in a table.  This module contains the
various actions that are beyond the icons shown in the editors of a form.
"""

import os

from ...core.qt import QtWidgets, QtGui
from ...core.utils import ugettext_lazy as _
from ...admin.icon import Icon
from .base import Action, RenderHint
from .application_action import (ApplicationActionModelContext,
                                 ApplicationActionGuiContext)


class FieldActionModelContext( ApplicationActionModelContext ):
    """The context for a :class:`Action` on a field.  On top of the attributes of the
    :class:`camelot.admin.action.application_action.ApplicationActionGuiContext`,
    this context contains :

    .. attribute:: obj

       the object of which the field displays a field

    .. attribute:: field

       the name of the field that is being displayed

       attribute:: value

       the value of the field as it is displayed in the editor

    .. attribute:: field_attributes

        A dictionary of field attributes of the field to which the context
        relates.

    """

    def __init__(self):
        super( FieldActionModelContext, self ).__init__()
        self.obj = None
        self.field = None
        self.value = None
        self.field_attributes = {}

class FieldActionGuiContext( ApplicationActionGuiContext ):
    """The context for an :class:`Action` on a field.  On top of the attributes of the
    :class:`camelot.admin.action.application_action.ApplicationActionGuiContext`,
    this context contains :

    .. attribute:: editor

       the editor through which the field is edited.

    """

    model_context = FieldActionModelContext

    def __init__( self ):
        super( FieldActionGuiContext, self ).__init__()
        self.editor = None

    def get_window(self):
        if self.editor is not None:
            return self.editor.window()
        return super(FieldActionGuiContext, self).get_window()

    def create_model_context( self ):
        context = super( FieldActionGuiContext, self ).create_model_context()
        context.value = self.editor.get_value()
        context.field_attributes = self.editor.get_field_attributes()
        return context

    def copy( self, base_class = None ):
        new_context = super( FieldActionGuiContext, self ).copy( base_class )
        new_context.editor = self.editor
        return new_context

class FieldAction(Action):
    """Action class that renders itself as a toolbutton, small enough to
    fit in an editor"""

    name = 'field_action'
    render_hint = RenderHint.TOOL_BUTTON


class SelectObject(FieldAction):
    """Allows the user to select an object, and set the selected object as
    the new value of the editor"""

    icon = Icon('search') # 'tango/16x16/actions/system-search.png'
    tooltip = _('select existing')
    name = 'select_object'

    def model_run(self, model_context):
        from camelot.view import action_steps
        admin = model_context.field_attributes.get('admin')
        if admin is not None:
            selected_objects = yield action_steps.SelectObjects(admin)
            for selected_object in selected_objects:
                yield action_steps.UpdateEditor('selected_object', selected_object)
                break

    def get_state(self, model_context):
        state = super(SelectObject, self).get_state(model_context)
        state.visible = (model_context.value is None)
        state.enabled = model_context.field_attributes.get('editable', False)
        return state

class NewObject(SelectObject):
    """Open a form for the creation of a new object, and set this
    object as the new value of the editor"""

    icon = Icon('plus-circle') # 'tango/16x16/actions/document-new.png'
    tooltip = _('create new')
    name = 'new_object'

    def model_run(self, model_context):
        from camelot.view import action_steps
        admin = model_context.field_attributes['admin']
        admin = yield action_steps.SelectSubclass(admin)
        obj = admin.entity()
        # Give the default fields their value
        admin.add(obj)
        admin.set_defaults(obj)
        yield action_steps.UpdateEditor('new_value', obj)
        yield action_steps.OpenFormView(obj, admin.get_proxy([obj]), admin)

class OpenObject(SelectObject):
    """Open the value of an editor in a form view"""

    icon = Icon('folder-open') # 'tango/16x16/places/folder.png'
    tooltip = _('open')
    name = 'open_object'

    def model_run(self, model_context):
        from camelot.view import action_steps
        obj = model_context.value
        if obj is not None:
            admin = model_context.field_attributes['admin']
            admin = admin.get_related_admin(obj.__class__)
            yield action_steps.OpenFormView(obj, admin.get_proxy([obj]), admin)

    def get_state(self, model_context):
        state = super(OpenObject, self).get_state(model_context)
        state.visible = (model_context.value is not None)
        state.enabled = (model_context.value is not None)
        return state

class ClearObject(OpenObject):
    """Set the new value of the editor to `None`"""

    icon = Icon('eraser') # 'tango/16x16/actions/edit-clear.png'
    tooltip = _('clear')
    name = 'clear_object'

    def model_run(self, model_context):
        from camelot.view import action_steps
        yield action_steps.UpdateEditor('selected_object', None)

    def get_state(self, model_context):
        state = super(ClearObject, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        return state

class UploadFile(FieldAction):
    """Upload a new file into the storage of the field"""

    icon = Icon('plus') # 'tango/16x16/actions/list-add.png'
    tooltip = _('Attach file')
    file_name_filter = 'All files (*)'
    name = 'attach_file'

    def model_run(self, model_context):
        from camelot.view import action_steps
        filenames = yield action_steps.SelectFile(self.file_name_filter)
        storage = model_context.field_attributes['storage']
        for file_name in filenames:
            # the storage cannot checkin empty file names
            if not file_name:
                continue
            remove = False
            if model_context.field_attributes.get('remove_original'):
                reply = yield action_steps.MessageBox(
                    text = _('Do you want to remove the original file?'),
                    icon = QtWidgets.QMessageBox.Warning,
                    title = _('The file will be stored.'),
                    standard_buttons = [QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes]
                    )
                if reply == QtWidgets.QMessageBox.Yes:
                    remove = True
            yield action_steps.UpdateProgress(text='Attaching file')
            stored_file = storage.checkin(file_name)
            yield action_steps.UpdateEditor('value', stored_file, propagate=True)
            if remove:
                os.remove(file_name)

    def get_state(self, model_context):
        state = super(UploadFile, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        state.enabled = (state.enabled is True) and (model_context.value is None)
        state.visible = (model_context.value is None)
        return state

class DetachFile(FieldAction):
    """Set the new value of the editor to `None`, leaving the
    actual file in the storage alone"""

    icon = Icon('trash') # 'tango/16x16/actions/edit-delete.png'
    tooltip = _('Detach file')
    message_title = _('Detach this file ?')
    message_text = _('If you continue, you will no longer be able to open this file.')
    name = 'detach_file'

    def model_run(self, model_context):
        from camelot.view import action_steps
        buttons = [QtWidgets.QMessageBox.Yes,QtWidgets.QMessageBox.No]
        answer = yield action_steps.MessageBox(title=self.message_title,
                                               text=self.message_text,
                                               standard_buttons=buttons)
        if answer == QtWidgets.QMessageBox.Yes:
            yield action_steps.UpdateEditor('value', None, propagate=True)

    def get_state(self, model_context):
        state = super(DetachFile, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        state.enabled = (state.enabled is True) and (model_context.value is not None)
        state.visible = (model_context.value is not None)
        return state

class OpenFile(FieldAction):
    """Open the file shown in the editor"""

    icon = Icon('folder-open') # 'tango/16x16/actions/document-open.png'
    tooltip = _('Open file')
    name = 'open_file'

    def model_run(self, model_context):
        from camelot.view import action_steps
        yield action_steps.UpdateProgress(text=_('Checkout file'))
        storage = model_context.field_attributes['storage']
        local_path = storage.checkout(model_context.value)
        yield action_steps.UpdateProgress(text=_('Open file'))
        yield action_steps.OpenFile(local_path)

    def get_state(self, model_context):
        state = super(OpenFile, self).get_state(model_context)
        state.enabled = model_context.value is not None
        state.visible = state.enabled
        return state

class SaveFile(OpenFile):
    """Copy the file shown in the editor to another location"""

    icon = Icon('save') # 'tango/16x16/actions/document-save-as.png'
    tooltip = _('Save as')
    name = 'file_save_as'

    def model_run(self, model_context):
        from camelot.view import action_steps
        stored_file = model_context.value
        storage = model_context.field_attributes['storage']
        local_path = yield action_steps.SaveFile()
        with open(local_path, 'wb') as destination:
            yield action_steps.UpdateProgress(text=_('Saving file'))
            destination.write(storage.checkout_stream(stored_file).read())


class AddNewObject( FieldAction ):
    """Add a new object to a collection. Depending on the
    'create_inline' field attribute, a new form is opened or not.

    This action will also set the default values of the new object, add the
    object to the session, and flush the object if it is valid.
    """

    shortcut = QtGui.QKeySequence.New
    icon = Icon('plus-circle') # 'tango/16x16/actions/document-new.png'
    tooltip = _('New')
    verbose_name = _('New')
    name = 'new_object'

    def get_admin(self, model_context):
        """
        Return the admin used for creating and handling the new entity instance with.
        By default, the given model_context's admin is used.
        """
        return model_context.admin

    def create_object(self, model_context, admin, session=None):
        """
        Create a new entity instance based on the given model_context as an instance of the given admin's entity.
        This is done in the given session, or the default session if it is not yet attached to a session.
        """
        new_object = admin.entity(_session=session)
        admin.add(new_object)
        # defaults might depend on object being part of a collection
        model_context.proxy.append(new_object)
        # Give the default fields their value
        admin.set_defaults(new_object)
        return new_object
        yield

    def model_run( self, model_context ):
        from camelot.view import action_steps
        admin = self.get_admin(model_context)
        if not admin.is_editable():
            raise RuntimeError("Action's model_run() called on noneditable entity")
        create_inline = model_context.field_attributes.get('create_inline', False)
        new_object = yield from self.create_object(model_context, admin)
        # if the object is valid, flush it, but in ancy case inform the gui
        # the object has been created
        yield action_steps.CreateObjects((new_object,))
        if not len(admin.get_validator().validate_object(new_object)):
            yield action_steps.FlushSession(model_context.session)
        # Even if the object was not flushed, it's now part of a collection,
        # so it's dependent objects should be updated
        yield action_steps.UpdateObjects(
            tuple(admin.get_depending_objects(new_object))
        )
        if create_inline is False:
            yield action_steps.OpenFormView(new_object, model_context.proxy, admin)


    def get_state( self, model_context ):
        state = super().get_state( model_context )
        # Check for editability on the level of the field
        if isinstance( model_context, FieldActionModelContext ):
            editable = model_context.field_attributes.get( 'editable', True )
            if editable == False:
                state.enabled = False
        # Check for editability on the level of the entity
        admin = model_context.admin
        if admin and not admin.is_editable():
            state.visible = False
            state.enabled = False
        return state

add_new_object = AddNewObject()

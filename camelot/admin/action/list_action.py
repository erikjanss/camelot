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

import codecs
import enum
import logging
import itertools

from ...core.item_model.proxy import AbstractModelFilter
from ...core.qt import QtGui, QtWidgets
from .base import Action, Mode, RenderHint

from camelot.admin.icon import Icon
from camelot.core.exception import UserException
from camelot.core.orm import Entity
from camelot.core.utils import ugettext, ugettext_lazy as _
from camelot.data.types import Types


LOGGER = logging.getLogger('camelot.admin.action.list_action')


class RowNumberAction( Action ):
    """
    An action that simply displays the current row number as its name to
    the user.
    """

    name = 'row_number'

    def get_state( self, model_context ):
        state = super(RowNumberAction, self).get_state(model_context)
        state.verbose_name = str(model_context.current_row + 1)
        return state

row_number_action = RowNumberAction()

class EditAction(Action):
    """A base class for an action that will modify the model, it will be
    disabled when the field_attributes for the relation field are set to 
    not-editable. It will also be disabled and hidden if the entity is set
    to be non-editable using __entity_args__ = { 'editable': False }.
    """

    name = 'edit_action'
    render_hint = RenderHint.TOOL_BUTTON

    class Message(enum.Enum):

        no_single_selection = _('Can only select 1 line')
        select_2_lines = _('Please select 2 lines')
        entity_not_rank_based = '{} has no rank column registered'
        incompatible_rank_dimension = _('The selected lines are not part of the same rank dimension')

    def get_state( self, model_context ):
        state = super( EditAction, self ).get_state( model_context )
        # Check for editability on the level of the field
        editable = model_context.field_attributes.get('editable', True)
        if editable == False:
            state.enabled = False
        # Check for editability on the level of the entity
        admin = model_context.admin
        if admin and not admin.is_editable():
            state.visible = False
            state.enabled = False
        return state

    def model_run( self, model_context, mode ):
        admin = model_context.admin
        if not admin.is_editable():
            raise RuntimeError("Action's model_run() called on noneditable entity")

class CloseList(Action):
    """
    Close the currently open table view
    """

    render_hint = RenderHint.TOOL_BUTTON

    icon = Icon('backspace')
    tooltip = _('Close')
    name = 'close'
    shortcut = QtGui.QKeySequence.StandardKey.Close

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield action_steps.CloseView()

close_list = CloseList()

class ListLabel(Action):
    """
    A simple action that displays the name of the table
    """

    render_hint = RenderHint.LABEL
    name = 'label'

    def get_state(self, model_context):
        state = super().get_state(model_context)
        state.verbose_name = str(model_context.admin.get_verbose_name_plural())
        return state

list_label = ListLabel()

class OpenFormView(Action):
    """Open a form view for the current row of a list."""
    
    shortcut = QtGui.QKeySequence.StandardKey.Open
    icon = Icon('folder') # 'tango/16x16/places/folder.png'
    tooltip = _('Open')
    # verbose name is set to None to avoid displaying it in the vertical
    # header of the table view
    verbose_name = None
    name = 'open_form_view'

    def get_object(self, model_context, mode):
        assert mode is not None
        # Workaround for windows, pass row + objId in mode
        row, objId = mode
        obj = model_context.get_object(row)
        if id(obj) != objId:
            raise UserException('Could not open correct form')
        return obj

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        obj = self.get_object(model_context, mode)
        yield action_steps.OpenFormView(
            obj, model_context.admin, model_context.proxy
        )

    def get_state( self, model_context ):
        state = Action.get_state(self, model_context)
        state.verbose_name = str()
        return state

open_form_view = OpenFormView()

class DuplicateSelection( EditAction ):
    """Duplicate the selected rows in a table"""
    
    # no shortcut here, as this is too dangerous if the user
    # presses the shortcut without being aware of the consequences
    icon = Icon('copy') # 'tango/16x16/actions/edit-copy.png'
    #icon = Icon('clone') # 'tango/16x16/actions/edit-copy.png'
    tooltip = _('Duplicate')
    verbose_name = _('Duplicate')
    name = 'duplicate_selection'

    def model_run( self, model_context, mode ):
        from camelot.view import action_steps
        super().model_run(model_context, mode)
        admin = model_context.admin
        if model_context.selection_count > 1:
            raise UserException(self.Message.no_single_selection.value)
        for obj in model_context.get_selection():
            new_object = admin.copy(obj)
            model_context.proxy.append(new_object)
            yield action_steps.CreateObjects([new_object])
            if not len(admin.get_validator().validate_object(new_object)):
                updated_objects = set(admin.get_depending_objects(new_object))
                yield action_steps.UpdateObjects(updated_objects)
                yield action_steps.FlushSession(model_context.session)
            else:
                yield action_steps.OpenFormView(new_object, admin)

    def get_state(self, model_context):
        state = super().get_state(model_context)
        if model_context.selection_count <= 0:
            state.enabled = False
        return state

duplicate_selection = DuplicateSelection()


class DeleteSelection( EditAction ):
    """Delete the selected rows in a table"""
    
    shortcut = QtGui.QKeySequence.StandardKey.Delete
    name = 'delete_selection'
    icon = Icon('trash') # 'tango/16x16/places/user-trash.png'
    tooltip = _('Delete')
    verbose_name = _('Delete')

    def model_run( self, model_context, mode ):
        from camelot.view import action_steps
        super().model_run(model_context, mode)
        admin = model_context.admin
        if model_context.selection_count <= 0:
            return

        # Check if all objects to removed are permitted to do so,
        # and raised otherwise.
        objects_to_remove = list( model_context.get_selection() )
        for obj in objects_to_remove:
            admin.deletable_or_raise(obj)

        answer = yield action_steps.MessageBox(
            title = ugettext('Remove %s %s ?')%( model_context.selection_count, ugettext('rows') ),
            icon = Icon('question'), 
            standard_buttons = [QtWidgets.QMessageBox.StandardButton.Yes, QtWidgets.QMessageBox.StandardButton.No], 
            text = ugettext('If you continue, they will no longer be accessible.'),
            hide_progress = True,
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        #
        # it might be impossible to determine the depending objects once
        # the object has been removed from the collection
        #
        depending_objects = set()
        for o in objects_to_remove:
            depending_objects.update( set( admin.get_depending_objects( o ) ) )
        for i, obj in enumerate( objects_to_remove ):
            yield action_steps.UpdateProgress( i + 1,
                                               (1 if self.remove_only() else 2) * model_context.selection_count,
                                               _('Removing') )
            #
            # We should not update depending objects that have
            # been deleted themselves
            #
            try:
                depending_objects.remove( obj )
            except KeyError:
                pass
            model_context.proxy.remove(obj)
        if not self.remove_only():
            yield action_steps.DeleteObjects(objects_to_remove)
            for i, obj in enumerate( objects_to_remove ):
                yield action_steps.UpdateProgress( model_context.selection_count + i + 1,
                                                   2 * model_context.selection_count,
                                                   _('Removing') )
                model_context.admin.delete(obj)
        else:
            yield action_steps.RefreshItemView(model_context)
        yield action_steps.UpdateObjects(depending_objects)
        yield action_steps.FlushSession( model_context.session )

    def remove_only(self):
        return False

    def get_state(self, model_context):
        state = super().get_state(model_context)
        if model_context.selection_count <= 0:
            state.enabled = False
        return state

delete_selection = DeleteSelection()

class AbstractToPrevious(object):

    render_hint = RenderHint.TOOL_BUTTON
    shortcut = QtGui.QKeySequence.StandardKey.MoveToPreviousPage
    icon = Icon('step-backward') # 'tango/16x16/actions/go-previous.png'
    tooltip = _('Previous')
    verbose_name = _('Previous')
    
class AbstractToFirst(object):

    render_hint = RenderHint.TOOL_BUTTON
    shortcut = QtGui.QKeySequence.StandardKey.MoveToStartOfDocument
    icon = Icon('fast-backward') # 'tango/16x16/actions/go-first.png'
    tooltip = _('First')
    verbose_name = _('First')

class ToFirstRow(AbstractToFirst, Action):
    """Move to the first row in a table"""

    name = 'to_first'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield action_steps.ToFirstRow()

to_first_row = ToFirstRow()

class AbstractToNext(object):

    render_hint = RenderHint.TOOL_BUTTON
    shortcut = QtGui.QKeySequence.StandardKey.MoveToNextPage
    icon = Icon('step-forward') # 'tango/16x16/actions/go-next.png'
    tooltip = _('Next')
    verbose_name = _('Next')
    
class AbstractToLast(object):

    render_hint = RenderHint.TOOL_BUTTON
    shortcut = QtGui.QKeySequence.StandardKey.MoveToEndOfDocument
    icon = Icon('fast-forward') # 'tango/16x16/actions/go-last.png'
    tooltip = _('Last')
    verbose_name = _('Last')
    
class ToLastRow(AbstractToLast, Action):
    """Move to the last row in a table"""

    name = 'to_last'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield action_steps.ToLastRow()

to_last_row = ToLastRow()

class SelectAll(Action):
    """Select all rows in a table"""
    
    verbose_name = _('Select &All')
    shortcut = QtGui.QKeySequence.StandardKey.SelectAll
    tooltip = _('Select all rows in the table')
    name = 'select_all'

select_all = SelectAll()

class ImportFromFile( EditAction ):
    """Import a csv file in the current table"""

    render_hint = RenderHint.TOOL_BUTTON
    verbose_name = _('Import from file')
    icon = Icon('file-import') # 'tango/16x16/mimetypes/text-x-generic.png'
    tooltip = _('Import from file')
    name = 'import'

    def model_run( self, model_context, mode ):
        import os.path
        import chardet
        from camelot.view import action_steps
        from camelot.view.import_utils import ( UnicodeReader, 
                                                RowData, 
                                                RowDataAdmin,
                                                XlsReader,
                                                ColumnMapping,
                                                ColumnMappingAdmin )
        super().model_run(model_context, mode)
        admin = model_context.admin
        file_names = yield action_steps.SelectFile()
        for file_name in file_names:
            yield action_steps.UpdateProgress( text = _('Reading data') )
            #
            # read the data into temporary row_data objects
            #
            if os.path.splitext( file_name )[-1] in ('.xls', '.xlsx'):
                items = list(XlsReader(file_name))
            else:
                detected = chardet.detect(open(file_name, 'rb').read())['encoding']
                enc = detected or 'utf-8'
                items = list(UnicodeReader(codecs.open(file_name, encoding=enc), encoding = enc ))
            collection = [ RowData(i, row_data) for i, row_data in enumerate( items ) ]
            if len( collection ) < 1:
                raise UserException( _('No data in file' ) )
            #
            # select columns to import
            #
            default_fields = [field for field in admin.get_columns()
                              if admin.get_field_attributes(field).get('editable', True)]
            mappings = []
            # 
            # it should be possible to select not editable fields, to be able to
            # import foreign keys, these are not editable by default, it might
            # be better to explicitly allow foreign keys, but this info is not
            # in the field attributes
            #
            all_fields = [(f,str(entity_fa['name'])) for f,entity_fa in 
                          admin.get_all_fields_and_attributes().items() if entity_fa.get('from_string')]
            all_fields.sort(key=lambda field_tuple:field_tuple[1])
            for i, default_field in itertools.zip_longest(range(len(all_fields)),
                                                          default_fields):
                mappings.append(ColumnMapping(i, items, default_field))
            
    
            column_mapping_admin = ColumnMappingAdmin(admin,
                                                      field_choices=all_fields)
    
            change_mappings = action_steps.ChangeObjects(mappings, 
                                                         column_mapping_admin)
            change_mappings.title = _('Select import column')
            change_mappings.subtitle = _('Select for each column in which field it should be imported')
            yield change_mappings
            #
            # validate the temporary data
            #
            row_data_admin = RowDataAdmin(admin, mappings)
            yield action_steps.ChangeObjects( collection, row_data_admin )
            #
            # Ask confirmation
            #
            yield action_steps.MessageBox( icon = Icon('question'),
                                           title = _('Proceed with import'), 
                                           text = _('Importing data cannot be undone,\n'
                                                    'are you sure you want to continue') )
            #
            # import the temporary objects into real objects
            #
            with model_context.session.begin():
                for i,row in enumerate(collection):
                    new_entity_instance = admin.entity()
                    for field_name in row_data_admin.get_columns():
                        attributes = row_data_admin.get_field_attributes(field_name)
                        original_field_name = attributes['original_field']
                        from_string = attributes.get('from_string')
                        assert from_string is not None, '{} with {} has no from string attribute'.format(field_name, original_field_name)
                        setattr(
                            new_entity_instance,
                            original_field_name,
                            from_string(getattr(row, field_name))
                        )
                    admin.add( new_entity_instance )
                    # in case the model is a collection proxy, the new objects should
                    # be appended
                    model_context.proxy.append(new_entity_instance)
                    yield action_steps.UpdateProgress( i + 1, len( collection ), _('Importing data') )
                yield action_steps.FlushSession( model_context.session )
            yield action_steps.Refresh()
        
import_from_file = ImportFromFile()

class FieldValue(object):
    """
    Abstract helper class for the `ReplaceFieldContents` action to configure
    the field values for a certain delegate.
    """

    def __init__(self, value):
        self.value = value

class ReplaceFieldContents( EditAction ):
    """Select a field an change the content for a whole selection"""

    verbose_name = _('Replace field contents')
    tooltip = _('Replace the content of a field for all rows in a selection')
    icon = Icon('edit') # 'tango/16x16/actions/edit-find-replace.png'
    message = _('Field is not editable')
    resolution = _('Only select editable rows')
    shortcut = QtGui.QKeySequence.StandardKey.Replace
    name = 'replace'

    def get_state(self, model_context):
        state = super().get_state(model_context)
        if model_context.selection_count <= 0:
            state.enabled = False
            return state
        state.modes = []
        for key, attributes in model_context.admin.get_all_fields_and_attributes().items():
            if attributes.get('change_value_admin') is None:
                continue
            state.modes.append(Mode(key, attributes['name']))
        return state

    def model_run( self, model_context, selected_field ):
        from camelot.view import action_steps
        super().model_run(model_context, selected_field)
        if selected_field is not None:
            admin = model_context.admin
            field_attributes = admin.get_field_attributes(selected_field)
            field_value = FieldValue(None)
            change_object = action_steps.ChangeObject(
                field_value, field_attributes['change_value_admin']
            )
            change_object.title = _('Replace field contents')
            yield change_object
            yield action_steps.UpdateProgress(text=_('Replacing field'))
            dynamic_field_attributes = admin.get_dynamic_field_attributes
            with model_context.session.begin():
                for obj in model_context.get_selection():
                    dynamic_fa = list(dynamic_field_attributes(obj, [selected_field]))[0]
                    if dynamic_fa.get('editable', True) == False:
                        raise UserException(self.message, resolution=self.resolution)
                    admin.set_field_value(obj, selected_field, field_value.value)
                    # dont rely on the session to update the gui, since the objects
                    # might not be in a session
                yield action_steps.UpdateObjects(model_context.get_selection())
            yield action_steps.FlushSession(model_context.session)

replace_field_contents = ReplaceFieldContents()

class FilterValue(object):
    """
    Abstract helper class for the `SetFilters` action to configure the filter values
    for a certain filter strategy and operator.
    The dimension of these filter values (remaining operands) depends on the arity of the operator.
    This class also provides functionality to associate implementations of :class: `camelot.admin.action.list_filter.AbstractFilterStrategy`
    with implementations of this FilterValue interface; either by defining them as an innner Value class, or directly using the :method register: method.
    Using the :method for_strategy: the concrete registered FilterValue class for a certain filter strategy class can be retrieved afterwards.
    """
    filter_strategy = None
    _filter_values = {}

    def __init__(self, strategy, operator, value_1=None, value_2=None):
        assert isinstance(strategy, self.filter_strategy)
        self.strategy = strategy
        self.operator = operator
        self.value_1 = value_1
        self.value_2 = value_2
        self._other_values = []

    @property
    def operator_prefix(self):
        return str(self.operator.prefix)

    @property
    def operator_infix(self):
        if self.operator.infix is not None:
            return str(self.operator.infix)

    def get_operands(self):
        operands = (self.value_1, self.value_2, *self._other_values)
        # Determine appropriate number of operands based on the maximum arity of the operator (-1 because the filtered attribute is an operand as well).
        # The arity's maximum may be undefined (e.g. for multi-ary operators), in which case the operands should not be sliced.
        if self.operator.arity.maximum is not None:
            return operands[0:self.operator.arity.maximum-1]
        return [op for op in operands if op is not None]

    def set_operands(self, *operands):
        for i, operand in enumerate(operands[:2], start=1):
            if i == 1: self.value_1 = operand
            if i == 2: self.value_2 = operand
        self._other_values = operands[2:]

    @classmethod
    def for_strategy(cls, filter_strategy):
        """
        Get the default :class:`FilterValue` class for the given specific filter
        strategy class, return None, if not known.  The FilterValue
        should either be registered through the :meth:`register` method or be
        defined as an inner class with name :keyword:`Value` of the filter strategy.

        :param filter_strategy: a subclass of :class: `camelot.admin.action.list_filter.AbstractFilterStrategy`
        """
        from camelot.admin.action.list_filter import AbstractFilterStrategy
        assert issubclass(filter_strategy, AbstractFilterStrategy)
        try:
            return cls._filter_values[filter_strategy]
        except KeyError:
            for strategy_cls in filter_strategy.__mro__:
                if issubclass(strategy_cls, AbstractFilterStrategy) and strategy_cls.name == filter_strategy.name:
                    value_class = cls._filter_values.get(strategy_cls, None)
                    if value_class is None:
                        if hasattr(strategy_cls, 'Value'):
                            value_class = strategy_cls.Value
                            value_class.filter_strategy = filter_strategy
                            break
                    else:
                        break
            else:
                raise Exception('Could not construct a default filter value class')
            cls._filter_values[filter_strategy] = value_class
            return value_class

    @classmethod
    def register(cls, filter_strategy, value_class):
        """
        Associate a certain FilterValue class with a filter strategy.
        This FilterValue will be used as default.

        :param filter_strategy: :class:`camelot.admin.action.list_filter.AbstractFilterStrategy`
        :param value_class: a subclass of `FilterValue.`
        """
        assert value_class.filter_strategy == filter_strategy
        cls._filter_values[filter_strategy] = value_class

class SetFilters(Action, AbstractModelFilter):
    """
    Apply a set of filters on a list.
    This action differs from those in `list_filter` in the sense that it will
    pop up a dialog to configure a complete filter and wont allow the user
    to apply filters from within its widget.
    """

    shortcut = QtGui.QKeySequence.StandardKey.FindNext
    render_hint = RenderHint.TOOL_BUTTON
    verbose_name = _('Find')
    tooltip = _('Filter the data')
    icon = Icon('filter')
    name = 'filter'

    def get_filter_strategies(self, model_context, priority_level=None):
        """:return: a list of field strategies the user can select."""
        filter_strategies = list(model_context.admin.get_field_filters(priority_level).items())
        filter_strategies.sort(key=lambda choice:(choice[1].priority_level.value, str(choice[1].get_verbose_name())))
        return filter_strategies

    def model_run( self, model_context, mode ):
        from camelot.view import action_steps

        filter_values = model_context.proxy.get_filter(self) or {}
        if mode == '__clear':
            new_filter_values = {}
        elif mode is None:
            new_filter_values = {}
        else:
            from camelot.admin.action.list_filter import Operator, Many2OneFilter, One2ManyFilter
            operator_name, filter_field_name = mode.split('-')
            filter_strategies = model_context.admin.get_field_filters()
            filter_strategy = filter_strategies.get(filter_field_name)
            filter_field_strategy = filter_strategy.get_field_strategy()
            filter_value_cls = FilterValue.for_strategy(type(filter_field_strategy))
            filter_value_admin = model_context.admin.get_related_admin(filter_value_cls)
            filter_operator = Operator[operator_name]
            filter_value = filter_value_cls(filter_field_strategy, filter_operator)

            # The filter values should only be updated by the user in case of multi-ary filter operators,
            # which requires filter values to be entered as the additional operands.
            # Unary operators can be applied directly, as the filter attribute is the only operand.
            if filter_operator.arity.minimum > 1:
                # The Many2OneFilter needs a selection of Entity objects to filter the foreign key relationship with.
                # So let the user select one, and programmatically set the filter value to the selected entity's id.
                if isinstance(filter_field_strategy, (Many2OneFilter, One2ManyFilter)):
                    admin = filter_field_strategy.admin or model_context.admin.get_related_admin(filter_field_strategy.entity)
                    query = admin.get_query()
                    objects = yield action_steps.SelectObjects(query, admin)
                    filter_value.set_operands(*objects)
                # Other multi-ary operator filter strategies require some filter value(s) from the user to be filled in:
                else:
                    # In case there was already an active filter present for the same field and operator,
                    # set the active operands as the default filter values for the user to manipulate:
                    if filter_field_name in filter_values:
                        (existing_operator, *existing_operands) = filter_values[filter_field_name]
                        if existing_operator == filter_operator:
                            filter_value.set_operands(*existing_operands)
                    step = action_steps.ChangeObject(filter_value, filter_value_admin)
                    step.title = ugettext('Filter {}').format(filter_field_strategy.get_verbose_name())
                    yield step

            operands = filter_value.get_operands()
            new_filter_values = {k:v for k,v in filter_values.items()}
            new_filter_values[filter_field_name] = (filter_field_strategy, filter_value.operator, *operands)

        if filter_values != new_filter_values:
            model_context.proxy.filter(self, new_filter_values)
            yield action_steps.RefreshItemView(model_context)
        new_state = self._get_state(model_context, new_filter_values)
        yield action_steps.UpdateActionsState(model_context, {self: new_state})

    def decorate_query(self, query, values):
        # Previously, the query was decorated with the the string-based filter value tuples by applying them to the query using filter_by.
        # This created problems though, as the filters are applied to the query's current zero joinpoint, which changes after every applied join to the joined entity.
        # This caused filters in some cases being tried to applied to the wrong entity.
        # Therefore we turn the filter values into entity descriptors condition clauses using the query's entity zero, which should always be the correct one.
        clauses = []
        for name, (filter_strategy, operator, *operands) in values.items():
            filter_clause = filter_strategy.get_clause(query, operator, *operands)
            if filter_clause is not None:
                clauses.append(filter_clause)
        return query.filter(*clauses)

    def _get_state(self, model_context, filter_value):
        state = super(SetFilters, self).get_state(model_context)
        state.modes = modes = []
        if len(filter_value) is not None:
            state.notification = True
        # Only show clear filter mode if any filters are active
        if len(filter_value):
            modes.extend([Mode('__clear', _('Clear filter'), icon=Icon('minus-circle'))])
        selected_mode_names = [op.name + '-' + field for field, (_, op, *_) in filter_value.items()]
        for name, filter_strategy in self.get_filter_strategies(model_context):
            for op in filter_strategy.get_operators():
                mode_name = op.name + '-' + name
                icon = Icon('check-circle') if mode_name in selected_mode_names else None
                modes.append(Mode(mode_name, '{} {}'.format(filter_strategy.get_verbose_name(), op.verbose_name), icon=icon))
        return state

    def get_state(self, model_context):
        filter_value = model_context.proxy.get_filter(self) or {}
        return self._get_state(model_context, filter_value)

set_filters = SetFilters()


class AddNewObjectMixin(object):
    
    def create_object(self, model_context, admin, mode=None, session=None):
        """
        Create a new entity instance based on the given model_context as an instance of the given admin's entity.
        This is done in the given session, or the default session if it is not yet attached to a session.
        """
        secondary_discriminator_values = []
        if issubclass(admin.get_subsystem_cls(), Entity):
            from camelot.view import action_steps
            # In case the subsystem class has secondary related entity discriminators defined,
            # prompt the user to select entity instances to instantiate them before creating the object
            # itself, as they are required to retrieve the correct registered facade class.
            for entity_cls in admin.entity.get_secondary_discriminator_types():
                related_admin = admin.get_related_admin(entity_cls)
                selected_object = yield action_steps.SelectObject(related_admin.get_query(), related_admin)
                if selected_object is not None:
                    secondary_discriminator_values.append(selected_object)

            # Resolve admin again based on the now fully qualified discriminator values, to create the object with.
            admin = self.get_admin(model_context, mode, secondary_discriminator_values)
            new_object = admin.entity(_session=session)
        else:
            new_object = admin.entity()
        admin.add(new_object)
        # defaults might depend on object being part of a collection
        self.get_proxy(model_context, admin).append(admin.get_subsystem_object(new_object))
        # Give the default fields their value
        admin.set_defaults(new_object)

        # Set the discriminator value, if defined.
        admin.set_discriminator_value(new_object, mode, *secondary_discriminator_values)
        return new_object
        yield

    def model_run( self, model_context, mode ):
        from camelot.view import action_steps
        admin = self.get_admin(model_context, mode)
        assert admin is not None # required by vfinance/test/test_facade/test_asset.py
        if not admin.is_editable():
            raise RuntimeError("Action's model_run() called on noneditable entity")
        create_inline = model_context.field_attributes.get('create_inline', False)
        new_object = yield from self.create_object(model_context, admin, mode)
        discriminator_value = admin.get_discriminator_value(new_object)
        if discriminator_value is not None:
            # Resolve admin again after the new object has been created, as it may
            # have gotten secondary discriminators set.
            # So only at this point we can be certain of the discriminatory value.
            (primary_discriminator_value, *secondary_discriminator_values) = discriminator_value
            admin = self.get_admin(model_context, mode=primary_discriminator_value, secondary_discriminators=secondary_discriminator_values)
        subsystem_object = admin.get_subsystem_object(new_object)
        # if the object is valid, flush it, but in ancy case inform the gui
        # the object has been created
        yield action_steps.CreateObjects((subsystem_object,))
        if not len(admin.get_validator().validate_object(new_object)):
            admin.flush(new_object)
        # Even if the object was not flushed, it's now part of a collection,
        # so it's dependent objects should be updated
        yield action_steps.UpdateObjects(
            tuple(admin.get_depending_objects(new_object))
        )
        if create_inline is False:
            yield from self.edit_object(new_object, model_context, admin)

    def edit_object(self, new_object, model_context, admin):
        from camelot.view import action_steps
        yield action_steps.OpenFormView(new_object, admin)

    def get_modes(self, model_context):
        """
        Determine and/or construct the applicable modes for this add action based on the given model_context.
        This will either be the explicitly set modes, or modes constructed based on registered/set types for the admin.
        """
        admin = self.get_admin(model_context)
        if not self.modes and admin is not None and issubclass(admin.entity, Entity):

            # TODO: for now, dynamic or custom types behaviour has been moved to a types field_attributes on one2many relation fields.
            #       To be determined if this is the best way to go...
            types = model_context.field_attributes.get('types')
            if types is not None:
                # Verify the custom type set is a subset of the registered types.
                assert isinstance(types, Types)
                assert all([t.name in admin.entity.__types__.__members__ for t in types])
                return types.get_modes()

            polymorphic_types = admin.entity.get_polymorphic_types()
            if admin.entity.__types__ is not None:
                return admin.entity.__types__.get_modes()

            elif polymorphic_types is not None:
                return polymorphic_types.get_modes()

        return self.modes

    def get_default_admin(self, model_context, mode=None):
        raise NotImplementedError

    def get_admin(self, model_context, mode=None, secondary_discriminators=tuple()):
        """
        Return the admin used for creating and handling the new entity instance with.
        """
        admin = self.get_default_admin(model_context, mode)
        if (admin is not None) and (mode is not None):
            facade_cls = admin.entity.get_cls_by_discriminator(mode, *secondary_discriminators)
            if facade_cls is not None:
                return admin.get_related_admin(facade_cls)
        return admin

class AddNewObject( AddNewObjectMixin, EditAction ):
    """Add a new object to a collection. Depending on the
    'create_inline' field attribute, a new form is opened or not.

    This action will also set the default values of the new object, add the
    object to the session, and flush the object if it is valid.
    """

    shortcut = QtGui.QKeySequence.StandardKey.New
    icon = Icon('plus-circle') # 'tango/16x16/actions/document-new.png'
    tooltip = _('New')
    verbose_name = _('New')
    name = 'new_object'

    def get_default_admin(self, model_context, mode=None):
        return model_context.admin

    def get_proxy(self, model_context, admin):
        return model_context.proxy

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield from super().model_run(model_context, mode)
        # Scroll to last row so that the user sees the newly added object in the list.
        yield action_steps.ToLastRow(wait_for_new_row=True)

    def get_state(self, model_context):
        state = super().get_state(model_context)
        state.modes = self.get_modes(model_context)
        return state

add_new_object = AddNewObject()

class RemoveSelection(DeleteSelection):
    """Remove the selected objects from a list without deleting them"""
    
    shortcut = None
    tooltip = _('Remove')
    verbose_name = _('Remove')
    icon = Icon('minus') # 'tango/16x16/actions/list-remove.png'
    name = 'remove_selection'

    def remove_only(self):
        return True

remove_selection = RemoveSelection()


class Stretch(Action):

    render_hint = RenderHint.STRETCH
    name = 'stretch'

stretch = Stretch()

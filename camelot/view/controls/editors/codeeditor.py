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

import six

from ....core.qt import QtGui, QtCore, QtWidgets, Qt
from camelot.view.model_thread import object_thread

from .customeditor import CustomEditor, set_background_color_palette, draw_tooltip_visualization

class PartEditor(QtWidgets.QLineEdit):

    def __init__(self, mask, max_length, first = False, last = False):
        super(PartEditor, self).__init__()
        self.setInputMask(mask)
        self.firstPart = first
        self.last = last
        self.max_length = max_length
        self.textEdited.connect( self.text_edited )

    def focusInEvent(self, event):
        super(PartEditor, self).focusInEvent(event)
        self.setCursorPosition(0)
        
    def focusOutEvent(self, event):
        super(PartEditor, self).focusOutEvent(event)
        if self.isModified():
            self.editingFinished.emit()
        
    def paintEvent(self, event):
        super(PartEditor, self).paintEvent(event)
        if self.firstPart and self.toolTip():
            draw_tooltip_visualization(self)

    @QtCore.qt_slot(str)
    def text_edited(self, text):
        if self.cursorPosition() == self.max_length:
            if self.last:
                self.editingFinished.emit()
            else:
                self.focusNextChild()
        
class CodeEditor(CustomEditor):

    def __init__(self, parent=None, parts=['99','AA'], editable=True, field_name='code', **kwargs):
        CustomEditor.__init__(self, parent)
        self.setObjectName( field_name )
        self.setSizePolicy( QtGui.QSizePolicy.Preferred,
                            QtGui.QSizePolicy.Fixed )        
        self.value = None
        self.parts = parts
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)
        for i, part in enumerate(parts):
            part_length = len(part)
            editor = PartEditor(part, part_length, i==0, i==(len(parts)-1) )
            editor.setFocusPolicy( Qt.StrongFocus )
            if i==0:
                self.setFocusProxy( editor )
            if not editable:
                editor.setEnabled(False)
            space_width = editor.fontMetrics().size(Qt.TextSingleLine, 'A').width()
            editor.setMaximumWidth(space_width*(part_length+1))
            editor.setObjectName( 'part_%i'%i )
            layout.addWidget(editor)
            editor.editingFinished.connect(self.emit_editing_finished)
        self.setLayout(layout)

    @QtCore.qt_slot()
    def emit_editing_finished(self):
        # if we don't do an isModified check here, spurious editingFinished
        # signals are generated by the QLineEdit itself, maybe because of the
        # pattern.  this can lead to spurious data entry in a form, therefor this
        # check is necessary
        for editor in self._get_part_editors():
            if editor.isModified():
                self.editingFinished.emit()
                return

    def _get_part_editors( self ):
        for i in range( len( self.parts ) ):
            part_editor = self.findChild( QtWidgets.QWidget,
                                          'part_%s'%i )
            yield part_editor
            
    def set_enabled(self, editable=True):
        for editor in self._get_part_editors():
            editor.setEnabled(editable)

    def set_value(self, value):
        assert object_thread( self )
        value = CustomEditor.set_value(self, value)
        if value:
            old_value = self.get_value()
            # value might be a collection container, with a custom __eq__, so it
            # should be on the left hand side
            if value!=old_value:
                for part_editor, part in zip( self._get_part_editors(), value ):
                    part_editor.setText(six.text_type(part))
        else:
            for part_editor in self._get_part_editors():
                part_editor.setText('')

    def get_value(self):
        assert object_thread( self )
        value = []
        for part_editor in self._get_part_editors():
            value.append( six.text_type( part_editor.text() ) )
        return CustomEditor.get_value(self) or value

    def set_background_color(self, background_color):
        for editor in self._get_part_editors():
            set_background_color_palette( editor, background_color )
            
    def set_field_attributes(self, **kwargs):
        super(CodeEditor, self).set_field_attributes(**kwargs)
        self.set_enabled(kwargs.get('editable', False))
        tooltip = six.text_type(kwargs.get('tooltip') or '')
        self.layout().itemAt(0).widget().setToolTip(tooltip)



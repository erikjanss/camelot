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

from camelot.core.item_model import PreviewRole
from camelot.core.qt import Qt, QtCore
from camelot.core.naming import initial_naming_context
from camelot.view.utils import local_datetime_format

from dataclasses import dataclass
from typing import Optional

from .customdelegate import DocumentationMetaclass
from .datedelegate import DateDelegate


@dataclass
class DateTimeDelegate(DateDelegate, metaclass=DocumentationMetaclass):

    editable: bool = True

    @classmethod
    def value_to_string(cls, value, locale, field_attributes) -> Optional[str]:
        if value is not None:
            return str(QtCore.QDateTime(value).toString(local_datetime_format()))

    @classmethod
    def get_standard_item(cls, locale, model_context):
        item = super().get_standard_item(locale, model_context)
        cls.set_item_editability(model_context, item, False)
        if model_context.value is not None:
            item.roles[Qt.ItemDataRole.EditRole] = initial_naming_context._bind_object(model_context.value)
            item.roles[PreviewRole] = cls.value_to_string(model_context.value, locale, model_context.field_attributes)
        return item

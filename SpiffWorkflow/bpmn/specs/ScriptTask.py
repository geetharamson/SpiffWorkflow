# -*- coding: utf-8 -*-

# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301  USA

from .BpmnSpecMixin import BpmnSpecMixin
from ...task import TaskState
from ...specs.Simple import Simple
from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException


class ScriptTask(Simple, BpmnSpecMixin):

    """
    Task Spec for a bpmn:scriptTask node.
    """

    def __init__(self, wf_spec, name, script, **kwargs):
        """
        Constructor.

        :param script: the script that must be executed by the script engine.
        """
        super(ScriptTask, self).__init__(wf_spec, name, **kwargs)
        self.script = script

    def _on_complete_hook(self, task):
        if task.workflow._is_busy_with_restore():
            return
        assert not task.workflow.read_only
        try:
            task.workflow.script_engine.execute(task, self.script, task.data)
        except Exception as e:
            # set state to WAITING (because it is definitely not COMPLETED)
            # and raise WorkflowException pointing to this task because
            # maybe upstream someone will be able to handle this situation
            task._set_state(TaskState.WAITING)
            if isinstance(e, WorkflowTaskExecException):
                raise e
            else:
                raise WorkflowTaskExecException(
                    task, 'Error during script execution:' + str(e), e)
        super(ScriptTask, self)._on_complete_hook(task)

    def serialize(self, serializer):
        return serializer.serialize_script_task(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer.deserialize_script_task(wf_spec, s_state)


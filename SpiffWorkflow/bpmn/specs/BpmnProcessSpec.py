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

from copy import deepcopy
import logging

from SpiffWorkflow.bpmn.exceptions import WorkflowDataException
from ...task import TaskState
from .UnstructuredJoin import UnstructuredJoin
from ...specs.Simple import Simple
from ...specs.WorkflowSpec import WorkflowSpec


data_log = logging.getLogger('spiff.data')

class _EndJoin(UnstructuredJoin):

    def _check_threshold_unstructured(self, my_task, force=False):
        # Look at the tree to find all ready and waiting tasks (excluding
        # ourself). The EndJoin waits for everyone!
        waiting_tasks = []
        for task in my_task.workflow.get_tasks(TaskState.READY | TaskState.WAITING):
            if task.thread_id != my_task.thread_id:
                continue
            if task.task_spec == my_task.task_spec:
                continue

            is_mine = False
            w = task.workflow
            if w == my_task.workflow:
                is_mine = True
            while w and w.outer_workflow != w:
                w = w.outer_workflow
                if w == my_task.workflow:
                    is_mine = True
            if is_mine:
                waiting_tasks.append(task)

        return force or len(waiting_tasks) == 0, waiting_tasks

    def _on_complete_hook(self, my_task):
        super(_EndJoin, self)._on_complete_hook(my_task)
        my_task.workflow.data.update(my_task.data)


class BpmnDataSpecification:

    def __init__(self, name, description=None):
        """
        :param name: the name of the task (the BPMN ID)
        :param description: the task description (the BPMN name)
        """
        self.name = name
        self.description = description or name
        # In the future, we can add schemas defining the objects here.

    def get(self, my_task):
        """Copy a value form the workflow data to the task data."""
        if self.name not in my_task.workflow.data:
            message = f"Data object '{self.name}' " \
                      f"does not exist and can not be read."
            raise WorkflowDataException(message, my_task, data_input=self)
        my_task.data[self.name] = deepcopy(my_task.workflow.data[self.name])

    def set(self, my_task):
        """Copy a value from the task data to the workflow data"""
        if self.name not in my_task.data:
            message = f"A Data Object  '{self.name}' " \
                      f"could not be set, it does not exist in the task data"
            raise WorkflowDataException(message, my_task, data_output=self)
        my_task.workflow.data[self.name] = deepcopy(my_task.data[self.name])
        del my_task.data[self.name]
        data_log.info(f'Set workflow variable {self.name}', extra=my_task.log_info())

    def copy(self, source, destination, data_input=False, data_output=False):
        """Copy a value from one task to another."""
        if self.name not in source.data:
            message = f"'{self.name}' was not found in the task data"
            raise WorkflowDataException(
                message,
                source,
                data_input=self if data_input else None,
                data_output=self if data_output else None,
            )
        destination.data[self.name] = deepcopy(source.data[self.name])


class BpmnProcessSpec(WorkflowSpec):
    """
    This class represents the specification of a BPMN process workflow. This
    specialises the standard Spiff WorkflowSpec class with a few extra methods
    and attributes.
    """

    def __init__(self, name=None, description=None, filename=None, svg=None):
        """
        Constructor.

        :param svg: This provides the SVG representation of the workflow as an
        LXML node. (optional)
        """
        super(BpmnProcessSpec, self).__init__(name=name, filename=filename)
        self.end = _EndJoin(self, '%s.EndJoin' % (self.name))
        end = Simple(self, 'End')
        end.follow(self.end)
        self.svg = svg
        self.description = description
        self.data_inputs = []
        self.data_outputs = []
        self.data_objects = {}
        self.correlation_keys = {}

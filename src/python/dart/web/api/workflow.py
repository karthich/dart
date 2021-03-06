import json
from flask import Blueprint, request, current_app
from flask.ext.jsontools import jsonapi
from dart.model.datastore import DatastoreState
from dart.model.query import Filter, Operator

from dart.model.workflow import Workflow, WorkflowState, WorkflowInstanceState
from dart.service.filter import FilterService
from dart.service.workflow import WorkflowService
from dart.service.trigger import TriggerService
from dart.web.api.entity_lookup import fetch_model


api_workflow_bp = Blueprint('api_workflow', __name__)


@api_workflow_bp.route('/datastore/<datastore>/workflow', methods=['POST'])
@fetch_model
@jsonapi
def post_workflow(datastore):
    """ :type datastore: dart.model.datastore.Datastore """
    workflow = Workflow.from_dict(request.get_json())
    workflow.data.datastore_id = datastore.id
    workflow.data.engine_name = datastore.data.engine_name
    if datastore.data.state == DatastoreState.ACTIVE:
        # only templated datastores can use concurrencies > 1
        workflow.data.concurrency = 1
    workflow = workflow_service().save_workflow(workflow)
    return {'results': workflow.to_dict()}


@api_workflow_bp.route('/workflow', methods=['GET'])
@fetch_model
@jsonapi
def find_workflows():
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    filters = [filter_service().from_string(f) for f in json.loads(request.args.get('filters', '[]'))]
    workflows = workflow_service().query_workflows(filters, limit, offset)
    return {
        'results': [d.to_dict() for d in workflows],
        'limit': limit,
        'offset': offset,
        'total': workflow_service().query_workflows_count(filters)
    }


@api_workflow_bp.route('/workflow/<workflow>', methods=['GET'])
@fetch_model
@jsonapi
def get_workflow(workflow):
    return {'results': workflow.to_dict()}


@api_workflow_bp.route('/workflow/<workflow>/instance', methods=['GET'])
@fetch_model
@jsonapi
def find_workflow_instances(workflow):
    return _find_workflow_instances(workflow)


@api_workflow_bp.route('/workflow/instance/<workflow_instance>', methods=['GET'])
@fetch_model
@jsonapi
def get_workflow_instance(workflow_instance):
    return {'results': workflow_instance.to_dict()}


@api_workflow_bp.route('/workflow/instance', methods=['GET'])
@fetch_model
@jsonapi
def find_instances():
    return _find_workflow_instances()


def _find_workflow_instances(workflow=None):
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    filters = [filter_service().from_string(f) for f in json.loads(request.args.get('filters', '[]'))]
    if workflow:
        filters.append(Filter('workflow_id', Operator.EQ, workflow.id))
    workflow_instances = workflow_service().query_workflow_instances(filters, limit, offset)
    return {
        'results': [d.to_dict() for d in workflow_instances],
        'limit': limit,
        'offset': offset,
        'total': workflow_service().query_workflow_instances_count(filters)
    }


@api_workflow_bp.route('/workflow/<workflow>', methods=['PUT'])
@fetch_model
@jsonapi
def put_workflow(workflow):
    """ :type workflow: dart.model.workflow.Workflow """
    updated_workflow = Workflow.from_dict(request.get_json())
    if updated_workflow.data.state not in [WorkflowState.ACTIVE, WorkflowState.INACTIVE]:
        return {'results': 'ERROR', 'error_message': 'state must be ACTIVE or INACTIVE'}, 400, None
    workflow = workflow_service().update_workflow_state(workflow, updated_workflow.data.state)
    return {'results': workflow.to_dict()}


@api_workflow_bp.route('/workflow/<workflow>/do-manual-trigger', methods=['POST'])
@fetch_model
@jsonapi
def trigger_workflow(workflow):
    """ :type workflow: dart.model.workflow.Workflow """
    wf = workflow
    if wf.data.state != WorkflowState.ACTIVE:
        return {'results': 'ERROR', 'error_message': 'This workflow is not ACTIVE'}, 400, None

    states = [WorkflowInstanceState.QUEUED, WorkflowInstanceState.RUNNING]
    if workflow_service().find_workflow_instances_count(wf.id, states) >= wf.data.concurrency:
        return {'results': 'ERROR', 'error_message': 'Max concurrency reached: %s' % wf.data.concurrency}, 400, None

    trigger_service().trigger_workflow_async(workflow.id)
    return {'results': 'OK'}


@api_workflow_bp.route('/workflow/<workflow>', methods=['DELETE'])
@fetch_model
@jsonapi
def delete_workflow(workflow):
    workflow_service().delete_workflow(workflow.id)
    return {'results': 'OK'}


@api_workflow_bp.route('/workflow/<workflow>/instance', methods=['DELETE'])
@fetch_model
@jsonapi
def delete_workflow_instances(workflow):
    workflow_service().delete_workflow_instances(workflow.id)
    return {'results': 'OK'}


def filter_service():
    """ :rtype: dart.service.filter.FilterService """
    return current_app.dart_context.get(FilterService)


def workflow_service():
    """ :rtype: dart.service.workflow.WorkflowService """
    return current_app.dart_context.get(WorkflowService)


def trigger_service():
    """ :rtype: dart.service.trigger.TriggerService """
    return current_app.dart_context.get(TriggerService)

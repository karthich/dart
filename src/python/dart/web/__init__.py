import logging
import logging.config
import os

from flask import Flask, jsonify

from dart.config.config import configuration
from dart.context.context import AppContext
from dart.context.database import db
from dart.model.exception import DartValidationException
from dart.web.api.graph import api_graph_bp
from dart.web.ui.admin.admin import admin_bp
from dart.web.api.action import api_action_bp
from dart.web.api.dataset import api_dataset_bp
from dart.web.api.datastore import api_datastore_bp
from dart.web.api.engine import api_engine_bp
from dart.web.api.event import api_event_bp
from dart.web.api.schema import api_schema_bp
from dart.web.api.trigger import api_trigger_bp
from dart.web.api.workflow import api_workflow_bp
from dart.web.api.subscription import api_subscription_bp
from dart.web.ui.index import index_bp

_logger = logging.getLogger(__name__)


api_version_prefix = '/api/1'
config_path = os.environ['DART_CONFIG']
config = configuration(config_path)
logging.config.dictConfig(config['logging'])
_logger.info('loaded config from path: %s' % config_path)


app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')

app.dart_context = AppContext(
    config=config,
    exclude_injectable_module_paths=[
        'dart.message.engine_listener',
        'dart.message.trigger_listener',
        'dart.message.subscription_listener'
    ]
)

app.config.update(config['flask'])
db.init_app(app)

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_dataset_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_datastore_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_engine_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_action_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_trigger_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_workflow_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_subscription_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_event_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_schema_bp, url_prefix=api_version_prefix)
app.register_blueprint(api_graph_bp, url_prefix=api_version_prefix)
app.register_blueprint(index_bp)


@app.errorhandler(DartValidationException)
def handle_dart_validation_exception(e):
    response = jsonify({'results': 'ERROR', 'error_message': e.message})
    response.status_code = 400
    return response


@app.after_request
def set_dart_version_cookie(response):
    response.set_cookie('dart.web.version', os.environ.get('DART_WEB_VERSION', 'unknown'))
    return response

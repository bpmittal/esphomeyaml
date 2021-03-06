import voluptuous as vol

from esphomeyaml.automation import ACTION_REGISTRY
import esphomeyaml.config_validation as cv
from esphomeyaml.const import CONF_DATA, CONF_DATA_TEMPLATE, CONF_ID, CONF_PASSWORD, CONF_PORT, \
    CONF_SERVICE, CONF_VARIABLES
from esphomeyaml.core import CORE
from esphomeyaml.cpp_generator import ArrayInitializer, Pvariable, add, get_variable, process_lambda
from esphomeyaml.cpp_helpers import setup_component
from esphomeyaml.cpp_types import Action, App, Component, StoringController, esphomelib_ns

api_ns = esphomelib_ns.namespace('api')
APIServer = api_ns.class_('APIServer', Component, StoringController)
HomeAssistantServiceCallAction = api_ns.class_('HomeAssistantServiceCallAction', Action)
KeyValuePair = api_ns.class_('KeyValuePair')
TemplatableKeyValuePair = api_ns.class_('TemplatableKeyValuePair')

CONFIG_SCHEMA = vol.Schema({
    cv.GenerateID(): cv.declare_variable_id(APIServer),
    vol.Optional(CONF_PORT, default=6053): cv.port,
    vol.Optional(CONF_PASSWORD, default=''): cv.string_strict,
}).extend(cv.COMPONENT_SCHEMA.schema)


def to_code(config):
    rhs = App.init_api_server()
    api = Pvariable(config[CONF_ID], rhs)

    if config[CONF_PORT] != 6053:
        add(api.set_port(config[CONF_PORT]))
    if config.get(CONF_PASSWORD):
        add(api.set_password(config[CONF_PASSWORD]))

    setup_component(api, config)


BUILD_FLAGS = '-DUSE_API'


def lib_deps(config):
    if CORE.is_esp32:
        return 'AsyncTCP@1.0.1'
    elif CORE.is_esp8266:
        return 'ESPAsyncTCP@1.1.3'
    raise NotImplementedError


CONF_HOMEASSISTANT_SERVICE = 'homeassistant.service'
LOGGER_LOG_ACTION_SCHEMA = vol.Schema({
    cv.GenerateID(): cv.use_variable_id(APIServer),
    vol.Required(CONF_SERVICE): cv.string,
    vol.Optional(CONF_DATA): vol.Schema({
        cv.string: cv.string,
    }),
    vol.Optional(CONF_DATA_TEMPLATE): vol.Schema({
        cv.string: cv.string,
    }),
    vol.Optional(CONF_VARIABLES): vol.Schema({
        cv.string: cv.lambda_,
    }),
})


@ACTION_REGISTRY.register(CONF_HOMEASSISTANT_SERVICE, LOGGER_LOG_ACTION_SCHEMA)
def homeassistant_service_to_code(config, action_id, arg_type, template_arg):
    for var in get_variable(config[CONF_ID]):
        yield None
    rhs = var.make_home_assistant_service_call_action(template_arg)
    type = HomeAssistantServiceCallAction.template(arg_type)
    act = Pvariable(action_id, rhs, type=type)
    add(act.set_service(config[CONF_SERVICE]))
    if CONF_DATA in config:
        datas = [KeyValuePair(k, v) for k, v in config[CONF_DATA].items()]
        add(act.set_data(ArrayInitializer(*datas)))
    if CONF_DATA_TEMPLATE in config:
        datas = [KeyValuePair(k, v) for k, v in config[CONF_DATA_TEMPLATE].items()]
        add(act.set_data_template(ArrayInitializer(*datas)))
    if CONF_VARIABLES in config:
        datas = []
        for key, value in config[CONF_VARIABLES].items():
            for value_ in process_lambda(value, []):
                yield None
            datas.append(TemplatableKeyValuePair(key, value_))
        add(act.set_variables(ArrayInitializer(*datas)))
    yield act

import os
import warnings
from ruyaml import YAML
from typing import List
from pathlib import Path
from ruyaml.comments import ordereddict
from dynaconf import Dynaconf, Validator
from dynaconf.utils.boxing import DynaBox


def check_cml_env():
    return 'PREPROD'


ENCODING = 'utf-8'
ENV = check_cml_env()
ENV_VARS_SECTION = 'ENV_VARIABLES'
ROOT_PATH = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', '..', '..'))
YAML_PATH_MAPPING = {
    'UAT': os.path.join(ROOT_PATH, 'config', 'uat.yaml'),
    'PROD': os.path.join(ROOT_PATH, 'config', 'prod.yaml'),
    'PREPROD': os.path.join(ROOT_PATH, 'config', 'preprod.yaml'),
    'NO_CML': os.path.join(ROOT_PATH, 'config', 'no_cml.yaml')
}


def update(src_dict, dst_dict):
    for k, v in src_dict.items():
        if isinstance(v, dict):
            dst_dict[k] = update(v, dst_dict.get(k, ordereddict()))
        else:
            dst_dict[k] = v
    return dst_dict


class Config(Dynaconf):
    ALLOWED_EXTENSIONS = ['.yaml', '.yml']

    def __init__(self, 
                 settings_file: str = None, 
                 load_env_vars: bool = True,
                 validators: List[Validator] = None,
                 env_vars_key: str = ENV_VARS_SECTION,
                 apply_default_on_none: bool = True,
                 ):
        if settings_file is None:
            settings_file = YAML_PATH_MAPPING.get(ENV)

        self.validate_extension(settings_file)

        # TODO: Add in validators for certain sections in the config yaml that we think should always be there
        super().__init__(
            settings_file = settings_file, 
            validators = validators,
            apply_default_on_none = apply_default_on_none,
            core_loaders = ['YAML'],
        )
        
        if load_env_vars:
            self.set_env_vars(env_vars_key)

    def validate_extension(self, filepath: str):
        _, ext = os.path.splitext(filepath)
        if ext not in self.ALLOWED_EXTENSIONS:
            raise NotImplementedError(f'File type not supported for reading: {ext}')
        
    def set_env_vars(self, env_vars_key: str = ENV_VARS_SECTION):
        env_variables = getattr(self, env_vars_key, None)
        if env_variables is None:
            warnings.warn(
                f'Skip the setting of environment variables as {env_vars_key} section is not found in {self.settings_file}'
            )
            return

        for key, value in env_variables.items():
            os.environ[key] = str(value)

    def reload(self, settings_module = None, **kwargs):
        super().configure(settings_module, **kwargs)

    def to_yaml(self, filepath: str = None):
        if filepath is None:
            filepath = self.settings_file

        self.validate_extension(filepath)
        data = DynaBox(self._wrapped.as_dict(), box_settings = {}).to_dict()

        if Path(filepath).exists():
            with open(filepath, encoding = ENCODING) as f:
                commented_data = YAML().load(f)

        commented_data = update(data, commented_data)

        with open(filepath, 'wb') as f:
            YAML().dump(commented_data, f)


# TODO: monkeypatch YAML loader such that it allows us to read from HDFS also (low priority)

# TODO: reload and write to file should be user managed rather than by config as it is expensive to reload and write to file each time we update an attribute
# TODO: Fix the uppercase issue where dynaconf will uppercase all the first level attributes (known limitation that will be fixed in 4.0.0, live with it for now)
# TODO: known limitations, first level have to be uppercase
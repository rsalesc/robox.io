from typing import Dict, List, Optional
import importlib.resources
import typer
import functools
import pathlib
import importlib
from pydantic import BaseModel

from .console import console
from . import utils

app = typer.Typer(no_args_is_help=True)

APP_NAME = "codefreaker"
_RESOURCES_PKG = "resources"
_CONFIG_FILE_NAME = "default_config.json"


def format_vars(template: str, **kwargs) -> str:
    res = template
    for key, value in kwargs.items():
        key = key.replace("_", "-")
        res = res.replace(f"%{{{key}}}", value)
    return res


class Language(BaseModel):
    template: str
    file: str
    submitFile: Optional[str] = None
    preprocess: Optional[List[str]] = None
    exec: str

    def get_file(self, basename: str) -> str:
        return format_vars(self.file, problem_code=basename)

    def get_submit_file(self, file: str, basename: str) -> str:
        return format_vars(self.file, file=file, problem_code=basename)

    def get_template(self) -> str:
        template_path = get_app_path() / "templates" / self.template
        if not template_path.is_file():
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(get_default_template(self.template))
        return template_path.read_text()


class Config(BaseModel):
    defaultLanguage: str
    languages: Dict[str, Language]

    def get_default_language(self) -> Optional[Language]:
        return self.languages.get(self.defaultLanguage)

    def get_language(self, name: Optional[str] = None) -> Optional[Language]:
        return self.languages.get(name or self.defaultLanguage)


def get_app_path() -> pathlib.Path:
    app_dir = typer.get_app_dir(APP_NAME)
    return pathlib.Path(app_dir)


def get_default_template_path(template: str) -> pathlib.Path:
    with importlib.resources.as_file(
        importlib.resources.files(_RESOURCES_PKG) / "templates" / template
    ) as file:
        return file


def get_default_template(template: str) -> str:
    file = get_default_template_path(template)
    if file.is_file():
        return file.read_text()
    return ""


def get_default_config_path() -> pathlib.Path:
    with importlib.resources.as_file(
        importlib.resources.files(_RESOURCES_PKG) / _CONFIG_FILE_NAME
    ) as file:
        return file


def get_default_config() -> Config:
    return Config.model_validate_json(get_default_config_path().read_text())


def get_config_path() -> pathlib.Path:
    return get_app_path() / "config.json"


@functools.cache
def get_config() -> Config:
    config_path = get_config_path()
    if not config_path.is_file():
        utils.create_and_write(config_path, utils.model_json(get_default_config()))
    return Config.model_validate_json(config_path.read_text())


@app.command()
def path():
    get_config()  # Ensure config is created.
    console.print(get_config_path())


@app.command()
def list():
    console.print_json(utils.model_json(get_config()))


@app.command()
def reset():
    if not typer.confirm("Do you really want to reset your config to the default one?"):
        return
    cfg_path = get_config_path()
    cfg_path.unlink(missing_ok=True)
    get_config()  # Reset the config.

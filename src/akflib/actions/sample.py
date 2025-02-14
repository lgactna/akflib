from types import ModuleType
from typing import Any, ClassVar, Optional

from caselib.uco.core import Bundle

from akflib.translation.core import AKFModule, AKFModuleArgs, AKFModuleConfig


class SampleModuleArgs(AKFModuleArgs):
    arg1: str
    arg2: str


class SampleModuleConfig(AKFModuleConfig):
    config1: str = "default"


class SampleModule(AKFModule[SampleModuleArgs, SampleModuleConfig]):
    aliases = ["sample"]
    arg_model = SampleModuleArgs
    config_model = SampleModuleConfig

    dependencies: ClassVar[set[ModuleType]] = set()

    @classmethod
    def generate_code(
        cls, args: SampleModuleArgs, config: SampleModuleConfig, state: dict[str, Any]
    ) -> str:
        return f"print('Hello, world! My arguments are {args.arg1} and {args.arg2}')\n"

    @classmethod
    def execute(
        cls,
        args: SampleModuleArgs,
        config: SampleModuleConfig,
        state: dict[str, Any],
        bundle: Optional[Bundle] = None,
    ) -> None:
        print(f"Hello, world! My arguments are {args.arg1} and {args.arg2}")

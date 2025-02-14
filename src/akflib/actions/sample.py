import random
from typing import Any, ClassVar, Optional

from caselib.uco.core import Bundle

from akflib.translation.core import AKFModule, AKFModuleArgs, AKFModuleConfig
from akflib.translation.util import auto_format


class SampleModuleArgs(AKFModuleArgs):
    arg1: str
    arg2: str


class SampleModuleConfig(AKFModuleConfig):
    config1: str = "default"


class SampleModule(AKFModule[SampleModuleArgs, SampleModuleConfig]):
    aliases = ["sample"]
    arg_model = SampleModuleArgs
    config_model = SampleModuleConfig

    dependencies: ClassVar[set[str]] = {"random"}

    @classmethod
    def generate_code(
        cls, args: SampleModuleArgs, config: SampleModuleConfig, state: dict[str, Any]
    ) -> str:
        return auto_format(
            f'print(f\'I choose {{random.choice(("{args.arg1}", "{args.arg2}"))}}\')\n',
            state,
        )

    @classmethod
    def execute(
        cls,
        args: SampleModuleArgs,
        config: SampleModuleConfig,
        state: dict[str, Any],
        bundle: Optional[Bundle] = None,
    ) -> None:
        print(f"I choose {random.choice((args.arg1, args.arg2))}")

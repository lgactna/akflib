from types import ModuleType
from typing import Any, Optional, ClassVar

from caselib.uco.core import Bundle
from pydantic import BaseModel

from ..core.base import AKFModule

class SampleModuleArgs(BaseModel):
    arg1: str
    arg2: str
    
class SampleModuleConfig(BaseModel):
    config1: str = "default" 

class SampleModule(AKFModule):
    aliases: ClassVar[list[str]] = ["sample"]
    arg_model: ClassVar[BaseModel] = SampleModuleArgs    
    config_model: ClassVar[BaseModel] = SampleModuleConfig
    
    dependencies: ClassVar[set[ModuleType]] = set()
    
    @classmethod
    def generate_code(
        cls,
        args: dict[str, Any], 
        config: dict[str, Any],
        state: dict[str, Any]
    ) -> str:
        arg_obj, config_obj = cls._parse_args(args, config)
        
        return f"print('Hello, world! My arguments are')\n"
    
    @classmethod
    def execute(
        cls,
        args: dict[str, Any], 
        config: BaseModel,
        state: dict[str, Any],
        bundle: Optional[Bundle] = None
    ) -> None:
        arg_obj, config_obj = cls._parse_args(args, config)
        
        print("Hello, world!")

import abc
from typing import Any, ClassVar, Generic, Type, TypeVar

# from caselib.uco.core import Bundle
from pydantic import BaseModel

from akflib.core.hypervisor.base import HypervisorABC
from akflib.rendering.objs import AKFBundle


class AKFModuleArgs(abc.ABC, BaseModel):
    """
    Root for any module argument models.
    """

    pass


class NullArgs(AKFModuleArgs):
    """
    Explicit, default argument model for modules that don't require arguments.
    """

    pass


class AKFModuleConfig(abc.ABC, BaseModel):
    """
    Root for any module configuration models.
    """

    pass


class NullConfig(AKFModuleConfig):
    """
    Explicit, default configuration model for modules that don't require configuration.
    """

    pass


class AKFAction(BaseModel):
    """
    The definition for a single action as part of a larger scenario.

    This looks and feels similar to an Ansible task, in large part because it is.
    """

    # The name/description for this action.
    name: str

    # A dictionary of keys to values that will be passed as part of a global
    # configuration dictionary to each `AKFModule`. These override any
    # configuration keys set at the scenario level.
    config: dict[str, Any] = {}

    # The (qualified) module name to execute.
    module: str

    # The arguments to pass to the module. These will eventually be used to
    # instantiate the module's argument model, which is also a Pydantic BaseModel.
    args: dict[str, Any] = {}

    # TODO: have module resolution logic here, as well as all the typevar'd stuff?


class AKFScenario(BaseModel):
    """
    The definition for a declarative scenario.
    """

    # The name of the scenario.
    name: str

    # A description of the scenario.
    description: str

    # The individual or organization that authored the scenario.
    author: str

    # The seed to use with Python's `random` library. This should be set
    # for scenarios in which reproducibility is required.
    seed: str | None = None

    # A dictionary of keys to values that will be passed as part of a global
    # configuration dictionary to each `AKFModule`. Individual modules may
    # choose to ignore extra values.
    config: dict[str, Any] = {}

    # The set of Python modules (i.e. libraries) to import, in fully-qualified
    # form. This allows the translator to import all visible `AKFModule` classes
    # ahead of time, as well as verify that the necsesary libraries installed and
    # that the declared modules as part of the `actions` attribute exist.
    #
    # This also provides the translator the opportunity to create aliases,
    # (eliminating the need for full module qualification, in some cases) ahead
    # of time. Libraries declared later in the list override names from earlier
    # libraries. This is used to build a dictionary of valid module names to their
    # corresponding `AKFModule` class before attempting to run through the task list.
    libraries: list[str] = []

    # The list of actions to take in this scenario. Each action is a dictionary,
    # which is in turn converted to an AKFAction.
    actions: list[AKFAction] = []


# Note that type variables are not allowed in `ClassVar`, at least for mypy.
# I believe this use case (for abstract attributes) is valid, but isn't supported.
# See https://github.com/python/mypy/issues/5144
ArgsType = TypeVar("ArgsType", bound=AKFModuleArgs)
ConfigType = TypeVar("ConfigType", bound=AKFModuleConfig)


def check_required_attributes(cls: Type[Any], required_attributes: list[str]) -> None:
    """
    Check that subclasses have required attributes.
    """
    for attr in required_attributes:
        if not hasattr(cls, attr):
            raise TypeError(
                f"Can't instantiate abstract class {cls.__name__} "
                f"without required attribute '{attr}'"
            )


class AKFModule(abc.ABC, Generic[ArgsType, ConfigType]):
    """
    Abstract base classes for modules that can be invoked through the declarative
    system.
    """

    # The list of aliases for this module. This allows the module to be
    # referenced by more than one name. Note that this comes after the
    # fully-qualified syntax; for example, a module at `namespace.lib` with
    # an alias of `foo` can be referenced as `namespace.lib.foo`, in addition
    # to the original class name.
    aliases: ClassVar[list[str]]

    # The argument model for this module.
    #
    # In addition to allowing the module to parse arguments at runtime using
    # this model, it also serves as the "schema" for this module, indicating
    # the expected arguments.
    arg_model: Type[ArgsType]

    # The configuration model for this module. This is used to accept and parse
    # global configuration variables that are accepted by this module.
    config_model: Type[ConfigType]

    # The dependencies that must be imported for any code generated by this
    # module to function.
    dependencies: ClassVar[set[str]]

    @staticmethod
    def check_required_attributes(
        cls: Type[Any], required_attributes: list[str]
    ) -> None:
        """
        Check that subclasses have required attributes.
        """
        # Get class annotations
        annotations = getattr(cls, "__annotations__", {})

        for attr in required_attributes:
            # Check if attribute exists either as a value or as an annotation --
            # for concrete classes, we care that it has a value (hasattr), but
            # for abstract classes, we care that it has an annotation.
            #
            # In the strictest sense, we could check if the class is abstract
            # or not, but what matters is that you're aware of the attributes
            # to begin with, so we don't make a distinction.
            if not (hasattr(cls, attr) or attr in annotations):
                raise TypeError(
                    f"Can't instantiate abstract class {cls.__name__} "
                    f"without required attribute '{attr}'"
                )

    def __init_subclass__(cls) -> None:
        """
        Check that subclasses have required attributes.
        """
        super().__init_subclass__()

        REQUIRED_ATTRIBUTES = ["aliases", "arg_model", "config_model", "dependencies"]
        cls.check_required_attributes(cls, REQUIRED_ATTRIBUTES)

    @staticmethod
    def get_hypervisor_var(state: dict[str, Any]) -> str | None:
        """
        Extract the name of the currently specified hypervisor variable from the state
        dictionary.

        Returns None if the hypervisor variable is not set.
        """

        if result := state.get("akflib.hypervisor_var", None):
            assert isinstance(result, str)

        return result  # type: ignore[no-any-return]

    @staticmethod
    def get_hypervisor(state: dict[str, Any]) -> HypervisorABC | None:
        """
        Extract the currently specified hypervisor object from the state dictionary.

        Returns None if the hypervisor object is not set.
        """
        if result := state.get("akflib.hypervisor", None):
            assert isinstance(result, HypervisorABC)

        return result  # type: ignore[no-any-return]

    @staticmethod
    def get_akf_bundle_var(state: dict[str, Any]) -> str | None:
        """
        Extract the name of the currently specified AKFBundle variable from the state
        dictionary.

        Returns None if the AKFBundle variable name is not set.
        """

        if result := state.get("akflib.akf_bundle_var", None):
            assert isinstance(result, str)

        return result  # type: ignore[no-any-return]

    @staticmethod
    def get_akf_bundle(state: dict[str, Any]) -> AKFBundle | None:
        """
        Extract the currently specified AKFBundle variable from the state
        dictionary.

        Returns None if the AKFBundle variable is not set.
        """

        if result := state.get("akflib.akf_bundle", None):
            assert isinstance(result, AKFBundle)

        return result  # type: ignore[no-any-return]

    @classmethod
    @abc.abstractmethod
    def generate_code(
        cls, args: ArgsType, config: ConfigType, state: dict[str, Any]
    ) -> str:
        """
        Generate the code necessary to execute this module from the imperative
        paradigm (that is, a typical Python script).

        This method should take the arguments and global configuration objects and
        and generate valid Python code, with or without indentation, that can
        be inserted into a Python script.

        Code returned as a result of this function should contain a trailing newline.

        Additionally, it receives a state dictionary that can be used to modify
        the output of the code. For example, if a related module sets a state
        variable that indicates it is inside a `with` block, this module can
        indent and use the context manager accordingly.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def execute(
        cls,
        args: ArgsType,
        config: ConfigType,
        state: dict[str, Any],
    ) -> None:
        """
        Execute the code generated by this module.

        This method operates in the same manner as `generate_code`, except that
        it does not generate code; instead, it executes the actual code that would
        have been returned directly.
        """
        raise NotImplementedError

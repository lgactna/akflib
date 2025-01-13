import logging
import sys

from agent.server import AService, BService

logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# This uses the "mixins" approach (or rather, subservices) to effectively
# turn multiple services into a single service.
#
# The alternative is to basically import each unique service, one by one.
#
# See https://stackoverflow.com/questions/47561840/how-can-i-separate-the-functions-of-a-class-into-multiple-files
#
# Note that the disadvantage of this approach is that we can't really maintain subservice/
# application-specific state as well as ForTrace...? We can't really implement
# on_connect() in every single class, and I don't otherwise know if there's a way
# to maintain state within individual subservices. What do we lose by not having this?
class MainService(AService, BService):

    # Something that 4o spat out
    @classmethod
    def check_method_conflicts(cls):
        parent_classes = cls.__bases__
        method_sets = {class_obj: set(dir(class_obj)) for class_obj in parent_classes}

        # Find common methods
        common_methods = set.intersection(*method_sets.values())

        # Exclude methods common to all services
        common_methods -= {"exposed_get_service_aliases", "exposed_get_service_name"}

        # Exclude methods that are not services (requires the exposed_ convention)
        #
        # it is also possible to test if a method was decorated with a particular 
        # decorator as described here:
        """
        from some_library import external_decorator

        def my_decorator(func):
            @external_decorator
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper._is_my_decorator = True
            return wrapper

        @my_decorator
        def my_function():
            pass

        # Test if the function was decorated
        if hasattr(my_function, '_is_my_decorator'):
            print("Function is decorated")
        else:
            print("Function is not decorated")
        """
        common_methods = {
            method for method in common_methods if method.startswith("exposed_")
        }

        if common_methods:
            raise Exception(f"Method conflicts found: {common_methods}")


if __name__ == "__main__":
    # Check for exposed name conflicts (a runtime process that can probably
    # also be delegated to a linter, or perhaps our own pre-commit hook) -- this
    # fixes the disadvantage of not having a "built-in" method to check for
    # shadowed functions
    MainService.check_method_conflicts()

    from rpyc.utils.server import ThreadedServer

    logger.info("Starting server on port 18861")
    t = ThreadedServer(MainService, port=18861)
    t.start()

from abc import ABC, abstractmethod
import inspect
from typing import Dict, Generic, Type, TypeVar

from implicitdict import ImplicitDict

from monitoring.uss_qualifier import resources as resources_module


SpecificationType = TypeVar("SpecificationType", bound=ImplicitDict)


class Resource(ABC, Generic[SpecificationType]):
    @abstractmethod
    def __init__(self, specification: SpecificationType, **dependencies):
        """Create an instance of the resource.

        Concrete subclasses of Resource must implement their constructor according to this specification.

        :param specification: A serializable (subclass of implicitdict.ImplicitDict) specification for how to create the resource.
        :param dependencies: If this resource depends on any other resources, each of the other dependencies should be declared as an additional typed parameter to the constructor.  Each parameter type should be a class that is a subclass of Resource.
        """
        raise NotImplementedError(
            "A concrete resource type must implement __init__ method"
        )


def _resource_type_from_string(type_name: str) -> Type:
    resource_type = resources_module
    for component in type_name.split("."):
        if not hasattr(resource_type, component):
            raise ValueError(
                "Could not find {} defined in {} while trying to create resource type {}".format(
                    component, resource_type.__name__, type_name
                )
            )
        resource_type = getattr(resource_type, component)
    if not issubclass(resource_type, Resource):
        raise NotImplementedError(
            "Resource type {} is not a subclass of the Resource base class".format(
                resource_type
            )
        )
    return resource_type


class ResourceDeclaration(ImplicitDict):
    resource_type: str
    """Type of resource, expressed as a Python class name qualified relative to this `resources` module"""

    dependencies: Dict[str, str] = {}
    """Mapping of dependency parameter (additional argument to concrete resource constructor) to `name` of resource to use"""

    specification: dict = {}
    """Specification of resource; format is the SpecificationType that corresponds to the Resource `type`"""

    def make_resource(self, resource_pool: Dict[str, Resource]) -> Resource:
        resource_type = _resource_type_from_string(self.resource_type)

        constructor_signature = inspect.signature(resource_type.__init__)
        specification_type = None
        constructor_args = {}
        for arg_name, arg in constructor_signature.parameters.items():
            if arg_name == "self":
                continue
            if arg_name == "specification":
                specification_type = arg.annotation
                continue
            if arg_name not in self.dependencies:
                raise ValueError(
                    'Resource declaration for {} is missing a source for dependency "{}"'.format(
                        self.resource_type, arg
                    )
                )
            if self.dependencies[arg_name] not in resource_pool:
                raise ValueError(
                    'Resource "{}" was not found in the resource pool when trying to create resource "{}" ({})'.format(
                        self.dependencies[arg], self.name, self.type
                    )
                )
            constructor_args[arg_name] = resource_pool[self.dependencies[arg_name]]
        if specification_type is not None:
            constructor_args["specification"] = ImplicitDict.parse(
                self.specification, specification_type
            )

        return resource_type(**constructor_args)


class ResourceCollection(ImplicitDict):
    resource_declarations: Dict[str, ResourceDeclaration]
    """Mapping of globally (within resource collection) unique name identifying a resource to the declaration of that resource"""

    def create_resources(self) -> Dict[str, Resource]:
        resource_pool: Dict[str, Resource] = {}

        resources_created = 1
        while resources_created > 0:
            resources_created = 0
            for name, declaration in self.resource_declarations.items():
                if name in resource_pool:
                    continue
                unmet_dependencies = sum(
                    1 if d in resource_pool else 0 for d in declaration.dependencies
                )
                if unmet_dependencies == 0:
                    resource_pool[name] = declaration.make_resource(resource_pool)

        if len(resource_pool) != len(self.resource_declarations):
            uncreated_resources = [
                r for r in self.resource_declarations if r not in resource_pool
            ]
            raise ValueError(
                "Could not create resources: {} (do you have circular dependencies?)".format(
                    ", ".join(uncreated_resources)
                )
            )

        return resource_pool
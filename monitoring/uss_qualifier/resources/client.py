from implicitdict import ImplicitDict
from typing import List

from monitoring.monitorlib.clients.logger.client import LoggerClient
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.resources.resource import Resource

class InterUSSLoggingProvider(ImplicitDict):
    base_url: str
    """The base URL at which the participant is hosting its implementation of the InterUSS automated testing versioning API."""

class LoggerProviderSpecification(ImplicitDict):
    interuss: InterUSSLoggingProvider = None
    """Populated when the version provider is using the InterUSS automated testing versioning API to provide versioning information."""


class LoggerProvidersSpecification(ImplicitDict):
    instances: List[LoggerProviderSpecification]

class LoggerProvidersResource(Resource[LoggerProvidersSpecification]):
    logger_providers: LoggerClient

    def __init__(
        self,
    ):
        #TODO: use auth in future implementation
        session = UTMClientSession(
                    #TODO: change URL to dynamic variable
                    prefix_url='http://localhost:8082',
                )
        self.logger_providers = InterUSSLoggingProvider(session=session)
           

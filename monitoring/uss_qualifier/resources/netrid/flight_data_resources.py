import copy
import json
import uuid
from datetime import timedelta
from typing import List, Optional, Self

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    TestFlightDetails,
    RIDAircraftState,
)

from monitoring.monitorlib.rid_automated_testing.injection_api import (
    TestFlight,
)
from monitoring.uss_qualifier.resources.files import load_dict, load_content
from monitoring.uss_qualifier.resources.netrid.flight_data import (
    FlightDataSpecification,
    FlightRecordCollection,
)
from monitoring.uss_qualifier.resources.netrid.simulation.adjacent_circular_flights_simulator import (
    generate_aircraft_states,
)
from monitoring.uss_qualifier.resources.netrid.simulation.kml_flights import (
    get_flight_records,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightDataResource(Resource[FlightDataSpecification]):
    _flight_start_delay: timedelta
    flight_collection: FlightRecordCollection

    def __init__(self, specification: FlightDataSpecification, resource_origin: str):
        super(FlightDataResource, self).__init__(specification, resource_origin)
        if "record_source" in specification:
            self.flight_collection = ImplicitDict.parse(
                load_dict(specification.record_source),
                FlightRecordCollection,
            )
        elif "adjacent_circular_flights_simulation_source" in specification:
            self.flight_collection = generate_aircraft_states(
                specification.adjacent_circular_flights_simulation_source
            )
        elif "kml_source" in specification:
            kml_content = load_content(specification.kml_source.kml_file)
            self.flight_collection = get_flight_records(
                kml_content,
                specification.kml_source.reference_time.datetime,
                specification.kml_source.random_seed,
            )
        else:
            raise ValueError(
                "A source of flight data was not identified in the specification for a FlightDataSpecification:\n"
                + json.dumps(specification, indent=2)
            )
        self._flight_start_delay = specification.flight_start_delay.timedelta

    def get_test_flights(self) -> List[TestFlight]:
        t0 = arrow.utcnow() + self._flight_start_delay

        test_flights: List[TestFlight] = []

        for flight in self.flight_collection.flights:
            dt = t0 - flight.reference_time.datetime

            telemetry: List[RIDAircraftState] = []
            for state in flight.states:
                shifted_state = RIDAircraftState(state)
                shifted_state.timestamp = StringBasedDateTime(
                    state.timestamp.datetime + dt
                )
                telemetry.append(shifted_state)

            details = TestFlightDetails(
                effective_after=StringBasedDateTime(t0),
                details=flight.flight_details,
            )

            test_flights.append(
                TestFlight(
                    injection_id=str(uuid.uuid4()),
                    telemetry=telemetry,
                    details_responses=[details],
                    aircraft_type=flight.aircraft_type,
                )
            )

        return test_flights

    def truncate_flights_duration(self, duration: timedelta) -> Self:
        """
        Ensures that the injected flight data will only contain telemetry for at most the specified duration.

        Returns a new, updated instance. The original instance remains unchanged.

        Intended to be used for simulating the disconnection of a networked UAS.
        """
        self_copy = copy.deepcopy(self)
        for flight in self_copy.flight_collection.flights:
            latest_allowed_end = flight.reference_time.datetime + duration
            # Keep only the states within the allowed duration
            flight.states = [
                state
                for state in flight.states
                if state.timestamp.datetime <= latest_allowed_end
            ]
        return self_copy


class FlightDataStorageSpecification(ImplicitDict):
    flight_record_collection_path: Optional[str]
    """Path, usually ending with .json, at which to store the FlightRecordCollection"""

    geojson_tracks_path: Optional[str]
    """Path (folder) in which to store track_XX.geojson files, 1 for each flight"""


class FlightDataStorageResource(Resource[FlightDataStorageSpecification]):
    storage_configuration: FlightDataStorageSpecification

    def __init__(
        self, specification: FlightDataStorageSpecification, resource_origin: str
    ):
        super(FlightDataStorageResource, self).__init__(specification, resource_origin)
        self.storage_configuration = specification

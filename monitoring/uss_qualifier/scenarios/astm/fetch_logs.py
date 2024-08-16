from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from implicitdict import ImplicitDict
from monitoring.monitorlib.clients.versioning.client import VersionQueryError
from monitoring.monitorlib.fetch import QueryType, Query
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.logger.client import LoggerProvidersResource
from monitoring.uss_qualifier.resources.versioning import SystemIdentityResource
from monitoring.uss_qualifier.resources.versioning.client import (
    VersionProvidersResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from uas_standards.interuss.automated_testing.versioning.api import GetVersionResponse


@dataclass
class _LogsInfo(object):
    log: dict

class FetchLog(TestScenario):
    def __init__(
        self,
    ):
        super(FetchLog, self).__init__()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Fetch log from USS")

        #test_env_versions, prod_env_versions = self._get_versions()
        #self._evaluate_versions(test_env_versions, prod_env_versions)
        #self._evaluate_consistency(context, test_env_versions)

        self._get_log()

        self.end_test_case()
        self.end_test_scenario()

    def _get_log(
        self,
    ) -> dict:
        try:
            resp = LoggerProvidersResource().get_log('2024-08-14T13:57:29Z', '2024-08-16T13:57:29Z')
            
        except(ValueError, KeyError):
            pass

        return resp.log
                        

    def _evaluate_log(
        self,
        log:dict
    ):
        self.begin_test_step("Evaluating log structure")

        mismatched_participants = []
        matched_participants = []
        for participant_id in test_env_versions:
            if participant_id not in prod_env_versions:
                self.record_note(
                    f"{participant_id} prod system",
                    f"The production version of {participant_id}'s system could not be determined (perhaps because of means of determining the production version was not provided)'",
                )
                continue
            if (
                test_env_versions[participant_id].version
                == prod_env_versions[participant_id].version
            ):
                matched_participants.append(participant_id)
            else:
                mismatched_participants.append(participant_id)
        for participant_id in matched_participants:
            with self.check(
                "Test software version matches production",
                participants=participant_id,
            ) as check:
                check.record_passed()

        if len(mismatched_participants) == 1:
            self.record_note(
                "Participant testing new software", mismatched_participants[0]
            )
            # Move technically-mismatched participant over to matched participants to prepare for one-at-a-time check
            matched_participants.append(mismatched_participants[0])
            mismatched_participants.clear()

        # Record appropriate failures for participants with mismatched software versions (when there are 2 or more)
        mismatch_timestamps = []
        for participant_id in mismatched_participants:
            timestamps = [
                test_env_versions[participant_id].query.timestamp,
                prod_env_versions[participant_id].query.timestamp,
            ]
            with self.check(
                "Test software version matches production", participants=participant_id
            ) as check:
                check.record_failed(
                    summary="Test environment software version does not match production",
                    details=f"{participant_id} indicated version '{test_env_versions[participant_id].version}' in the test environment and version '{prod_env_versions[participant_id].version}' in the production environment.",
                    query_timestamps=timestamps,
                )
            mismatch_timestamps.extend(timestamps)

        # Record one-at-a-time check result
        if mismatched_participants:
            with self.check(
                "At most one participant is testing a new software version",
                participants=mismatched_participants,
            ) as check:
                check.record_failed(
                    summary="Test environment software version does not match production",
                    details=f"At most, only one participant may be testing a software version that differs from production, but {', '.join(mismatched_participants)} all had differing versions between environments.",
                    query_timestamps=mismatch_timestamps,
                )
        else:
            with self.check(
                "At most one participant is testing a new software version",
                participants=matched_participants,
            ) as check:
                check.record_passed()

        self.end_test_step()

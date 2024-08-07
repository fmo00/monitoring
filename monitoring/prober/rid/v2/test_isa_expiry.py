"""Test ISAs aren't returned after they expire."""

import datetime

from monitoring.monitorlib.delay import sleep
from uas_standards.astm.f3411.v22a.api import OPERATIONS, OperationID
from uas_standards.astm.f3411.v22a.constants import Scope

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v2
from monitoring.prober.infrastructure import register_resource_type
from . import common


ISA_PATH = OPERATIONS[OperationID.SearchIdentificationServiceAreas].path
ISA_TYPE = register_resource_type(347, "ISA")


def test_ensure_clean_workspace_v2(ids, session_ridv2):
    resp = session_ridv2.get(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.ServiceProvider
    )
    if resp.status_code == 200:
        version = resp.json()["service_area"]["version"]
        resp = session_ridv2.delete(
            "{}/{}/{}".format(ISA_PATH, ids(ISA_TYPE), version),
            scope=Scope.ServiceProvider,
        )
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, resp.content


@default_scope(Scope.ServiceProvider)
def test_create(ids, session_ridv2):
    time_start = datetime.datetime.now(datetime.UTC)
    time_end = time_start + datetime.timedelta(seconds=5)

    resp = session_ridv2.put(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)),
        json={
            "extents": {
                "volume": {
                    "outline_polygon": {
                        "vertices": common.VERTICES,
                    },
                    "altitude_lower": rid_v2.make_altitude(20),
                    "altitude_upper": rid_v2.make_altitude(400),
                },
                "time_start": rid_v2.make_time(time_start),
                "time_end": rid_v2.make_time(time_end),
            },
            "uss_base_url": "https://example.interuss.org/ridv2",
        },
    )
    assert resp.status_code == 200, resp.content


@default_scope(Scope.DisplayProvider)
def test_valid_immediately(ids, session_ridv2):
    # The ISA is still valid immediately after we create it.
    resp = session_ridv2.get("{}/{}".format(ISA_PATH, ids(ISA_TYPE)))
    assert resp.status_code == 200, resp.content


def test_sleep_5_seconds():
    # But if we wait 5 seconds it will expire...
    sleep(5, "if we wait 5 seconds, the ISA of interest will expire")


@default_scope(Scope.DisplayProvider)
def test_returned_by_id(ids, session_ridv2):
    # We can get it explicitly by ID
    resp = session_ridv2.get("{}/{}".format(ISA_PATH, ids(ISA_TYPE)))
    assert resp.status_code == 200, resp.content


@default_scope(Scope.DisplayProvider)
def test_not_returned_by_search(ids, session_ridv2):
    # ...but it's not included in a search.
    resp = session_ridv2.get("{}?area={}".format(ISA_PATH, common.GEO_POLYGON_STRING))
    assert resp.status_code == 200, resp.content
    assert ids(ISA_TYPE) not in [x["id"] for x in resp.json()["service_areas"]]


@default_scope(Scope.DisplayProvider)
def test_delete(ids, session_ridv2):
    resp = session_ridv2.get(
        "{}/{}".format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.DisplayProvider
    )
    assert resp.status_code == 200
    version = resp.json()["service_area"]["version"]
    resp = session_ridv2.delete(
        "{}/{}/{}".format(ISA_PATH, ids(ISA_TYPE), version), scope=Scope.ServiceProvider
    )
    assert resp.status_code == 200, resp.content

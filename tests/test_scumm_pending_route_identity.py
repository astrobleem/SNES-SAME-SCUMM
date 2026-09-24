from __future__ import annotations

import unittest

from tools.validate_scumm_pending_room_request_nexen import (
    require_request_route_identity,
)


class PendingRequestRouteIdentityTests(unittest.TestCase):
    def test_far_profile_cannot_be_reported_as_near(self) -> None:
        identity = {"explicit_environment": {"SAME_BUILD_M24RB": "1"}}
        require_request_route_identity(identity, "far")
        with self.assertRaisesRegex(RuntimeError, "compiled route is far"):
            require_request_route_identity(identity, "near")

    def test_near_profile_cannot_be_reported_as_far(self) -> None:
        identity = {"explicit_environment": {"SAME_BUILD_M24RB": "0"}}
        require_request_route_identity(identity, "near")
        with self.assertRaisesRegex(RuntimeError, "compiled route is near"):
            require_request_route_identity(identity, "far")

    def test_controller_conformance_selects_far_route(self) -> None:
        identity = {"explicit_environment": {
            "SAME_BUILD_M24RB": "0",
            "SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE": "1",
        }}
        require_request_route_identity(identity, "far")
        with self.assertRaisesRegex(RuntimeError, "compiled route is far"):
            require_request_route_identity(identity, "near")

    def test_missing_identity_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no explicit build environment"):
            require_request_route_identity({}, "near")
        with self.assertRaisesRegex(RuntimeError, "omits SAME_BUILD_M24RB"):
            require_request_route_identity({"explicit_environment": {}}, "near")


if __name__ == "__main__":
    unittest.main()

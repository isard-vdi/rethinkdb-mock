"""
IsardVDI APIv4 Compatibility Tests

This test suite validates that rethinkdb-mock correctly handles all the database
query patterns used in IsardVDI's APIv4 implementation. These tests are based on
analysis of IsardVDI's actual test files and GitLab CI configuration.

IsardVDI uses complex patterns including:
- Role-based access control with set intersections
- Conditional logic with r.branch and default values
- Nested lambda functions with r.row usage
- Array filtering and counting operations
- Cross-database operations and joins

This test suite proves that the database context propagation fix enables
rethinkdb-mock to be a drop-in replacement for RethinkDB in IsardVDI testing.
"""

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestIsardVDICompatibility(MockTest):
    @staticmethod
    def get_data():
        # Set up data structure similar to IsardVDI
        data = {
            "dbs": {
                "isard": {
                    "tables": {
                        "media": [
                            {
                                "id": "media_ubuntu",
                                "name": "ubuntu-20.04.iso",
                                "status": "Downloaded",
                                "user": "admin",
                                "category": "system",
                                "allowed": {
                                    "roles": ["admin"],
                                    "categories": ["system"],
                                    "groups": [],
                                    "users": [],
                                },
                            },
                            {
                                "id": "media_windows",
                                "name": "windows-10.iso",
                                "status": "Available",
                                "user": "user1",
                                "category": "desktop",
                                "allowed": {
                                    "roles": ["user"],
                                    "categories": ["desktop"],
                                    "groups": ["windows-users"],
                                    "users": ["user1", "user2"],
                                },
                            },
                            {
                                "id": "media_public",
                                "name": "public-tool.iso",
                                "status": "Downloaded",
                                "user": "admin",
                                "category": "tools",
                                "allowed": {
                                    "roles": [],  # Empty roles - should use default
                                    "categories": ["tools"],
                                    "groups": [],
                                    "users": [],
                                },
                            },
                        ],
                        "domains": [
                            {
                                "id": "template_ubuntu",
                                "name": "Ubuntu Base Template",
                                "kind": "template",
                                "enabled": True,
                                "user": "admin",
                                "category": "system",
                                "allowed": {
                                    "roles": ["admin", "user"],
                                    "categories": ["system", "desktop"],
                                    "groups": [],
                                    "users": [],
                                },
                            },
                            {
                                "id": "desktop_user1",
                                "name": "User Desktop",
                                "kind": "desktop",
                                "status": "Started",
                                "user": "user1",
                                "viewers": [
                                    {"id": "viewer1", "type": "spice", "port": 5900},
                                    {"id": "viewer2", "type": "vnc", "port": 5901},
                                ],
                                "hardware": {"vcpus": 2, "memory": 2048},
                                "allowed": {"roles": ["user"], "users": ["user1"]},
                            },
                        ],
                        "categories": [
                            {"id": "system", "name": "System", "enabled": True},
                            {"id": "desktop", "name": "Desktop", "enabled": True},
                            {"id": "tools", "name": "Tools", "enabled": True},
                        ],
                    }
                }
            }
        }
        return data

    def test_media_access_filtering_admin_role(self, conn):
        """Test IsardVDI media access pattern for admin users"""

        # This pattern is core to IsardVDI's media access control
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Downloaded"})
            .filter(
                lambda media: (
                    r.expr(["admin"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        # Should find media_ubuntu (has admin role) and media_public (empty roles -> default)
        assertEqual(len(result), 2)
        media_ids = [m["id"] for m in result]
        assert "media_ubuntu" in media_ids
        assert "media_public" in media_ids

    def test_media_access_filtering_user_role(self, conn):
        """Test IsardVDI media access pattern for regular users"""

        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        # Should find media_windows (has user role) and media_public (empty roles -> default)
        assertEqual(len(result), 2)
        media_ids = [m["id"] for m in result]
        assert "media_windows" in media_ids
        assert "media_public" in media_ids

    def test_media_access_multi_criteria(self, conn):
        """Test IsardVDI's multi-criteria access control (roles, categories, groups, users)"""

        # Simulate a user with specific roles, categories, groups, and ID
        user_roles = ["user"]
        user_categories = ["desktop"]
        user_groups = ["windows-users"]
        user_id = "user1"

        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (
                    # Role check
                    r.expr(user_roles)
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
                | (
                    # Category check
                    r.expr(user_categories)
                    .set_intersection(r.row["allowed"]["categories"].default([]))
                    .count()
                    > 0
                )
                | (
                    # Group check
                    r.expr(user_groups)
                    .set_intersection(r.row["allowed"]["groups"].default([]))
                    .count()
                    > 0
                )
                | (
                    # User check
                    r.expr([user_id])
                    .set_intersection(r.row["allowed"]["users"].default([]))
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        # Should find media_windows and media_public
        assertEqual(len(result), 2)
        media_ids = [m["id"] for m in result]
        assert "media_windows" in media_ids
        assert "media_public" in media_ids

    def test_template_access_filtering(self, conn):
        """Test IsardVDI template access with role and category checks"""

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: (
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
                & (
                    r.expr(["desktop"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["categories"].default([]).is_empty(),
                            ["default"],
                            r.row["allowed"]["categories"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assert result[0]["id"] == "template_ubuntu"

    def test_desktop_viewer_filtering(self, conn):
        """Test IsardVDI desktop viewer array filtering patterns"""

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .filter(
                lambda desktop: r.row["viewers"]
                .filter(lambda viewer: viewer["type"] == "spice")
                .count()
                > 0
            )
            .map(
                lambda desktop: {
                    "id": r.row["id"],
                    "spice_viewers": r.row["viewers"]
                    .filter(lambda viewer: viewer["type"] == "spice")
                    .count(),
                    "total_viewers": r.row["viewers"].count(),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assert result[0]["spice_viewers"] == 1
        assert result[0]["total_viewers"] == 2

    def test_nested_conditional_logic(self, conn):
        """Test IsardVDI's nested conditional branching patterns"""

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .map(
                lambda desktop: {
                    "id": r.row["id"],
                    "status_info": r.branch(
                        r.row["status"] == "Started",
                        r.branch(
                            r.row["viewers"].count() > 0,
                            "running_with_viewers",
                            "running_no_viewers",
                        ),
                        "not_running",
                    ),
                    "resource_tier": r.branch(
                        r.row["hardware"]["memory"] >= 4096,
                        "high",
                        r.branch(
                            r.row["hardware"]["memory"] >= 2048,
                            "medium",
                            "low",
                        ),
                    ),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assert result[0]["status_info"] == "running_with_viewers"
        assert result[0]["resource_tier"] == "medium"

    def test_null_and_missing_field_handling(self, conn):
        """Test IsardVDI's null and missing field handling patterns"""

        # Add test data with null and missing fields
        r.db("isard").table("media").insert(
            {
                "id": "media_null_roles",
                "allowed": {"roles": None},
            }
        ).run(conn)

        r.db("isard").table("media").insert(
            {
                "id": "media_missing_allowed",
                # No allowed field at all
            }
        ).run(conn)

        # Test null role handling
        result = list(
            r.db("isard")
            .table("media")
            .filter({"id": "media_null_roles"})
            .filter(
                lambda media: r.branch(
                    r.row["allowed"]["roles"].default(None) == None,
                    True,  # Allow access if roles is null
                    r.expr(["admin"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0,
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)

        # Test missing field handling with defaults
        result = list(
            r.db("isard")
            .table("media")
            .filter({"id": "media_missing_allowed"})
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "has_allowed": r.row.has_fields("allowed"),
                    "roles": r.row["allowed"]["roles"].default([]),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assert result[0]["has_allowed"] == False
        assert result[0]["roles"] == []

    def test_complex_role_intersection_edge_cases(self, conn):
        """Test edge cases in role intersection logic"""

        # Test with user having multiple roles
        multi_roles = ["user", "advanced"]

        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (
                    r.expr(multi_roles)
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        # Should find all media due to user role in multi_roles and default behavior
        assertEqual(len(result), 3)

    def test_combined_status_and_access_filtering(self, conn):
        """Test combined status and access filtering (common IsardVDI pattern)"""

        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Downloaded"})
            .filter(
                lambda media: (
                    r.expr(["admin"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        # Should find Downloaded media accessible to admin
        assertEqual(len(result), 2)
        media_ids = [m["id"] for m in result]
        assert "media_ubuntu" in media_ids
        assert "media_public" in media_ids

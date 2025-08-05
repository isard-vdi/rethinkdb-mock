#!/usr/bin/env python3
"""
Test the specific patterns that were failing in IsardVDI's test suite.

This test reproduces the exact database context propagation issues that were
causing 'NoneType' object has no attribute 'get_db' errors in the IsardVDI
project tests, particularly in test_media.py and test_templates.py.
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestIsardVDIPatterns(MockTest):
    """Test patterns extracted from IsardVDI's failing tests"""

    def get_data(self):
        # Simulate data similar to IsardVDI's media and templates
        media_data = [
            {
                "id": "media1",
                "name": "test-media.iso",
                "status": "Downloaded",
                "user": "admin",
                "category": "system",
                "kind": "file",
                "url-web": "http://example.com/media1.iso",
                "url-isard": "http://storage/media1.iso",
                "detail": "Test media file",
                "description": "A test ISO file",
                "icon": "fa-file",
                "size": 1024000,
                "progress": {"total": 1024000, "received": 1024000},
                "domains": [],
                "hypervisors_pools": ["default"],
                "allowed": {
                    "roles": ["admin"],
                    "categories": ["default"],
                    "groups": [],
                    "users": [],
                },
            },
            {
                "id": "media2",
                "name": "ubuntu-desktop.iso",
                "status": "Available",
                "user": "user1",
                "category": "desktop",
                "kind": "file",
                "url-web": "http://ubuntu.com/desktop.iso",
                "url-isard": "http://storage/ubuntu.iso",
                "detail": "Ubuntu Desktop ISO",
                "description": "Ubuntu Desktop installation media",
                "icon": "fa-ubuntu",
                "size": 3500000000,
                "progress": {"total": 3500000000, "received": 3500000000},
                "domains": ["domain1", "domain2"],
                "hypervisors_pools": ["default", "pool1"],
                "allowed": {
                    "roles": ["user"],
                    "categories": ["desktop"],
                    "groups": ["users"],
                    "users": ["user1", "user2"],
                },
            },
        ]

        templates_data = [
            {
                "id": "template1",
                "name": "Ubuntu Base Template",
                "status": "Available",
                "user": "admin",
                "category": "system",
                "kind": "template",
                "icon": "fa-ubuntu",
                "description": "Base Ubuntu template",
                "detail": "Ubuntu 20.04 base template",
                "enabled": True,
                "allowed": {
                    "roles": ["admin", "user"],
                    "categories": ["default"],
                    "groups": [],
                    "users": [],
                },
                "create_dict": {
                    "hardware": {"vcpus": 2, "memory": 2048},
                    "origin": "base-image",
                },
            },
            {
                "id": "template2",
                "name": "Windows Template",
                "status": "Available",
                "user": "admin",
                "category": "desktop",
                "kind": "template",
                "icon": "fa-windows",
                "description": "Windows 10 template",
                "detail": "Windows 10 Pro template",
                "enabled": True,
                "allowed": {
                    "roles": ["user"],
                    "categories": ["desktop"],
                    "groups": ["windows-users"],
                    "users": [],
                },
                "create_dict": {
                    "hardware": {"vcpus": 4, "memory": 4096},
                    "origin": "windows-base",
                },
            },
        ]

        return {
            **as_db_and_table("isard", "media", media_data),
            **as_db_and_table("isard", "domains", templates_data),
        }

    def test_media_get_allowed_pattern(self, conn):
        """
        Test the exact pattern from test_media.py::test_get_media_allowed

        This reproduces the r.row usage within lambda functions that was causing
        'NoneType' object has no attribute 'get_db' errors.
        """
        # This is the pattern extracted from IsardVDI's helpers.py
        # get_media_allowed_domain function
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

        # Should find media1 which has status "Downloaded" and roles ["admin"]
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media1")

    def test_media_get_allowed_none_pattern(self, conn):
        """
        Test the pattern from test_media.py::test_get_media_allowed_none

        This tests r.row usage with None checks in lambda functions.
        """
        # Pattern that checks for empty/None allowed roles
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Available"})
            .filter(
                lambda media: r.branch(
                    r.row["allowed"]["roles"].default(None) == None,
                    True,  # If roles is None, allow access
                    r.expr(["user"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0,
                )
            )
            .run(conn)
        )

        # Should find media2 which has status "Available" and roles ["user"]
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media2")

    def test_templates_get_all_pattern(self, conn):
        """
        Test the pattern from test_templates.py::test_get_all_templates

        This reproduces complex r.row usage in nested lambda operations.
        """
        # Pattern for getting allowed templates with complex filtering
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: (
                    # Check if user roles intersect with template allowed roles
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
                    # Check if user categories intersect with template allowed categories
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
            .map(
                lambda template: template.merge(
                    {
                        "category_name": r.db("isard")
                        .table("categories")
                        .get(r.row["category"])
                        .default({"name": "Unknown"})["name"],
                        "user_name": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown"})["name"],
                    }
                )
            )
            .run(conn)
        )

        # Should find template2 which matches the criteria
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "template2")

    def test_nested_database_context_in_lambda(self, conn):
        """
        Test nested database operations within lambda functions.

        This is the core pattern that was failing - r.db() calls within
        lambda functions that are executed in a different context.
        """
        # Create some mock category and user data for the joins
        categories_data = [
            {"id": "system", "name": "System Category"},
            {"id": "desktop", "name": "Desktop Category"},
        ]
        users_data = [
            {"id": "admin", "name": "Administrator"},
            {"id": "user1", "name": "Test User"},
        ]

        # Insert the additional test data
        r.db("isard").table_create("categories").run(conn)
        r.db("isard").table("categories").insert(categories_data).run(conn)
        r.db("isard").table_create("users").run(conn)
        r.db("isard").table("users").insert(users_data).run(conn)

        # This is the exact pattern that was failing:
        # r.db() calls within map() lambda functions
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: media.merge(
                    {
                        "category_info": r.db("isard")
                        .table("categories")
                        .get(r.row["category"])
                        .default({"name": "Unknown"}),
                        "user_info": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown"}),
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 2)
        assertEqual(result[0]["category_info"]["name"], "System Category")
        assertEqual(result[0]["user_info"]["name"], "Administrator")
        assertEqual(result[1]["category_info"]["name"], "Desktop Category")
        assertEqual(result[1]["user_info"]["name"], "Test User")

    def test_complex_filter_with_cross_db_references(self, conn):
        """
        Test complex filtering that involves cross-database references in lambdas.

        This reproduces the most complex case that was failing.
        """
        # This pattern combines filtering with cross-database lookups
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template"})
            .filter(
                lambda template: r.db("isard")
                .table("categories")
                .get(r.row["category"])
                .default({"enabled": False})["enabled"]
                .default(True)  # Default to enabled if field missing
            )
            .map(
                lambda template: {
                    "id": r.row["id"],
                    "name": r.row["name"],
                    "category_enabled": r.db("isard")
                    .table("categories")
                    .get(r.row["category"])
                    .default({"enabled": True})["enabled"],
                }
            )
            .run(conn)
        )

        # Both templates should be returned since categories don't have enabled field
        # and we default to True
        assertEqual(len(result), 2)

    def test_branch_with_row_in_lambda_context(self, conn):
        """
        Test r.branch operations with r.row in lambda contexts.

        This reproduces the specific branch + row pattern that was problematic.
        """
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "access_level": r.branch(
                        r.row["allowed"]["roles"].default([]).contains("admin"),
                        "admin",
                        r.branch(
                            r.row["allowed"]["roles"].default([]).contains("user"),
                            "user",
                            "none",
                        ),
                    ),
                    "size_category": r.branch(
                        r.row["size"] > 1000000000,  # > 1GB
                        "large",
                        r.branch(r.row["size"] > 1000000, "medium", "small"),  # > 1MB
                    ),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)
        assertEqual(result[0]["access_level"], "admin")
        assertEqual(result[0]["size_category"], "medium")  # 1024000 bytes
        assertEqual(result[1]["access_level"], "user")
        assertEqual(result[1]["size_category"], "large")  # 3.5GB

    def test_set_operations_with_row_in_lambdas(self, conn):
        """
        Test set operations (intersections, unions) with r.row in lambda contexts.

        This reproduces the set operation patterns that were failing.
        """
        # Test set intersection with default values - the exact failing pattern
        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: r.expr(["admin", "user"])
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
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "matching_roles": r.expr(["admin", "user"]).set_intersection(
                        r.row["allowed"]["roles"].default([])
                    ),
                    "has_admin": r.row["allowed"]["roles"]
                    .default([])
                    .contains("admin"),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)
        assertEqual(result[0]["matching_roles"], ["admin"])
        assertEqual(result[0]["has_admin"], True)
        assertEqual(result[1]["matching_roles"], ["user"])
        assertEqual(result[1]["has_admin"], False)


if __name__ == "__main__":
    import unittest

    unittest.main()

#!/usr/bin/env python3
"""
Test to validate the database context propagation fix against real-world scenarios
from the IsardVDI project that were failing with the 'NoneType' object has no attribute 'get_db' error.

This recreates the exact patterns that were causing issues in the original test failures:
- api/routes/tests/test_media.py::test_get_media_allowed
- api/routes/tests/test_media.py::test_get_media_allowed_none
- api/routes/tests/test_templates.py::test_get_all_templates
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestIsardVDIPatterns(MockTest):
    """Test patterns from IsardVDI that were causing database context issues"""

    @staticmethod
    def get_data():
        # Recreate the media data structure from the failing tests
        media_data = [
            {
                "id": "media-1",
                "name": "dsl-4.4.10.iso",
                "status": "Downloaded",
                "category": "default",
                "group": "default-default",
                "user": "local-default-admin-admin",
                "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                "kind": "iso",
                "url-isard": False,
                "url-web": "https://example.org/dsl-4.4.10.iso",
                "allowed": {
                    "categories": False,
                    "groups": False,
                    "roles": False,
                    "users": ["another-user"],
                },
            },
            {
                "id": "media-2",
                "name": "ubuntu-20.04.iso",
                "status": "Downloading",
                "category": "default",
                "group": "default-default",
                "user": "local-default-admin-admin",
                "description": "Ubuntu server ISO",
                "kind": "iso",
                "url-isard": False,
                "url-web": "https://example.org/ubuntu-20.04.iso",
                "allowed": {
                    "categories": False,
                    "groups": False,
                    "roles": False,
                    "users": [],
                },
            },
        ]

        domains_data = [
            {
                "id": "template-1",
                "kind": "template",
                "user": "local-default-admin-admin",
                "group": "default-default",
                "category": "default",
                "name": "Template 1",
                "description": "Test template 1",
                "status": "Stopped",
                "create_dict": {"hardware": {"isos": []}},
            },
            {
                "id": "desktop-1",
                "kind": "desktop",
                "user": "local-default-admin-admin",
                "group": "default-default",
                "category": "default",
                "name": "Desktop 1",
                "description": "Test desktop 1",
                "status": "Running",
                "create_dict": {"hardware": {"isos": []}},
            },
        ]

        return as_db_and_table("isard", {"media": media_data, "domains": domains_data})

    def test_isardvdi_index_creation_patterns(self, conn):
        """Test the exact r.row patterns used in IsardVDI index creation that were failing"""

        # This recreates the pattern from helpers.py:create_indexes that was causing issues
        # These are compound indexes using r.row expressions within lambda functions

        # Create indexes that use r.row with database context propagation
        # This pattern was failing with 'NoneType' object has no attribute 'get_db'

        # Test status_category compound index
        r.db("isard").table("media").index_create(
            "status_category", [r.row["status"], r.row["category"]]
        ).run(conn)

        # Test status_group compound index
        r.db("isard").table("media").index_create(
            "status_group", [r.row["status"], r.row["group"]]
        ).run(conn)

        # Test status_user compound index
        r.db("isard").table("media").index_create(
            "status_user", [r.row["status"], r.row["user"]]
        ).run(conn)

        # Wait for indexes to be ready
        r.db("isard").table("media").index_wait().run(conn)

        # Verify the indexes were created successfully
        indexes = r.db("isard").table("media").index_list().run(conn)
        expected_indexes = {"status_category", "status_group", "status_user"}
        actual_indexes = set(indexes)

        # Check that our custom indexes are present
        assert expected_indexes.issubset(
            actual_indexes
        ), f"Missing indexes: {expected_indexes - actual_indexes}"

    def test_isardvdi_query_patterns_with_compound_indexes(self, conn):
        """Test querying with the compound indexes that use r.row patterns"""

        # Create the compound indexes first
        r.db("isard").table("media").index_create(
            "status_category", [r.row["status"], r.row["category"]]
        ).run(conn)
        r.db("isard").table("media").index_wait().run(conn)

        # Query using the compound index - this pattern was causing the database context issues
        result = list(
            r.db("isard")
            .table("media")
            .get_all(["Downloaded", "default"], index="status_category")
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media-1")
        assertEqual(result[0]["status"], "Downloaded")
        assertEqual(result[0]["category"], "default")

    def test_isardvdi_lambda_with_row_references(self, conn):
        """Test lambda functions with r.row references in filter operations"""

        # This pattern mimics the filtering logic that was failing in the original tests
        # Query media items with complex r.row expressions in lambda functions

        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (r.row["status"] == "Downloaded")
                & (r.row["category"] == "default")
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media-1")

    def test_isardvdi_map_with_row_references(self, conn):
        """Test map operations with r.row references"""

        # This tests the pattern where r.row is used in map transformations
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "status_category": r.row["status"] + "_" + r.row["category"],
                    "has_users": r.row["allowed"]["users"].count() > 0,
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)
        assertEqual(result[0]["status_category"], "Downloaded_default")
        assertEqual(result[0]["has_users"], True)
        assertEqual(result[1]["status_category"], "Downloading_default")
        assertEqual(result[1]["has_users"], False)

    def test_isardvdi_nested_row_access(self, conn):
        """Test nested field access with r.row that was causing issues"""

        # Test deep nested access patterns from the failing tests
        result = list(
            r.db("isard")
            .table("media")
            .filter(r.row["allowed"]["users"].contains("another-user"))
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "allowed_users": r.row["allowed"]["users"],
                    "user_count": r.row["allowed"]["users"].count(),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media-1")
        assertEqual(result[0]["allowed_users"], ["another-user"])
        assertEqual(result[0]["user_count"], 1)

    def test_isardvdi_cross_table_queries(self, conn):
        """Test cross-table queries that use database context propagation"""

        # This tests queries that involve multiple tables and database context
        result = list(
            r.db("isard")
            .table("domains")
            .filter(lambda domain: domain["kind"] == "template")
            .map(
                lambda template: {
                    "template_id": r.row["id"],
                    "template_name": r.row["name"],
                    # This would have failed before the database context fix
                    "media_count": r.db("isard")
                    .table("media")
                    .filter(lambda media: media["category"] == template["category"])
                    .count(),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["template_id"], "template-1")
        assertEqual(result[0]["template_name"], "Template 1")
        assertEqual(
            result[0]["media_count"], 2
        )  # Both media items have category "default"

    def test_isardvdi_complex_aggregation(self, conn):
        """Test complex aggregation patterns that use r.row in lambda contexts"""

        # Test aggregation with group_by and r.row references
        result = list(
            r.db("isard")
            .table("media")
            .group(lambda media: [r.row["status"], r.row["category"]])
            .count()
            .ungroup()
            .map(
                lambda group: {
                    "status": group["group"][0],
                    "category": group["group"][1],
                    "count": group["reduction"],
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)

        # Check that we have the expected groups
        groups = {(item["status"], item["category"]): item["count"] for item in result}
        assertEqual(groups[("Downloaded", "default")], 1)
        assertEqual(groups[("Downloading", "default")], 1)

    def test_isardvdi_merge_with_row_references(self, conn):
        """Test merge operations with r.row references that were problematic"""

        # Test merge with r.row expressions in lambda functions
        result = list(
            r.db("isard")
            .table("media")
            .merge(
                lambda media: {
                    "computed_status": r.branch(
                        r.row["status"] == "Downloaded", "ready", "not_ready"
                    ),
                    "full_name": r.row["category"] + "/" + r.row["name"],
                    "metadata": {
                        "has_users": r.row["allowed"]["users"].count() > 0,
                        "is_iso": r.row["kind"] == "iso",
                    },
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)
        assertEqual(result[0]["computed_status"], "ready")
        assertEqual(result[0]["full_name"], "default/dsl-4.4.10.iso")
        assertEqual(result[0]["metadata"]["has_users"], True)
        assertEqual(result[0]["metadata"]["is_iso"], True)

        assertEqual(result[1]["computed_status"], "not_ready")
        assertEqual(result[1]["full_name"], "default/ubuntu-20.04.iso")
        assertEqual(result[1]["metadata"]["has_users"], False)
        assertEqual(result[1]["metadata"]["is_iso"], True)

"""
Test for advanced merge and bracket access functionality.

This module tests specific edge cases and advanced patterns for:
1. Merge operations without lambda functions
2. Direct table bracket access (table["field"])

These tests cover the functionality that was recently fixed for proper table field extraction.
"""

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestAdvancedMergeAndBracket(MockTest):
    @staticmethod
    def get_data():
        data = {
            "dbs": {
                "test_db": {
                    "tables": {
                        "users": [
                            {"id": 1, "name": "Alice", "category": 1},
                            {"id": 2, "name": "Bob", "category": 2},
                            {"id": 3, "name": "Charlie", "category": 1},
                        ],
                        "categories": [
                            {"id": 1, "name": "Admin"},
                            {"id": 2, "name": "User"},
                        ],
                        "domains": [
                            {"id": "domain1", "name": "example.com"},
                            {"id": "domain2", "name": "test.org"},
                            {"id": "domain3", "name": "demo.net"},
                        ],
                    }
                }
            }
        }
        return data

    def test_merge_without_lambda_with_nested_query(self, conn):
        """Test merge without lambda using complex nested queries"""
        result = (
            r.db("test_db")
            .table("users")
            .merge(
                {
                    "category_name": r.db("test_db")
                    .table("categories")
                    .get(r.row["category"])["name"],
                }
            )
            .run(conn)
        )

        result_list = list(result)

        # Verify all users have the category_name field
        assert all("category_name" in doc for doc in result_list)

        # Verify specific mappings
        alice = next(doc for doc in result_list if doc["name"] == "Alice")
        bob = next(doc for doc in result_list if doc["name"] == "Bob")
        charlie = next(doc for doc in result_list if doc["name"] == "Charlie")

        assertEqual(alice["category_name"], "Admin")
        assertEqual(bob["category_name"], "User")
        assertEqual(charlie["category_name"], "Admin")

    def test_direct_table_bracket_access_id(self, conn):
        """Test direct table bracket access for 'id' field"""
        result = r.db("test_db").table("domains")["id"].run(conn)
        result_list = list(result)

        assertEqual(result_list, ["domain1", "domain2", "domain3"])

    def test_direct_table_bracket_access_name(self, conn):
        """Test direct table bracket access for 'name' field"""
        result = r.db("test_db").table("domains")["name"].run(conn)
        result_list = list(result)

        assertEqual(result_list, ["example.com", "test.org", "demo.net"])

    def test_bracket_access_vs_pluck_equivalence(self, conn):
        """Test that bracket access and pluck give equivalent results for single fields"""
        # Get results using bracket access
        bracket_result = list(r.db("test_db").table("domains")["id"].run(conn))

        # Get results using pluck (should return objects with the field)
        pluck_result = list(r.db("test_db").table("domains").pluck("id").run(conn))
        pluck_ids = [doc["id"] for doc in pluck_result]

        assertEqual(bracket_result, pluck_ids)

    def test_bracket_access_vs_map_equivalence(self, conn):
        """Test that bracket access and map give equivalent results"""
        # Get results using bracket access
        bracket_result = list(r.db("test_db").table("domains")["id"].run(conn))

        # Get results using map
        map_result = list(r.db("test_db").table("domains").map(r.row["id"]).run(conn))

        assertEqual(bracket_result, map_result)

    def test_merge_with_static_object(self, conn):
        """Test merge with a completely static object (no queries)"""
        result = r.db("test_db").table("users").merge({"status": "active"}).run(conn)
        result_list = list(result)

        # Verify all users have the status field
        assert all(doc["status"] == "active" for doc in result_list)
        assertEqual(len(result_list), 3)

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestDocumentManipulation(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "user1", "name": "Alice", "age": 25, "email": "alice@example.com"},
            {"id": "user2", "name": "Bob", "age": 30, "email": "bob@example.com"},
            {
                "id": "user3",
                "name": "Charlie",
                "age": 35,
                "email": "charlie@example.com",
            },
        ]
        return as_db_and_table("test_db", "users", data)

    def test_row_basic(self, conn):
        """Test r.row basic functionality"""
        expected = [25, 30, 35]
        result = list(r.db("test_db").table("users").map(r.row["age"]).run(conn))
        assertEqUnordered(expected, result)

    def test_row_in_filter(self, conn):
        """Test r.row in filter context"""
        expected = [
            {"id": "user2", "name": "Bob", "age": 30, "email": "bob@example.com"}
        ]
        result = list(
            r.db("test_db").table("users").filter(r.row["age"] == 30).run(conn)
        )
        assertEqual(expected, result)

    def test_row_complex_expression(self, conn):
        """Test r.row in complex expressions"""
        expected = [
            {
                "id": "user3",
                "name": "Charlie",
                "age": 35,
                "email": "charlie@example.com",
            }
        ]
        result = list(
            r.db("test_db").table("users").filter(r.row["age"] > 30).run(conn)
        )
        assertEqual(expected, result)

    def test_get_field_basic(self, conn):
        """Test get_field basic functionality"""
        expected = ["Alice", "Bob", "Charlie"]
        result = list(r.db("test_db").table("users").get_field("name").run(conn))
        assertEqUnordered(expected, result)

    def test_get_field_on_single_doc(self, conn):
        """Test get_field on a single document"""
        expected = "Alice"
        result = r.db("test_db").table("users").get("user1").get_field("name").run(conn)
        assertEqual(expected, result)

    def test_get_field_nonexistent(self, conn):
        """Test get_field with nonexistent field"""
        from rethinkdb.errors import ReqlNonExistenceError

        try:
            r.db("test_db").table("users").get("user1").get_field("nonexistent").run(
                conn
            )
            assert False, "Should have raised ReqlNonExistenceError"
        except ReqlNonExistenceError:
            pass  # Expected

    def test_values_basic(self, conn):
        """Test values() basic functionality"""
        expected = ["Alice", 25, "alice@example.com"]
        result = (
            r.db("test_db").table("users").get("user1").without("id").values().run(conn)
        )
        assertEqUnordered(expected, result)

    def test_values_multiple_docs(self, conn):
        """Test values() on multiple documents"""
        result = list(
            r.db("test_db")
            .table("users")
            .without("id")
            .map(lambda doc: doc.values())
            .run(conn)
        )
        # Each result should be an array of 3 values (name, age, email)
        assertEqual(3, len(result))
        for values_array in result:
            assertEqual(3, len(values_array))

    def test_object_basic(self, conn):
        """Test r.object basic functionality"""
        expected = {"name": "Test User", "age": 25}
        result = r.object("name", "Test User", "age", 25).run(conn)
        assertEqual(expected, result)

    def test_object_empty(self, conn):
        """Test r.object with no arguments"""
        expected = {}
        result = r.object().run(conn)
        assertEqual(expected, result)

    def test_object_in_query(self, conn):
        """Test r.object used within a query"""
        expected = [
            {"user": {"name": "Alice", "age": 25}},
            {"user": {"name": "Bob", "age": 30}},
            {"user": {"name": "Charlie", "age": 35}},
        ]
        result = list(
            r.db("test_db")
            .table("users")
            .map(
                lambda user: {
                    "user": r.object("name", user["name"], "age", user["age"])
                }
            )
            .run(conn)
        )
        assertEqUnordered(expected, result)

    def test_literal_in_merge(self, conn):
        """Test r.literal in merge operations"""
        # Set up test data with nested object
        user_with_data = {
            "id": "test_user",
            "name": "Test",
            "data": {"old_field": "old_value", "keep_field": "keep_value"},
        }

        # Insert the test user
        r.db("test_db").table("users").insert(user_with_data).run(conn)

        # Update using literal to replace entire data object
        r.db("test_db").table("users").get("test_user").update(
            {"data": r.literal({"new_field": "new_value"})}
        ).run(conn)

        # Verify the data object was completely replaced
        result = r.db("test_db").table("users").get("test_user")["data"].run(conn)
        expected = {"new_field": "new_value"}
        assertEqual(expected, result)

    def test_combined_operations(self, conn):
        """Test combining multiple document manipulation operations"""
        # Create a new object using multiple operations
        result = (
            r.db("test_db")
            .table("users")
            .map(
                lambda user: r.object(
                    "name",
                    user.get_field("name"),
                    "age_in_years",
                    user["age"],
                    "contact",
                    r.object("email", user["email"]),
                )
            )
            .run(conn)
        )

        result_list = list(result)
        assertEqual(3, len(result_list))

        # Verify structure of first result
        first_result = result_list[0]
        assert "name" in first_result
        assert "age_in_years" in first_result
        assert "contact" in first_result
        assert "email" in first_result["contact"]

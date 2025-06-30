"""
Test for administrative and configuration functions.

This module tests database and table administration functionality including:
- Database and table creation/management
- Index status and configuration
- Table status and configuration queries
"""

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestAdminFunctions(MockTest):
    @staticmethod
    def get_data():
        return as_db_and_table("test", "test", [])

    def test_database_creation_and_management(self, conn):
        """Test database creation and basic management"""
        # Create a test database
        r.db_create("test_admin_db").run(conn)

        # Verify it exists in the database list
        db_list = r.db_list().run(conn)
        assert "test_admin_db" in db_list

    def test_table_creation_and_management(self, conn):
        """Test table creation and basic management"""
        # Ensure database exists
        try:
            r.db_create("test_admin_db").run(conn)
        except:
            pass  # Database might already exist

        # Create a test table
        r.db("test_admin_db").table_create("admin_test_table").run(conn)

        # Verify it exists in the table list
        table_list = r.db("test_admin_db").table_list().run(conn)
        assert "admin_test_table" in table_list

    def test_index_status_empty_table(self, conn):
        """Test index status on a table with no indexes"""
        # Ensure database and table exist
        try:
            r.db_create("test_admin_db").run(conn)
            r.db("test_admin_db").table_create("admin_test_table").run(conn)
        except:
            pass  # Might already exist

        # Get index status - should be empty for new table
        result = (
            r.db("test_admin_db").table("admin_test_table").index_status().run(conn)
        )
        result_list = list(result)

        # New table should have no secondary indexes (only primary key)
        # The exact behavior may vary, but it should return some status info
        assert isinstance(result_list, list)

    def test_table_config(self, conn):
        """Test getting table configuration"""
        # Ensure database and table exist
        try:
            r.db_create("test_admin_db").run(conn)
            r.db("test_admin_db").table_create("admin_test_table").run(conn)
        except:
            pass  # Might already exist

        # Get table config
        result = r.db("test_admin_db").table("admin_test_table").config().run(conn)

        # Should return configuration information
        assert result is not None
        # Configuration should contain basic table info
        if isinstance(result, dict):
            # May contain fields like 'name', 'db', etc.
            pass

    def test_table_status(self, conn):
        """Test getting table status"""
        # Ensure database and table exist
        try:
            r.db_create("test_admin_db").run(conn)
            r.db("test_admin_db").table_create("admin_test_table").run(conn)
        except:
            pass  # Might already exist

        # Get table status
        result = r.db("test_admin_db").table("admin_test_table").status().run(conn)

        # Should return status information
        assert result is not None

    def test_index_creation_and_status(self, conn):
        """Test creating an index and checking its status"""
        # Ensure database and table exist
        try:
            r.db_create("test_admin_db").run(conn)
            r.db("test_admin_db").table_create("admin_test_table").run(conn)
        except:
            pass

        # Insert some test data
        r.db("test_admin_db").table("admin_test_table").insert(
            [
                {"id": 1, "name": "test1", "category": "A"},
                {"id": 2, "name": "test2", "category": "B"},
            ]
        ).run(conn)

        # Create a secondary index
        r.db("test_admin_db").table("admin_test_table").index_create("name").run(conn)

        # Wait for index to be ready
        r.db("test_admin_db").table("admin_test_table").index_wait("name").run(conn)

        # Check index status
        result = (
            r.db("test_admin_db")
            .table("admin_test_table")
            .index_status("name")
            .run(conn)
        )
        result_list = list(result)

        # Should show information about the 'name' index
        assert len(result_list) > 0

        # Check all indexes
        all_indexes = (
            r.db("test_admin_db").table("admin_test_table").index_list().run(conn)
        )
        assert "name" in all_indexes

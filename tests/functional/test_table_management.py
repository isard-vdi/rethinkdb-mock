"""
Tests for table management and administrative functions in rethinkdb-mock
"""

import pytest
import rethinkdb as r
from tests.functional.common import MockTest


class TestTableManagement(MockTest):
    @staticmethod
    def get_data():
        return {"dbs": {"test_db": {"tables": {"test_table": []}}}}

    def test_index_status(self, conn):
        """Test index_status() function"""

        # Test index status on table with no indexes
        result = r.db("test_db").table("test_table").index_status().run(conn)
        assert isinstance(result, list)
        assert len(result) == 0  # No indexes initially

        # Create an index
        r.db("test_db").table("test_table").index_create("name").run(conn)

        # Test index status after creating an index
        result = r.db("test_db").table("test_table").index_status().run(conn)
        assert isinstance(result, list)
        assert len(result) == 1

        index_info = result[0]
        assert index_info["index"] == "name"
        assert index_info["ready"] is True
        assert index_info["progress"] == 1.0

        # Test index status for specific index
        result = r.db("test_db").table("test_table").index_status("name").run(conn)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["index"] == "name"

    def test_config(self, conn):
        """Test config() function for tables and databases"""

        # Test table config
        result = r.db("test_db").table("test_table").config().run(conn)
        assert isinstance(result, dict)
        assert "id" in result
        assert result["name"] == "test_table"
        assert result["db"] == "test_db"
        assert result["primary_key"] == "id"
        assert "shards" in result
        assert "write_acks" in result
        assert "durability" in result

        # Test database config
        result = r.db("test_db").config().run(conn)
        assert isinstance(result, dict)
        assert result["name"] == "test_db"
        assert "id" in result

    def test_status(self, conn):
        """Test status() function for tables and databases"""

        # Test table status
        result = r.db("test_db").table("test_table").status().run(conn)
        assert isinstance(result, dict)
        assert result["name"] == "test_table"
        assert result["db"] == "test_db"
        assert "status" in result
        assert result["status"]["ready_for_reads"] is True
        assert result["status"]["ready_for_writes"] is True
        assert result["status"]["all_replicas_ready"] is True
        assert "shards" in result

        # Test database status
        result = r.db("test_db").status().run(conn)
        assert isinstance(result, dict)
        assert result["name"] == "test_db"
        assert "status" in result
        assert result["status"]["ready_for_reads"] is True

    def test_write_hooks(self, conn):
        """Test set_write_hook() and get_write_hook() functions"""

        # Test get_write_hook with no hook set
        result = r.db("test_db").table("test_table").get_write_hook().run(conn)
        assert result is None

        # Test set_write_hook (mock implementation)
        # In reality this would take a function, but for mock we'll use a simple expr
        result = (
            r.db("test_db")
            .table("test_table")
            .set_write_hook(r.expr({"test": "hook"}))
            .run(conn)
        )
        assert isinstance(result, dict)
        assert "created" in result
        assert result["errors"] == 0

    def test_index_status_nonexistent(self, conn):
        """Test index_status() with non-existent index"""

        # Test index status for non-existent index should raise error
        with pytest.raises(Exception):  # Should be ReqlNonExistenceError
            r.db("test_db").table("test_table").index_status("nonexistent").run(conn)

    def test_multiple_indexes_status(self, conn):
        """Test index_status() with multiple indexes"""

        # Create multiple indexes
        r.db("test_db").table("test_table").index_create("name").run(conn)
        r.db("test_db").table("test_table").index_create("email").run(conn)
        r.db("test_db").table("test_table").index_create("age").run(conn)

        # Test index status shows all indexes
        result = r.db("test_db").table("test_table").index_status().run(conn)
        assert isinstance(result, list)
        assert len(result) == 3

        index_names = [idx["index"] for idx in result]
        assert "name" in index_names
        assert "email" in index_names
        assert "age" in index_names

        # All should be ready
        for idx in result:
            assert idx["ready"] is True
            assert idx["progress"] == 1.0

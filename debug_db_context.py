#!/usr/bin/env python3

from rethinkdb import r
from rethinkdb_mock import MockThink

# Initialize the mock
mock = MockThink({
    "dbs": {
        "test_db": {
            "tables": {
                "test": [
                    {"id": 1, "value": 10}
                ]
            }
        }
    }
})
conn = mock.get_conn()

print("=== Testing r.db() access in different contexts ===")

# Test 1: Direct r.db() access (should work)
try:
    result = list(r.db("test_db").table("test").run(conn))
    print(f"Direct access: OK - {len(result)} records")
except Exception as e:
    print(f"Direct access: ERROR - {e}")

# Test 2: r.db() in simple map context (might fail)
try:
    result = list(
        r.db("test_db")
        .table("test")
        .map(lambda doc: doc["value"] * 2)
        .run(conn)
    )
    print(f"Simple map: OK - {result}")
except Exception as e:
    print(f"Simple map: ERROR - {e}")

# Test 3: r.db() inside lambda (likely to fail)
try:
    result = list(
        r.db("test_db")
        .table("test")
        .map(lambda doc: {
            "original": doc["value"],
            "other_table_count": r.db("test_db").table("test").count()
        })
        .run(conn)
    )
    print(f"Nested r.db() in lambda: OK - {result}")
except Exception as e:
    print(f"Nested r.db() in lambda: ERROR - {e}")

# Test 4: Check the mock object structure
print(f"\nMock object type: {type(mock)}")
print(f"Connection type: {type(conn)}")
print(f"Connection has get_db: {hasattr(conn, 'get_db')}")
if hasattr(conn, 'rethinkdb_mock_parent'):
    print(f"Connection parent type: {type(conn.rethinkdb_mock_parent)}")

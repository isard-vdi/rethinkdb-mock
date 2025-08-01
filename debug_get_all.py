#!/usr/bin/env python3

import rethinkdb as r
from rethinkdb_mock import MockThink

# Create a mock connection using the same pattern as tests
mock = MockThink({"dbs": {"test_db": {"tables": {"users": {}}}}})
conn = mock.get_conn()

# Create the test data
users = [
    {"id": "1", "first_name": "John", "last_name": "Smith"},
    {"id": "2", "first_name": "Jane", "last_name": "Smith"},
    {"id": "3", "first_name": "John", "last_name": "Doe"},
]
r.db("test_db").table("users").insert(users).run(conn)

# Test regular get_all with multiple IDs (should work)
print("=== Regular get_all with multiple IDs ===")
try:
    result = list(r.db("test_db").table("users").get_all("1", "3").run(conn))
    print(f"Found {len(result)} users with IDs 1 or 3")
except Exception as e:
    print(f"Error: {e}")

# Create compound index
r.db("test_db").table("users").index_create(
    "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
).run(conn)
r.db("test_db").table("users").index_wait("full_name").run(conn)

print("\n=== Compound index single key ===")
try:
    result1 = list(
        r.db("test_db")
        .table("users")
        .get_all(["Smith", "John"], index="full_name")
        .run(conn)
    )
    print(f"Found {len(result1)} users for ['Smith', 'John']")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Compound index multiple keys ===")
try:
    result2 = list(
        r.db("test_db")
        .table("users")
        .get_all(["Smith", "John"], ["Doe", "John"], index="full_name")
        .run(conn)
    )
    print(f"Found {len(result2)} users for ['Smith', 'John'] or ['Doe', 'John']")
except Exception as e:
    print(f"Error: {e}")

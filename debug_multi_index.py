#!/usr/bin/env python3

import rethinkdb as r
from rethinkdb_mock import MockThink

# Initialize the mock
mock = MockThink({})
conn = mock.connect()

# Use the original r for queries

# Create test data
r.db_create("test_db").run(conn, noreply_wait=True)
r.db("test_db").table_create("people").run(conn, noreply_wait=True)

data = [
    {"id": "1", "name": "Alice", "tags": ["developer", "python", "backend"]},
    {"id": "2", "name": "Bob", "tags": ["designer", "frontend", "react"]},
]

r.db("test_db").table("people").insert(data).run(conn)

print("=== Data inserted ===")
all_people = list(r.db("test_db").table("people").run(conn))
for person in all_people:
    print(f"Person: {person}")

print("\n=== Creating compound multi-index ===")
# Create compound multi index: [user_name, tag] for each tag
r.db("test_db").table("people").index_create(
    "name_tags",
    lambda person: person["tags"].map(lambda tag: [person["name"], tag]),
    multi=True,
).run(conn)
r.db("test_db").table("people").index_wait("name_tags").run(conn)

print("Index created successfully")

print("\n=== Querying compound multi-index ===")
# Query for specific person-tag combination
result = list(
    r.db("test_db")
    .table("people")
    .get_all(["Alice", "python"], index="name_tags")
    .run(conn)
)

print(f"Query result: {result}")
print(f"Result length: {len(result)}")

if len(result) == 0:
    print("\n=== Debugging: Let's see what the index function produces ===")
    # Let's manually check what the index function should generate
    alice = {"id": "1", "name": "Alice", "tags": ["developer", "python", "backend"]}

    # Simulate what the index function should do
    index_values = []
    for tag in alice["tags"]:
        index_values.append([alice["name"], tag])

    print(f"Expected index values for Alice: {index_values}")
    print(f"Looking for: ['Alice', 'python']")
    print(f"Should match: {['Alice', 'python'] in index_values}")

print("\n=== Testing simple multi-index ===")
# Test simple multi-index for comparison
r.db("test_db").table("people").index_create("tags", multi=True).run(conn)
r.db("test_db").table("people").index_wait("tags").run(conn)

simple_result = list(
    r.db("test_db").table("people").get_all("python", index="tags").run(conn)
)
print(f"Simple multi-index result: {len(simple_result)} records")

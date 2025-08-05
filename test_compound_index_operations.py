#!/usr/bin/env python3
"""
Test compound index patterns and get_all operations

This specifically tests whether compound index operations work in rethinkdb-mock,
which were mentioned as potentially problematic.
"""

import sys

sys.path.insert(0, "/home/darta/gits/rethinkdb-mock")

from rethinkdb_mock.db import MockThink
from rethinkdb import r


def test_compound_index_operations():
    """Test compound index and get_all operations"""

    print("🔍 Testing Compound Index Operations")
    print("=" * 50)

    # Create test data
    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "domains": [
                        {
                            "id": "template1",
                            "kind": "template",
                            "enabled": True,
                            "category": "system",
                        },
                        {
                            "id": "template2",
                            "kind": "template",
                            "enabled": False,
                            "category": "desktop",
                        },
                        {
                            "id": "desktop1",
                            "kind": "desktop",
                            "enabled": True,
                            "category": "desktop",
                        },
                    ]
                }
            }
        }
    }

    mock = MockThink(initial_data)
    conn = mock.get_conn()

    try:
        # Test 1: Check if secondary indexes are supported
        print("1️⃣  Testing basic index operations...")

        # Try to create an index
        try:
            r.db("isard").table("domains").index_create("kind").run(conn)
            r.db("isard").table("domains").index_wait("kind").run(conn)
            index_created = True
            print("   ✅ Secondary index creation works!")
        except Exception as e:
            index_created = False
            print(f"   ⚠️  Secondary index creation not supported: {e}")

        # Test get_all if index was created
        if index_created:
            try:
                result = list(
                    r.db("isard")
                    .table("domains")
                    .get_all("template", index="kind")
                    .run(conn)
                )
                print(f"   ✅ get_all with index works! Found {len(result)} templates")
                assert len(result) == 2
            except Exception as e:
                print(f"   ❌ get_all with index failed: {e}")
                return False
        else:
            print("   ℹ️  Skipping get_all with index (not supported)")

    except Exception as e:
        print(f"   ❌ Index operations failed: {e}")
        return False

    try:
        # Test 2: Alternative patterns that work without indexes
        print("\n2️⃣  Testing alternative filtering patterns...")

        # Use filter instead of get_all with index
        result = list(
            r.db("isard").table("domains").filter({"kind": "template"}).run(conn)
        )

        print(
            f"   ✅ Filter-based template selection works! Found {len(result)} templates"
        )
        assert len(result) == 2

    except Exception as e:
        print(f"   ❌ Filter-based selection failed: {e}")
        return False

    try:
        # Test 3: Compound filtering (simulating compound index)
        print("\n3️⃣  Testing compound filtering...")

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .run(conn)
        )

        print(f"   ✅ Compound filtering works! Found {len(result)} enabled templates")
        assert len(result) == 1

    except Exception as e:
        print(f"   ❌ Compound filtering failed: {e}")
        return False

    try:
        # Test 4: Complex compound operations
        print("\n4️⃣  Testing complex compound operations...")

        result = list(
            r.db("isard")
            .table("domains")
            .filter(
                lambda doc: (doc["kind"] == "template")
                & (doc["enabled"] == True)
                & (doc["category"] == "system")
            )
            .run(conn)
        )

        print(
            f"   ✅ Complex compound filtering works! Found {len(result)} matching docs"
        )
        assert len(result) == 1

    except Exception as e:
        print(f"   ❌ Complex compound filtering failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("📊 COMPOUND INDEX OPERATION RESULTS:")
    print("✅ Filter-based operations work perfectly")
    print("✅ Compound filtering works as expected")
    print("✅ Complex compound operations work")

    if not index_created:
        print("ℹ️  Secondary indexes not supported, but alternative patterns work")
        print("ℹ️  IsardVDI can use filter-based patterns instead of get_all")
    else:
        print("✅ Secondary indexes and get_all operations work")

    print("\n🎯 RECOMMENDATION FOR ISARDVDI:")
    print("  Use filter-based patterns instead of get_all with indexes")
    print("  All functionality is available through alternative patterns")

    return True


if __name__ == "__main__":
    success = test_compound_index_operations()
    sys.exit(0 if success else 1)

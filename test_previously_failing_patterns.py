#!/usr/bin/env python3
"""
Test the specific template patterns that were failing before with r.row and map operations

This focuses on the problematic patterns with lambda variable scoping and r.row usage
that were causing issues in IsardVDI template functions.
"""

import sys

sys.path.insert(0, "/home/darta/gits/rethinkdb-mock")

from rethinkdb_mock.db import MockThink
from rethinkdb import r


def test_problematic_template_patterns():
    """Test the specific patterns that were failing before"""

    print("🔍 Testing Previously Problematic Template Patterns")
    print("=" * 70)

    # Create test data
    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "domains": [
                        {
                            "id": "template1",
                            "name": "Ubuntu Template",
                            "kind": "template",
                            "enabled": True,
                            "user": "admin",
                            "category": "system",
                            "allowed": {
                                "roles": ["admin", "user"],
                                "categories": ["system", "desktop"],
                                "groups": [],
                                "users": [],
                            },
                            "hardware": {"vcpus": 2, "memory": 4096},
                        },
                        {
                            "id": "template2",
                            "name": "Windows Template",
                            "kind": "template",
                            "enabled": True,
                            "user": "admin",
                            "category": "desktop",
                            "allowed": {
                                "roles": ["user"],
                                "categories": ["desktop"],
                                "groups": ["users"],
                                "users": [],
                            },
                            "hardware": {"vcpus": 4, "memory": 8192},
                        },
                    ],
                    "categories": [
                        {"id": "system", "name": "System", "enabled": True},
                        {"id": "desktop", "name": "Desktop", "enabled": True},
                    ],
                    "users": [
                        {"id": "admin", "name": "Administrator"},
                    ],
                }
            }
        }
    }

    mock = MockThink(initial_data)
    conn = mock.get_conn()

    try:
        # Test 1: The specific pattern that was failing - map with nested lambda and r.row
        print("1️⃣  Testing map with nested lambda and database lookups...")

        # This pattern was problematic before the fix
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .map(
                lambda template: {
                    "id": template["id"],
                    "name": template["name"],
                    "category_name": r.db("isard")
                    .table("categories")
                    .get(template["category"])
                    .default({"name": "Unknown"})["name"],
                    "user_name": r.db("isard")
                    .table("users")
                    .get(template["user"])
                    .default({"name": "Unknown"})["name"],
                    "memory_gb": template["hardware"]["memory"] / 1024,
                }
            )
            .run(conn)
        )

        print(f"   Processed {len(result)} templates with nested lookups")
        assert len(result) == 2

        for template in result:
            assert "category_name" in template
            assert "user_name" in template
            assert "memory_gb" in template
            assert template["category_name"] in ["System", "Desktop"]
            assert template["user_name"] == "Administrator"

        print("   ✅ Map with nested lookups works!")

    except Exception as e:
        print(f"   ❌ Map with nested lookups failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    try:
        # Test 2: The r.row version that was also problematic
        print("\n2️⃣  Testing r.row in map with database lookups...")

        # This pattern using r.row was also failing
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .map(
                {
                    "id": r.row["id"],
                    "name": r.row["name"],
                    "category_name": r.db("isard")
                    .table("categories")
                    .get(r.row["category"])
                    .default({"name": "Unknown"})["name"],
                    "user_name": r.db("isard")
                    .table("users")
                    .get(r.row["user"])
                    .default({"name": "Unknown"})["name"],
                    "vcpus": r.row["hardware"]["vcpus"],
                }
            )
            .run(conn)
        )

        print(f"   Processed {len(result)} templates with r.row lookups")
        assert len(result) == 2

        for template in result:
            assert "category_name" in template
            assert "user_name" in template
            assert "vcpus" in template
            assert template["category_name"] in ["System", "Desktop"]
            assert template["user_name"] == "Administrator"
            assert template["vcpus"] in [2, 4]

        print("   ✅ r.row in map with lookups works!")

    except Exception as e:
        print(f"   ❌ r.row in map with lookups failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    try:
        # Test 3: Complex nested pattern with conditional logic
        print("\n3️⃣  Testing complex nested pattern with conditionals...")

        # This combines multiple problematic patterns
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .map(
                lambda template: {
                    "id": template["id"],
                    "name": template["name"],
                    "resource_tier": r.branch(
                        template["hardware"]["memory"] >= 8192,
                        "high",
                        r.branch(
                            template["hardware"]["memory"] >= 4096, "medium", "low"
                        ),
                    ),
                    "category_info": r.db("isard")
                    .table("categories")
                    .get(template["category"])
                    .default({"name": "Unknown", "enabled": False}),
                    "has_admin_access": r.expr(["admin"])
                    .set_intersection(
                        r.branch(
                            template["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "user"],
                            template["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0,
                }
            )
            .run(conn)
        )

        print(f"   Processed {len(result)} templates with complex logic")
        assert len(result) == 2

        for template in result:
            assert "resource_tier" in template
            assert "category_info" in template
            assert "has_admin_access" in template
            assert template["resource_tier"] in ["medium", "high"]
            assert isinstance(template["category_info"], dict)
            assert isinstance(template["has_admin_access"], bool)

        print("   ✅ Complex nested patterns work!")

    except Exception as e:
        print(f"   ❌ Complex nested patterns failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    try:
        # Test 4: Pattern with array operations in map
        print("\n4️⃣  Testing array operations within map...")

        # Add array data first
        r.db("isard").table("domains").get("template1").update(
            {
                "tags": ["ubuntu", "server", "base"],
                "features": [
                    {"name": "docker", "enabled": True},
                    {"name": "gui", "enabled": False},
                    {"name": "ssh", "enabled": True},
                ],
            }
        ).run(conn)

        r.db("isard").table("domains").get("template2").update(
            {
                "tags": ["windows", "desktop"],
                "features": [
                    {"name": "office", "enabled": True},
                    {"name": "development", "enabled": False},
                ],
            }
        ).run(conn)

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .map(
                lambda template: {
                    "id": template["id"],
                    "name": template["name"],
                    "tag_count": template["tags"].default([]).count(),
                    "enabled_features": template["features"]
                    .default([])
                    .filter(lambda feature: feature["enabled"])
                    .map(lambda feature: feature["name"]),
                    "has_server_tag": template["tags"].default([]).contains("server"),
                    "category_lookup": r.db("isard")
                    .table("categories")
                    .get(template["category"])
                    .default({"name": "Unknown"})["name"],
                }
            )
            .run(conn)
        )

        print(f"   Processed {len(result)} templates with array operations")
        assert len(result) == 2

        ubuntu_template = next((t for t in result if "Ubuntu" in t["name"]), None)
        windows_template = next((t for t in result if "Windows" in t["name"]), None)

        assert ubuntu_template is not None
        assert ubuntu_template["tag_count"] == 3
        assert ubuntu_template["has_server_tag"] == True
        assert "docker" in ubuntu_template["enabled_features"]
        assert "ssh" in ubuntu_template["enabled_features"]

        assert windows_template is not None
        assert windows_template["tag_count"] == 2
        assert windows_template["has_server_tag"] == False
        assert "office" in windows_template["enabled_features"]

        print("   ✅ Array operations in map work!")

    except Exception as e:
        print(f"   ❌ Array operations in map failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    try:
        # Test 5: Very complex nesting that was breaking before
        print("\n5️⃣  Testing very complex nesting patterns...")

        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: (
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            template["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "user"],
                            template["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .map(
                lambda template: {
                    "template_info": {
                        "id": template["id"],
                        "name": template["name"],
                        "specs": {
                            "memory_mb": template["hardware"]["memory"],
                            "vcpus": template["hardware"]["vcpus"],
                            "tier": r.branch(
                                template["hardware"]["memory"] >= 8192,
                                "premium",
                                "standard",
                            ),
                        },
                    },
                    "access_info": {
                        "category": r.db("isard")
                        .table("categories")
                        .get(template["category"])
                        .default({"name": "Unknown", "enabled": False}),
                        "owner": r.db("isard")
                        .table("users")
                        .get(template["user"])
                        .default({"name": "Unknown"}),
                        "allowed_roles": template["allowed"]["roles"].default([]),
                    },
                    "computed": {
                        "total_features": template["features"].default([]).count(),
                        "enabled_feature_names": template["features"]
                        .default([])
                        .filter(lambda f: f["enabled"])
                        .map(lambda f: f["name"]),
                        "is_high_spec": template["hardware"]["memory"] >= 8192,
                    },
                }
            )
            .run(conn)
        )

        print(f"   Processed {len(result)} templates with very complex nesting")
        assert len(result) == 2

        for template in result:
            assert "template_info" in template
            assert "access_info" in template
            assert "computed" in template

            # Check nested structure
            assert "specs" in template["template_info"]
            assert "tier" in template["template_info"]["specs"]
            assert template["template_info"]["specs"]["tier"] in ["premium", "standard"]

            assert "category" in template["access_info"]
            assert "owner" in template["access_info"]
            assert isinstance(template["access_info"]["category"], dict)
            assert isinstance(template["access_info"]["owner"], dict)

            assert "total_features" in template["computed"]
            assert "enabled_feature_names" in template["computed"]
            assert isinstance(template["computed"]["enabled_feature_names"], list)

        print("   ✅ Very complex nesting works!")

    except Exception as e:
        print(f"   ❌ Very complex nesting failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("🎉 ALL PREVIOUSLY PROBLEMATIC PATTERNS NOW WORK!")
    print("✅ Map with nested lambda and database lookups")
    print("✅ r.row in map with database lookups")
    print("✅ Complex nested patterns with conditionals")
    print("✅ Array operations within map")
    print("✅ Very complex nesting patterns")
    print("\n🔧 These patterns were failing before the database context fix")
    print("🔧 Now they all work correctly with proper variable scoping")

    return True


if __name__ == "__main__":
    success = test_problematic_template_patterns()
    sys.exit(0 if success else 1)

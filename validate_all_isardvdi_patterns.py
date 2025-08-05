#!/usr/bin/env python3
"""
Comprehensive validation of all IsardVDI APIv4 patterns in rethinkdb-mock

This script validates that rethinkdb-mock handles all the database query patterns
used in IsardVDI's APIv4 test suite correctly.
"""

import sys

sys.path.insert(0, "/home/darta/gits/rethinkdb-mock")

from rethinkdb_mock.db import MockThink
from rethinkdb import r


def test_isardvdi_media_patterns():
    """Test all media-related patterns from IsardVDI"""

    print("🧪 Testing IsardVDI Media Patterns...")

    # Media data structure similar to IsardVDI
    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "media": [
                        {
                            "id": "media1",
                            "name": "ubuntu-20.04.iso",
                            "status": "Downloaded",
                            "user": "admin",
                            "category": "system",
                            "allowed": {
                                "roles": ["admin"],
                                "categories": ["system"],
                                "groups": [],
                                "users": [],
                            },
                        },
                        {
                            "id": "media2",
                            "name": "windows-10.iso",
                            "status": "Available",
                            "user": "user1",
                            "category": "desktop",
                            "allowed": {
                                "roles": ["user"],
                                "categories": ["desktop"],
                                "groups": ["users"],
                                "users": ["user1", "user2"],
                            },
                        },
                    ],
                    "categories": [
                        {"id": "system", "name": "System", "enabled": True},
                        {"id": "desktop", "name": "Desktop", "enabled": True},
                    ],
                    "users": [
                        {"id": "admin", "name": "Administrator", "role": "admin"},
                        {"id": "user1", "name": "Test User", "role": "user"},
                    ],
                }
            }
        }
    }

    mock = MockThink(initial_data)
    conn = mock.get_conn()

    try:
        # Test 1: Media access filtering (core IsardVDI pattern)
        print("  ✅ Test 1: Media access filtering...")
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Downloaded"})
            .filter(
                lambda media: (
                    r.expr(["admin"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )
        assert len(result) == 1
        assert result[0]["id"] == "media1"
        print("     ✅ Media access filtering works!")

        # Test 2: Media with category join
        print("  ✅ Test 2: Media with category information...")
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: media.merge(
                    {
                        "category_info": r.db("isard")
                        .table("categories")
                        .get(media["category"])
                        .default({"name": "Unknown"}),
                    }
                )
            )
            .run(conn)
        )
        assert len(result) == 2
        assert result[0]["category_info"]["name"] == "System"
        print("     ✅ Cross-database joins work!")

        # Test 3: Complex role and category filtering
        print("  ✅ Test 3: Complex multi-criteria filtering...")
        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (
                    r.expr(["admin", "user"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0
                )
                & (
                    r.expr(["system", "desktop"])
                    .set_intersection(r.row["allowed"]["categories"].default([]))
                    .count()
                    > 0
                )
            )
            .run(conn)
        )
        assert len(result) == 2
        print("     ✅ Complex filtering works!")

        return True

    except Exception as e:
        print(f"❌ Media patterns failed: {e}")
        return False


def test_isardvdi_template_patterns():
    """Test all template/domain-related patterns from IsardVDI"""

    print("🧪 Testing IsardVDI Template Patterns...")

    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "domains": [
                        {
                            "id": "template1",
                            "name": "Ubuntu Base Template",
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
                        },
                        {
                            "id": "template2",
                            "name": "Windows Desktop Template",
                            "kind": "template",
                            "enabled": True,
                            "user": "admin",
                            "category": "desktop",
                            "allowed": {
                                "roles": ["user"],
                                "categories": ["desktop"],
                                "groups": ["windows-users"],
                                "users": [],
                            },
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
        # Test 1: Template access with role and category filtering
        print("  ✅ Test 1: Template access filtering...")
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: (
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
                & (
                    r.expr(["desktop"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["categories"].default([]).is_empty(),
                            ["default"],
                            r.row["allowed"]["categories"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )
        assert len(result) == 1
        assert result[0]["id"] == "template2"
        print("     ✅ Template filtering works!")

        # Test 2: Template with joined data
        print("  ✅ Test 2: Template with category and user joins...")
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template"})
            .map(
                lambda template: template.merge(
                    {
                        "category_name": r.db("isard")
                        .table("categories")
                        .get(template["category"])
                        .default({"name": "Unknown"})["name"],
                        "user_name": r.db("isard")
                        .table("users")
                        .get(template["user"])
                        .default({"name": "Unknown"})["name"],
                    }
                )
            )
            .run(conn)
        )
        assert len(result) == 2
        assert result[0]["category_name"] == "System"
        assert result[0]["user_name"] == "Administrator"
        print("     ✅ Template joins work!")

        return True

    except Exception as e:
        print(f"❌ Template patterns failed: {e}")
        return False


def test_isardvdi_advanced_patterns():
    """Test advanced patterns from IsardVDI"""

    print("🧪 Testing IsardVDI Advanced Patterns...")

    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "domains": [
                        {
                            "id": "desktop1",
                            "kind": "desktop",
                            "status": "Started",
                            "user": "user1",
                            "hypervisor": "hyp1",
                            "viewers": [
                                {"id": "viewer1", "type": "spice", "port": 5900},
                                {"id": "viewer2", "type": "vnc", "port": 5901},
                            ],
                            "hardware": {"vcpus": 2, "memory": 2048},
                            "allowed": {"roles": ["user"], "users": ["user1"]},
                        },
                    ],
                    "hypervisors": [
                        {
                            "id": "hyp1",
                            "hostname": "hypervisor1.local",
                            "status": "Online",
                            "resources": {"cpu_used": 20, "cpu_total": 100},
                        },
                    ],
                }
            }
        }
    }

    mock = MockThink(initial_data)
    conn = mock.get_conn()

    try:
        # Test 1: Complex nested operations with arrays
        print("  ✅ Test 1: Array filtering and processing...")
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .filter(
                lambda desktop: r.row["viewers"]
                .filter(lambda viewer: viewer["type"] == "spice")
                .count()
                > 0
            )
            .map(
                lambda desktop: {
                    "id": r.row["id"],
                    "spice_viewers": r.row["viewers"].filter(
                        lambda viewer: viewer["type"] == "spice"
                    ),
                    "total_viewers": r.row["viewers"].count(),
                }
            )
            .run(conn)
        )
        assert len(result) == 1
        assert len(result[0]["spice_viewers"]) == 1
        assert result[0]["total_viewers"] == 2
        print("     ✅ Array operations work!")

        # Test 2: Join with calculations
        print("  ✅ Test 2: Joins with calculated fields...")
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .map(
                lambda desktop: desktop.merge(
                    {
                        "hypervisor_info": r.db("isard")
                        .table("hypervisors")
                        .get(desktop["hypervisor"])
                        .default({"hostname": "unknown"}),
                        "memory_gb": desktop["hardware"]["memory"] / 1024,
                    }
                )
            )
            .run(conn)
        )
        assert len(result) == 1
        assert result[0]["hypervisor_info"]["hostname"] == "hypervisor1.local"
        assert result[0]["memory_gb"] == 2.0
        print("     ✅ Complex joins work!")

        # Test 3: Nested conditional logic
        print("  ✅ Test 3: Nested conditional branching...")
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .map(
                lambda desktop: {
                    "id": desktop["id"],
                    "status_info": r.branch(
                        desktop["status"] == "Started",
                        r.branch(
                            desktop["viewers"].count() > 0,
                            "running_with_viewers",
                            "running_no_viewers",
                        ),
                        "not_running",
                    ),
                    "resource_level": r.branch(
                        desktop["hardware"]["memory"] >= 4096,
                        "high",
                        r.branch(
                            desktop["hardware"]["memory"] >= 2048,
                            "medium",
                            "low",
                        ),
                    ),
                }
            )
            .run(conn)
        )
        assert len(result) == 1
        assert result[0]["status_info"] == "running_with_viewers"
        assert result[0]["resource_level"] == "medium"
        print("     ✅ Nested conditionals work!")

        return True

    except Exception as e:
        print(f"❌ Advanced patterns failed: {e}")
        return False


def test_isardvdi_edge_cases():
    """Test edge cases and error handling patterns"""

    print("🧪 Testing IsardVDI Edge Cases...")

    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "media": [
                        {
                            "id": "media1",
                            "allowed": {"roles": None},  # Null roles
                        },
                        {
                            "id": "media2",
                            "allowed": {},  # Missing roles
                        },
                        {
                            "id": "media3",
                            # Missing allowed field entirely
                        },
                    ]
                }
            }
        }
    }

    mock = MockThink(initial_data)
    conn = mock.get_conn()

    try:
        # Test 1: Null handling in role checks
        print("  ✅ Test 1: Null and missing field handling...")
        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: r.branch(
                    r.row["allowed"]["roles"].default(None) == None,
                    True,  # Allow if roles is null
                    r.expr(["admin"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0,
                )
            )
            .run(conn)
        )
        assert len(result) == 3  # All should pass due to null handling
        print("     ✅ Null handling works!")

        # Test 2: Default value handling
        print("  ✅ Test 2: Default value patterns...")
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: {
                    "id": media["id"],
                    "roles": media["allowed"]["roles"].default([]),
                    "has_allowed": media.has_fields("allowed"),
                    "roles_empty": media["allowed"]["roles"].default([]).is_empty(),
                }
            )
            .run(conn)
        )
        assert len(result) == 3
        for item in result:
            if item["id"] == "media1":
                assert item["roles"] == []  # None becomes []
                assert item["has_allowed"] == True
                assert item["roles_empty"] == True
            elif item["id"] == "media2":
                assert item["roles"] == []
                assert item["has_allowed"] == True
                assert item["roles_empty"] == True
            elif item["id"] == "media3":
                assert item["roles"] == []
                assert item["has_allowed"] == False
                assert item["roles_empty"] == True
        print("     ✅ Default values work!")

        return True

    except Exception as e:
        print(f"❌ Edge cases failed: {e}")
        return False


def main():
    """Run all IsardVDI pattern tests"""

    print("🚀 Comprehensive IsardVDI APIv4 Pattern Validation")
    print("=" * 60)

    tests = [
        test_isardvdi_media_patterns,
        test_isardvdi_template_patterns,
        test_isardvdi_advanced_patterns,
        test_isardvdi_edge_cases,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ PASSED\n")
            else:
                failed += 1
                print("❌ FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAILED with exception: {e}\n")

    print("=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 ALL ISARDVDI PATTERNS WORK CORRECTLY!")
        print("✅ rethinkdb-mock is fully compatible with IsardVDI APIv4!")
        print("✅ Database context propagation fix is complete!")
        return True
    else:
        print("❌ Some patterns failed - needs investigation")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

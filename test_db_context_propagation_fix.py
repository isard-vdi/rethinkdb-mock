#!/usr/bin/env python3
"""
Test the exact database context propagation fix for the IsardVDI error.

This reproduces the exact error pattern and validates the fix.
"""

import sys
sys.path.insert(0, "/home/darta/gits/rethinkdb-mock")

from rethinkdb_mock.db import MockThink
from rethinkdb import r


def test_exact_error_pattern():
    """Test the exact pattern that was causing the AttributeError in IsardVDI"""
    
    print("🧪 Testing exact IsardVDI error pattern...")
    
    # Set up mock data similar to IsardVDI templates
    initial_data = {
        "dbs": {
            "isard": {
                "tables": {
                    "media": [
                        {
                            "id": "media1",
                            "allowed": {"roles": ["admin"]},
                            "name": "Test Media"
                        }
                    ],
                    "domains": [
                        {
                            "id": "template1", 
                            "name": "Test Template",
                            "status": "Started"
                        }
                    ]
                }
            }
        }
    }
    
    mock = MockThink(initial_data)
    conn = mock.get_conn()
    
    try:
        # This is the exact pattern that was failing in IsardVDI:
        # A map operation that calls r.db() inside the lambda
        result = list(
            r.db("isard")
            .table("domains")
            .map(lambda template: {
                "id": template["id"],
                "name": template["name"],
                # This r.db() call inside map was causing the error
                "media_count": r.db("isard").table("media").count()
            })
            .run(conn)
        )
        
        print(f"✅ SUCCESS: Result = {result}")
        
        # Verify the result is correct
        expected = [{
            "id": "template1",
            "name": "Test Template", 
            "media_count": 1
        }]
        
        assert result == expected, f"Expected {expected}, got {result}"
        print("✅ Result validation passed!")
        
        return True
        
    except AttributeError as e:
        if "'dict' object has no attribute 'get_db'" in str(e):
            print(f"❌ FAILED: Original error still occurs: {e}")
            return False
        else:
            print(f"❌ FAILED: Different AttributeError: {e}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False


def test_nested_db_calls():
    """Test more complex nested database calls"""
    
    print("\n🧪 Testing nested database calls...")
    
    initial_data = {
        "dbs": {
            "test_db": {
                "tables": {
                    "users": [
                        {"id": 1, "name": "Alice"},
                        {"id": 2, "name": "Bob"}
                    ],
                    "posts": [
                        {"id": 1, "user_id": 1, "title": "Post 1"},
                        {"id": 2, "user_id": 2, "title": "Post 2"}
                    ]
                }
            }
        }
    }
    
    mock = MockThink(initial_data)
    conn = mock.get_conn()
    
    try:
        # Test deeply nested r.db() calls
        result = list(
            r.db("test_db")
            .table("users")
            .map(lambda user: {
                "user_id": user["id"],
                "user_name": user["name"],
                "posts": r.db("test_db").table("posts").filter(
                    lambda post: post["user_id"] == user["id"]
                ).map(lambda post: {
                    "post_id": post["id"],
                    "title": post["title"],
                    "total_users": r.db("test_db").table("users").count()
                })
            })
            .run(conn)
        )
        
        print(f"✅ SUCCESS: Nested result = {result}")
        
        # Verify we got posts for each user
        assert len(result) == 2, f"Expected 2 users, got {len(result)}"
        assert len(result[0]["posts"]) == 1, "Alice should have 1 post"
        assert len(result[1]["posts"]) == 1, "Bob should have 1 post"
        assert result[0]["posts"][0]["total_users"] == 2, "Should count 2 total users"
        
        print("✅ Nested database calls validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Nested database calls failed: {e}")
        return False


if __name__ == "__main__":
    print("=== Testing Database Context Propagation Fix ===\n")
    
    test1_passed = test_exact_error_pattern()
    test2_passed = test_nested_db_calls()
    
    print(f"\n=== Results ===")
    print(f"Exact error pattern: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Nested database calls: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 ALL TESTS PASSED! Database context propagation fix is working!")
        sys.exit(0)
    else:
        print(f"\n💥 SOME TESTS FAILED! Fix needs more work.")
        sys.exit(1)

#!/usr/bin/env python3

from rethinkdb import r
from rethinkdb_mock import MockThink

# Test the issue with r.db() in lambda functions
def test_db_in_lambda():
    # Create mock connection
    mock = MockThink({
        "dbs": {
            "test_db": {
                "tables": {
                    "users": [
                        {"id": "1", "name": "Alice"},
                        {"id": "2", "name": "Bob"}
                    ]
                }
            }
        }
    })
    conn = mock.get_conn()
    
    print("=== Testing r.db() in lambda function ===")
    
    try:
        # This should trigger the error: r.db() inside a lambda
        result = list(
            r.db("test_db")
            .table("users")
            .map(lambda doc: {
                "id": doc["id"],
                "user_count": r.db("test_db").table("users").count()
            })
            .run(conn)
        )
        print(f"Success: {result}")
    except AttributeError as e:
        print(f"Error reproduced: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_db_in_lambda()

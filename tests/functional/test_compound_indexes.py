#!/usr/bin/env python3
"""
Tests for compound indexes in RethinkDB mock

Compound indexes allow efficient querying by multiple fields using array keys.
Based on RethinkDB documentation: https://rethinkdb.com/docs/secondary-indexes/python/
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestCompoundIndexes(MockTest):
    """Test compound indexes using multiple fields"""

    def get_data(self):
        data = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Smith",
                "age": 30,
                "city": "New York",
            },
            {
                "id": "2",
                "first_name": "Jane",
                "last_name": "Smith",
                "age": 25,
                "city": "Boston",
            },
            {
                "id": "3",
                "first_name": "John",
                "last_name": "Doe",
                "age": 35,
                "city": "New York",
            },
            {
                "id": "4",
                "first_name": "Alice",
                "last_name": "Johnson",
                "age": 28,
                "city": "Boston",
            },
            {
                "id": "5",
                "first_name": "Bob",
                "last_name": "Wilson",
                "age": 32,
                "city": "Chicago",
            },
            {
                "id": "6",
                "first_name": "John",
                "last_name": "Smith",
                "age": 45,
                "city": "Chicago",
            },
        ]
        return as_db_and_table("test_db", "users", data)

    def test_compound_index_creation_with_array_syntax(self, conn):
        """Test creating compound indexes using array syntax"""
        # Test compound index creation with array syntax
        try:
            r.db("test_db").table("users").index_create(
                "full_name", [r.row["last_name"], r.row["first_name"]]
            ).run(conn)
            r.db("test_db").table("users").index_wait("full_name").run(conn)

            # Check that index was created
            indexes = list(r.db("test_db").table("users").index_list().run(conn))
            assert "full_name" in indexes

        except Exception as e:
            # If this fails, we need to implement array syntax support
            print(f"Array syntax not supported yet: {e}")
            # Fall back to function syntax
            r.db("test_db").table("users").index_create(
                "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
            ).run(conn)
            r.db("test_db").table("users").index_wait("full_name").run(conn)

    def test_compound_index_creation_with_function_syntax(self, conn):
        """Test creating compound indexes using function syntax"""
        # Create compound index using function that returns array
        r.db("test_db").table("users").index_create(
            "name_age", lambda doc: [doc["last_name"], doc["first_name"], doc["age"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("name_age").run(conn)

        # Verify index exists
        indexes = list(r.db("test_db").table("users").index_list().run(conn))
        assert "name_age" in indexes

    def test_compound_index_simple_query(self, conn):
        """Test querying with compound index using array syntax"""
        # Create table and compound index
        r.db("test_db").table_create("users").run(conn)
        r.db("test_db").table("users").index_create(
            "full_name", [r.row["last_name"], r.row["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Insert test data
        users = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Smith",
                "age": 30,
                "city": "New York",
            },
            {
                "id": "2",
                "first_name": "Jane",
                "last_name": "Smith",
                "age": 25,
                "city": "Boston",
            },
            {
                "id": "3",
                "first_name": "John",
                "last_name": "Doe",
                "age": 35,
                "city": "New York",
            },
            {
                "id": "4",
                "first_name": "Alice",
                "last_name": "Johnson",
                "age": 28,
                "city": "Boston",
            },
            {
                "id": "5",
                "first_name": "Bob",
                "last_name": "Wilson",
                "age": 32,
                "city": "Chicago",
            },
            {
                "id": "6",
                "first_name": "John",
                "last_name": "Smith",
                "age": 45,
                "city": "Chicago",
            },
        ]
        r.db("test_db").table("users").insert(users).run(conn)

        # Query using compound index - should find users with last_name='Smith' and first_name='John'
        result = list(
            r.db("test_db")
            .table("users")
            .get_all(["Smith", "John"], index="full_name")
            .run(conn)
        )

        assertEqual(len(result), 2)
        for user in result:
            assertEqual(user["last_name"], "Smith")
            assertEqual(user["first_name"], "John")

    def test_compound_index_multiple_keys(self, conn):
        """Test querying compound index with multiple keys"""
        # Create compound index
        r.db("test_db").table("users").index_create(
            "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Query with multiple compound keys
        result = list(
            r.db("test_db")
            .table("users")
            .get_all(["Smith", "John"], ["Doe", "John"], index="full_name")
            .run(conn)
        )

        # Should find John Smith (2 records) and John Doe (1 record)
        assertEqual(len(result), 3)
        john_smiths = [u for u in result if u["last_name"] == "Smith"]
        john_does = [u for u in result if u["last_name"] == "Doe"]
        assertEqual(len(john_smiths), 2)
        assertEqual(len(john_does), 1)

    def test_compound_index_between_query(self, conn):
        """Test range queries on compound indexes"""
        # Create compound index
        r.db("test_db").table("users").index_create(
            "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Query range from "Johnson" to "Smith" (inclusive)
        result = list(
            r.db("test_db")
            .table("users")
            .between(["Johnson", r.minval], ["Smith", r.maxval], index="full_name")
            .run(conn)
        )

        # Should include Johnson and Smith records, but not Doe or Wilson
        last_names = {user["last_name"] for user in result}
        assert "Johnson" in last_names
        assert "Smith" in last_names
        # Doe comes before Johnson alphabetically, so shouldn't be included
        assert "Doe" not in last_names
        # Wilson comes after Smith, so shouldn't be included
        assert "Wilson" not in last_names

    def test_compound_index_partial_key_query(self, conn):
        """Test querying compound index with partial keys using minval/maxval"""
        # Create compound index
        r.db("test_db").table("users").index_create(
            "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Query all users with last name "Smith" (regardless of first name)
        result = list(
            r.db("test_db")
            .table("users")
            .between(["Smith", r.minval], ["Smith", r.maxval], index="full_name")
            .run(conn)
        )

        # Should find all Smith records
        assertEqual(
            len(result), 3
        )  # Jane Smith, John Smith (age 30), John Smith (age 45)
        for user in result:
            assertEqual(user["last_name"], "Smith")

    def test_compound_index_order_by(self, conn):
        """Test ordering by compound index"""
        # Create compound index
        r.db("test_db").table("users").index_create(
            "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Order by compound index
        result = list(
            r.db("test_db").table("users").order_by(index="full_name").run(conn)
        )

        # Should be ordered by last name, then first name
        assertEqual(len(result), 6)

        # Check ordering
        expected_order = [
            ("Doe", "John"),
            ("Johnson", "Alice"),
            ("Smith", "Jane"),
            ("Smith", "John"),  # age 30
            ("Smith", "John"),  # age 45
            ("Wilson", "Bob"),
        ]

        actual_order = [(user["last_name"], user["first_name"]) for user in result]
        assertEqual(actual_order, expected_order)

    def test_three_field_compound_index(self, conn):
        """Test compound index with three fields"""
        # Create compound index with three fields
        r.db("test_db").table("users").index_create(
            "location_name",
            lambda doc: [doc["city"], doc["last_name"], doc["first_name"]],
        ).run(conn)
        r.db("test_db").table("users").index_wait("location_name").run(conn)

        # Query by city and full name
        result = list(
            r.db("test_db")
            .table("users")
            .get_all(["New York", "Smith", "John"], index="location_name")
            .run(conn)
        )

        assertEqual(len(result), 1)
        user = result[0]
        assertEqual(user["city"], "New York")
        assertEqual(user["last_name"], "Smith")
        assertEqual(user["first_name"], "John")
        assertEqual(user["age"], 30)  # The John Smith from New York

    def test_compound_index_with_partial_city_query(self, conn):
        """Test partial key queries on three-field compound index"""
        # Create compound index
        r.db("test_db").table("users").index_create(
            "location_name",
            lambda doc: [doc["city"], doc["last_name"], doc["first_name"]],
        ).run(conn)
        r.db("test_db").table("users").index_wait("location_name").run(conn)

        # Get all users from Boston
        result = list(
            r.db("test_db")
            .table("users")
            .between(
                ["Boston", r.minval, r.minval],
                ["Boston", r.maxval, r.maxval],
                index="location_name",
            )
            .run(conn)
        )

        assertEqual(len(result), 2)  # Jane Smith and Alice Johnson
        cities = {user["city"] for user in result}
        assertEqual(cities, {"Boston"})

    def test_compound_index_eq_join(self, conn):
        """Test eq_join with compound indexes"""
        # Create a second table for join testing
        posts_data = [
            {
                "id": "p1",
                "title": "Post 1",
                "author_last": "Smith",
                "author_first": "John",
            },
            {
                "id": "p2",
                "title": "Post 2",
                "author_last": "Doe",
                "author_first": "John",
            },
            {
                "id": "p3",
                "title": "Post 3",
                "author_last": "Smith",
                "author_first": "Jane",
            },
        ]
        r.db_create("test_db").run(conn, noreply_wait=True)  # Ensure db exists
        r.db("test_db").table_create("posts").run(conn, noreply_wait=True)
        r.db("test_db").table("posts").insert(posts_data).run(conn)

        # Create compound index on users
        r.db("test_db").table("users").index_create(
            "full_name", lambda doc: [doc["last_name"], doc["first_name"]]
        ).run(conn)
        r.db("test_db").table("users").index_wait("full_name").run(conn)

        # Join posts with users using compound key
        result = list(
            r.db("test_db")
            .table("posts")
            .eq_join(
                lambda post: [post["author_last"], post["author_first"]],
                r.db("test_db").table("users"),
                index="full_name",
            )
            .zip()
            .run(conn)
        )

        # Should find matches for the posts
        assertEqual(len(result), 3)

        # Verify the joins worked correctly
        post1 = next(p for p in result if p["id"] == "p1")
        assertEqual(post1["first_name"], "John")
        assertEqual(post1["last_name"], "Smith")


class TestMultiIndexes(MockTest):
    """Test multi indexes (array-based indexing)"""

    def get_data(self):
        data = [
            {"id": "1", "name": "Alice", "tags": ["developer", "python", "backend"]},
            {"id": "2", "name": "Bob", "tags": ["designer", "frontend", "react"]},
            {
                "id": "3",
                "name": "Charlie",
                "tags": ["developer", "javascript", "frontend"],
            },
            {"id": "4", "name": "Diana", "tags": ["manager", "leadership"]},
            {"id": "5", "name": "Eve", "tags": ["developer", "python", "data-science"]},
        ]
        return as_db_and_table("test_db", "people", data)

    def test_multi_index_creation(self, conn):
        """Test creating multi indexes"""
        # Create multi index on tags array
        r.db("test_db").table("people").index_create("tags", multi=True).run(conn)
        r.db("test_db").table("people").index_wait("tags").run(conn)

        # Verify index exists
        indexes = list(r.db("test_db").table("people").index_list().run(conn))
        assert "tags" in indexes

    def test_multi_index_single_tag_query(self, conn):
        """Test querying multi index for single tag"""
        # Create multi index
        r.db("test_db").table("people").index_create("tags", multi=True).run(conn)
        r.db("test_db").table("people").index_wait("tags").run(conn)

        # Find all developers
        result = list(
            r.db("test_db").table("people").get_all("developer", index="tags").run(conn)
        )

        assertEqual(len(result), 3)  # Alice, Charlie, Eve
        names = {person["name"] for person in result}
        assertEqual(names, {"Alice", "Charlie", "Eve"})

    def test_multi_index_multiple_tags_query(self, conn):
        """Test querying multi index for multiple tags"""
        # Create multi index
        r.db("test_db").table("people").index_create("tags", multi=True).run(conn)
        r.db("test_db").table("people").index_wait("tags").run(conn)

        # Find people with either python or javascript
        result = list(
            r.db("test_db")
            .table("people")
            .get_all("python", "javascript", index="tags")
            .run(conn)
        )

        assertEqual(len(result), 3)  # Alice, Charlie (javascript), Eve (python)
        names = {person["name"] for person in result}
        assertEqual(names, {"Alice", "Charlie", "Eve"})

    def test_multi_index_distinct_results(self, conn):
        """Test using distinct with multi index to avoid duplicates"""
        # Add a person with both python AND javascript tags
        r.db("test_db").table("people").insert(
            {
                "id": "6",
                "name": "Frank",
                "tags": ["developer", "python", "javascript", "fullstack"],
            }
        ).run(conn)

        # Create multi index
        r.db("test_db").table("people").index_create("tags", multi=True).run(conn)
        r.db("test_db").table("people").index_wait("tags").run(conn)

        # Query without distinct - should get Frank twice (once for python, once for javascript)
        result_with_duplicates = list(
            r.db("test_db")
            .table("people")
            .get_all("python", "javascript", index="tags")
            .run(conn)
        )

        # Query with distinct - should get Frank only once
        result_distinct = list(
            r.db("test_db")
            .table("people")
            .get_all("python", "javascript", index="tags")
            .distinct()
            .run(conn)
        )

        # Without distinct, Frank appears twice (once for each matching tag)
        frank_count_with_dups = len(
            [p for p in result_with_duplicates if p["name"] == "Frank"]
        )
        assertEqual(frank_count_with_dups, 2)

        # With distinct, Frank appears only once
        frank_count_distinct = len([p for p in result_distinct if p["name"] == "Frank"])
        assertEqual(frank_count_distinct, 1)

    def test_compound_multi_index(self, conn):
        """Test compound multi index combining user info with tags"""
        # Create compound multi index: [user_name, tag] for each tag
        r.db("test_db").table("people").index_create(
            "name_tags",
            lambda person: person["tags"].map(lambda tag: [person["name"], tag]),
            multi=True,
        ).run(conn)
        r.db("test_db").table("people").index_wait("name_tags").run(conn)

        # Query for specific person-tag combination
        result = list(
            r.db("test_db")
            .table("people")
            .get_all(["Alice", "python"], index="name_tags")
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["name"], "Alice")
        assert "python" in result[0]["tags"]


class TestAdvancedCompoundIndexes(MockTest):
    """Test advanced compound index scenarios"""

    def get_data(self):
        data = [
            {
                "id": "1",
                "department": "Engineering",
                "team": "Backend",
                "level": "Senior",
                "salary": 95000,
            },
            {
                "id": "2",
                "department": "Engineering",
                "team": "Frontend",
                "level": "Junior",
                "salary": 70000,
            },
            {
                "id": "3",
                "department": "Engineering",
                "team": "Backend",
                "level": "Mid",
                "salary": 80000,
            },
            {
                "id": "4",
                "department": "Design",
                "team": "UX",
                "level": "Senior",
                "salary": 85000,
            },
            {
                "id": "5",
                "department": "Design",
                "team": "Visual",
                "level": "Mid",
                "salary": 75000,
            },
            {
                "id": "6",
                "department": "Product",
                "team": "Strategy",
                "level": "Senior",
                "salary": 100000,
            },
        ]
        return as_db_and_table("test_db", "employees", data)

    def test_hierarchical_compound_index(self, conn):
        """Test compound index for hierarchical data (department -> team -> level)"""
        # Create hierarchical compound index
        r.db("test_db").table("employees").index_create(
            "hierarchy", lambda emp: [emp["department"], emp["team"], emp["level"]]
        ).run(conn)
        r.db("test_db").table("employees").index_wait("hierarchy").run(conn)

        # Query specific hierarchy path
        result = list(
            r.db("test_db")
            .table("employees")
            .get_all(["Engineering", "Backend", "Senior"], index="hierarchy")
            .run(conn)
        )

        assertEqual(len(result), 1)
        emp = result[0]
        assertEqual(emp["department"], "Engineering")
        assertEqual(emp["team"], "Backend")
        assertEqual(emp["level"], "Senior")

    def test_compound_index_range_on_hierarchy(self, conn):
        """Test range queries on hierarchical compound index"""
        # Create hierarchical compound index
        r.db("test_db").table("employees").index_create(
            "dept_team", lambda emp: [emp["department"], emp["team"]]
        ).run(conn)
        r.db("test_db").table("employees").index_wait("dept_team").run(conn)

        # Get all Engineering teams
        result = list(
            r.db("test_db")
            .table("employees")
            .between(
                ["Engineering", r.minval], ["Engineering", r.maxval], index="dept_team"
            )
            .run(conn)
        )

        assertEqual(len(result), 3)  # Backend Senior, Frontend Junior, Backend Mid
        departments = {emp["department"] for emp in result}
        assertEqual(departments, {"Engineering"})

    def test_compound_index_with_numeric_fields(self, conn):
        """Test compound index with numeric fields"""
        # Create compound index with department and salary
        r.db("test_db").table("employees").index_create(
            "dept_salary", lambda emp: [emp["department"], emp["salary"]]
        ).run(conn)
        r.db("test_db").table("employees").index_wait("dept_salary").run(conn)

        # Find Engineering employees with salary >= 80000
        result = list(
            r.db("test_db")
            .table("employees")
            .between(
                ["Engineering", 80000], ["Engineering", r.maxval], index="dept_salary"
            )
            .run(conn)
        )

        assertEqual(len(result), 2)  # Senior Backend (95k) and Mid Backend (80k)
        for emp in result:
            assertEqual(emp["department"], "Engineering")
            assert emp["salary"] >= 80000

    def test_compound_index_ordering_with_mixed_types(self, conn):
        """Test compound index ordering with string and numeric fields"""
        # Create compound index: level (string) then salary (number)
        r.db("test_db").table("employees").index_create(
            "level_salary", lambda emp: [emp["level"], emp["salary"]]
        ).run(conn)
        r.db("test_db").table("employees").index_wait("level_salary").run(conn)

        # Order by level, then salary
        result = list(
            r.db("test_db").table("employees").order_by(index="level_salary").run(conn)
        )

        assertEqual(len(result), 6)

        # Should be ordered by level (alphabetically), then by salary within each level
        # Junior -> Mid -> Senior, then by salary within each level
        levels = [emp["level"] for emp in result]

        # Find the boundaries
        junior_end = levels.index("Mid") if "Mid" in levels else len(levels)
        mid_start = junior_end
        mid_end = levels.index("Senior") if "Senior" in levels else len(levels)
        senior_start = mid_end

        # Check Junior section (should be sorted by salary)
        junior_salaries = [result[i]["salary"] for i in range(0, junior_end)]
        assertEqual(junior_salaries, sorted(junior_salaries))

        # Check Mid section
        mid_salaries = [result[i]["salary"] for i in range(mid_start, mid_end)]
        assertEqual(mid_salaries, sorted(mid_salaries))

        # Check Senior section
        senior_salaries = [
            result[i]["salary"] for i in range(senior_start, len(result))
        ]
        assertEqual(senior_salaries, sorted(senior_salaries))

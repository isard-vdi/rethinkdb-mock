from rethinkdb import r
from tests.common import assertEqUnordered
from tests.common import assertEqual
from tests.functional.common import MockTest


def common_join_data():
    people_data = [
        {"id": "joe-id", "name": "Joe"},
        {"id": "tom-id", "name": "Tom"},
        {"id": "arnold-id", "name": "Arnold"},
    ]
    job_data = [
        {"id": "lawyer-id", "name": "Lawyer"},
        {"id": "nurse-id", "name": "Nurse"},
        {"id": "semipro-wombat-id", "name": "Semi-Professional Wombat"},
    ]
    employee_data = [
        {"id": "joe-emp-id", "person": "joe-id", "job": "lawyer-id"},
        {"id": "arnold-emp-id", "person": "arnold-id", "job": "nurse-id"},
    ]
    data = {
        "dbs": {
            "jezebel": {
                "tables": {
                    "people": people_data,
                    "jobs": job_data,
                    "employees": employee_data,
                }
            }
        }
    }
    return data


class TestEqJoin(MockTest):
    @staticmethod
    def get_data():
        return common_join_data()

    def test_eq_join_1(self, conn):
        expected = [
            {
                "left": {"id": "joe-emp-id", "person": "joe-id", "job": "lawyer-id"},
                "right": {"id": "joe-id", "name": "Joe"},
            },
            {
                "left": {
                    "id": "arnold-emp-id",
                    "person": "arnold-id",
                    "job": "nurse-id",
                },
                "right": {"id": "arnold-id", "name": "Arnold"},
            },
        ]
        result = (
            r.db("jezebel")
            .table("employees")
            .eq_join("person", r.db("jezebel").table("people"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestInnerJoin(MockTest):
    @staticmethod
    def get_data():
        return common_join_data()

    def test_inner_join_1(self, conn):
        expected = [
            {
                "left": {"id": "joe-emp-id", "person": "joe-id", "job": "lawyer-id"},
                "right": {"id": "joe-id", "name": "Joe"},
            },
            {
                "left": {
                    "id": "arnold-emp-id",
                    "person": "arnold-id",
                    "job": "nurse-id",
                },
                "right": {"id": "arnold-id", "name": "Arnold"},
            },
        ]
        result = (
            r.db("jezebel")
            .table("employees")
            .inner_join(
                r.db("jezebel").table("people"),
                lambda employee, person: employee["person"] == person["id"],
            )
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestOuterJoin(MockTest):
    @staticmethod
    def get_data():
        people = [
            {"id": "sam-id", "name": "Sam"},
            {"id": "miguel-id", "name": "Miguel"},
            {"id": "mark-id", "name": "Mark"},
        ]
        pets = [
            {"id": "pet1-id", "name": "Pet1", "owner": "miguel-id"},
            {"id": "pet2-id", "name": "Pet2", "owner": "mark-id"},
            {"id": "pet3-id", "name": "Pet3", "owner": "miguel-id"},
        ]
        return {"dbs": {"awesomesauce": {"tables": {"pets": pets, "people": people}}}}

    def test_outer_join_1(self, conn):
        expected = [
            {
                "left": {"id": "miguel-id", "name": "Miguel"},
                "right": {"id": "pet1-id", "name": "Pet1", "owner": "miguel-id"},
            },
            {
                "left": {"id": "miguel-id", "name": "Miguel"},
                "right": {"id": "pet3-id", "name": "Pet3", "owner": "miguel-id"},
            },
            {
                "left": {"id": "mark-id", "name": "Mark"},
                "right": {"id": "pet2-id", "name": "Pet2", "owner": "mark-id"},
            },
            {"left": {"id": "sam-id", "name": "Sam"}},
        ]
        result = (
            r.db("awesomesauce")
            .table("people")
            .outer_join(
                r.db("awesomesauce").table("pets"),
                lambda person, pet: pet["owner"] == person["id"],
            )
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestZip(MockTest):
    @staticmethod
    def get_data():
        left = [
            {"id": "one", "lname": "One", "rval": "r-one"},
            {"id": "two", "lname": "Two", "rval": "r-two"},
        ]
        right = [
            {"id": "r-one", "rname": "RightOne"},
            {"id": "r-two", "rname": "RightTwo"},
        ]
        return {"dbs": {"x": {"tables": {"ltab": left, "rtab": right}}}}

    def test_zip_1(self, conn):
        expected = [
            {"id": "r-one", "lname": "One", "rname": "RightOne", "rval": "r-one"},
            {"id": "r-two", "lname": "Two", "rname": "RightTwo", "rval": "r-two"},
        ]
        result = (
            r.db("x")
            .table("ltab")
            .eq_join("rval", r.db("x").table("rtab"))
            .zip()
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestJoinEdgeCases(MockTest):
    """Test edge cases for join operations"""

    @staticmethod
    def get_data():
        # Extended data with edge cases
        people_data = [
            {"id": "person-1", "name": "Alice", "dept_id": "dept-1"},
            {"id": "person-2", "name": "Bob", "dept_id": "dept-2"},
            {"id": "person-3", "name": "Charlie", "dept_id": "dept-3"},
            {
                "id": "person-4",
                "name": "David",
                "dept_id": "nonexistent",
            },  # No matching dept
            {"id": "person-5", "name": "Eve", "dept_id": None},  # Null dept_id
        ]

        dept_data = [
            {"id": "dept-1", "name": "Engineering", "manager_id": "person-1"},
            {"id": "dept-2", "name": "Marketing", "manager_id": "person-2"},
            {"id": "dept-3", "name": "Sales", "manager_id": None},  # No manager
            {
                "id": "dept-orphan",
                "name": "Orphaned",
                "manager_id": "person-999",
            },  # No matching person
        ]

        # Empty table for testing
        empty_data = []

        return {
            "dbs": {
                "test_db": {
                    "tables": {
                        "people": people_data,
                        "departments": dept_data,
                        "empty_table": empty_data,
                    }
                }
            }
        }

    def test_eq_join_no_matches(self, conn):
        """Test eq_join when left side has no matches in right side"""
        # Person with nonexistent dept_id
        result = list(
            r.db("test_db")
            .table("people")
            .filter({"id": "person-4"})
            .eq_join("dept_id", r.db("test_db").table("departments"))
            .run(conn)
        )
        # Should return empty result
        assertEqual(len(result), 0)

    def test_eq_join_with_nulls(self, conn):
        """Test eq_join with null values"""
        # Person with null dept_id should not match anything
        result = list(
            r.db("test_db")
            .table("people")
            .filter({"id": "person-5"})
            .eq_join("dept_id", r.db("test_db").table("departments"))
            .run(conn)
        )
        assertEqual(len(result), 0)

    def test_eq_join_empty_tables(self, conn):
        """Test eq_join with empty tables"""
        result = list(
            r.db("test_db")
            .table("empty_table")
            .eq_join("id", r.db("test_db").table("departments"))
            .run(conn)
        )
        assertEqual(len(result), 0)

    def test_inner_join_edge_cases(self, conn):
        """Test inner_join with edge cases"""
        # Inner join with always false predicate
        result = list(
            r.db("test_db")
            .table("people")
            .inner_join(
                r.db("test_db").table("departments"), lambda person, dept: False
            )
            .run(conn)
        )
        assertEqual(len(result), 0)

    def test_outer_join_edge_cases(self, conn):
        """Test outer_join with edge cases"""
        # Outer join where some left items have no matches
        result = list(
            r.db("test_db")
            .table("people")
            .outer_join(
                r.db("test_db").table("departments"),
                lambda person, dept: person["dept_id"] == dept["id"],
            )
            .run(conn)
        )
        # Should include all people, even those without matching departments
        assertEqual(len(result), 5)  # All 5 people should be included

        # Check that we got a reasonable number of results (simplified assertion)
        assert len(result) >= 3  # Should have at least inner join results

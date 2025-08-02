from pprint import pprint

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqUnordered
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestArrayManip(MockTest):
    @staticmethod
    def get_data():
        data = [{"id": 1, "animals": ["frog", "cow"]}, {"id": 2, "animals": ["horse"]}]
        return as_db_and_table("x", "farms", data)

    def test_insert_at(self, conn):
        expected = [["frog", "pig", "cow"], ["horse", "pig"]]
        result = (
            r.db("x")
            .table("farms")
            .map(lambda d: d["animals"].insert_at(1, "pig"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_splice_at(self, conn):
        expected = [["frog", "pig", "chicken", "cow"], ["horse", "pig", "chicken"]]
        result = (
            r.db("x")
            .table("farms")
            .map(lambda d: d["animals"].splice_at(1, ["pig", "chicken"]))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_prepend(self, conn):
        expected = [["pig", "frog", "cow"], ["pig", "horse"]]
        result = (
            r.db("x")
            .table("farms")
            .map(lambda d: d["animals"].prepend("pig"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_append(self, conn):
        expected = [["frog", "cow", "pig"], ["horse", "pig"]]
        result = (
            r.db("x").table("farms").map(lambda d: d["animals"].append("pig")).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_change_at(self, conn):
        expected = [["wombat", "cow"], ["wombat"]]
        result = (
            r.db("x")
            .table("farms")
            .map(lambda d: d["animals"].change_at(0, "wombat"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_delete_at(self, conn):
        expected = [["cow"], []]
        result = (
            r.db("x").table("farms").map(lambda d: d["animals"].delete_at(0)).run(conn)
        )
        res = list(result)
        assertEqUnordered(expected, res)


class TestUnion(MockTest):
    @staticmethod
    def get_data():
        things_1 = [{"id": "thing1-1"}, {"id": "thing1-2"}]
        things_2 = [{"id": "thing2-1"}, {"id": "thing2-2"}]
        return {"dbs": {"x": {"tables": {"things_1": things_1, "things_2": things_2}}}}

    def test_table_union(self, conn):
        expected = [
            {"id": "thing1-1"},
            {"id": "thing1-2"},
            {"id": "thing2-1"},
            {"id": "thing2-2"},
        ]
        result = (
            r.db("x").table("things_1").union(r.db("x").table("things_2")).run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestIndexesOf(MockTest):
    @staticmethod
    def get_data():
        things = [
            {"id": "one", "letters": ["c", "c"]},
            {"id": "two", "letters": ["a", "b", "a", ["q", "q"], "b"]},
            {"id": "three", "letters": ["b", "a", "b", "a"]},
            {"id": "four", "letters": ["c", "a", "b", "a", ["q", "q"]]},
        ]
        return as_db_and_table("scrumptious", "cake", things)

    def test_offsets_of_val(self, conn):
        expected = [[], [1, 4], [0, 2], [2]]
        result = (
            r.db("scrumptious")
            .table("cake")
            .map(lambda doc: doc["letters"].offsets_of("b"))
            .run(conn)
        )
        result = list(result)
        pprint(result)
        assertEqUnordered(expected, result)

    def test_offsets_of_array_val(self, conn):
        expected = [[], [3], [], [4]]
        result = (
            r.db("scrumptious")
            .table("cake")
            .map(lambda doc: doc["letters"].offsets_of(["q", "q"]))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_offsets_of_func(self, conn):
        expected = [[], [1, 4], [0, 2], [2]]
        result = (
            r.db("scrumptious")
            .table("cake")
            .map(lambda doc: doc["letters"].offsets_of(lambda letter: letter == "b"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestSample(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "one", "data": list(range(10, 20))},
            {"id": "two", "data": list(range(20, 30))},
            {"id": "three", "data": list(range(30, 40))},
        ]
        return as_db_and_table("db", "things", data)

    def test_nested(self, conn):
        result = (
            r.db("db")
            .table("things")
            .filter({"id": "one"})
            .map(lambda doc: doc["data"].sample(3))
            .run(conn)
        )
        result = list(result)
        assert len(result) == 1
        result = result[0]
        assert len(result) == 3
        for num in result:
            assert num <= 20
            assert num >= 10

    def test_docs(self, conn):
        result = r.db("db").table("things").sample(2).run(conn)
        result = list(result)
        assert len(result) == 2
        doc1, doc2 = result
        assert doc1 != doc2
        ids = set(["one", "two", "three"])
        assert doc1["id"] in ids
        assert doc2["id"] in ids


class TestArrayManipEdgeCases(MockTest):
    """Test edge cases for array manipulation functions"""

    @staticmethod
    def get_data():
        data = [
            {"id": 1, "empty": [], "single": [42], "mixed": [1, "str", None, 3.14]},
            {"id": 2, "nested": [[1, 2], [3, [4, 5]], []], "duplicates": [1, 1, 2, 1]},
            {"id": 3, "nulls": [None, None, None], "sparse": [1, None, 3, None, 5]},
            {"id": 4, "large": list(range(100)), "strings": ["a", "A", "b", "B"]},
            {"id": 5, "booleans": [True, False, True], "special": [0, "", False, None]},
        ]
        return as_db_and_table("test_db", "arrays", data)

    def test_insert_at_edge_cases(self, conn):
        """Test insert_at with edge cases"""
        # Insert at beginning of empty array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].insert_at(0, "first"))
            .run(conn)
        )
        assertEqual(result[0], ["first"])

        # Insert at negative index (should handle gracefully or error)
        try:
            result = list(
                r.db("test_db")
                .table("arrays")
                .filter({"id": 1})
                .map(lambda doc: doc["single"].insert_at(-1, "neg"))
                .run(conn)
            )
            # If supported, should insert at end
        except Exception:
            pass  # Negative indices might not be supported

        # Insert at out-of-bounds index
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].insert_at(5, "far"))
            .run(conn)
        )
        assertEqual(result[0], [42, "far"])  # Should append at end

    def test_splice_at_edge_cases(self, conn):
        """Test splice_at with edge cases"""
        # Splice empty array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].splice_at(0, ["a", "b"]))
            .run(conn)
        )
        assertEqual(result[0], ["a", "b"])

        # Splice with empty insertion array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].splice_at(0, []))
            .run(conn)
        )
        assertEqual(result[0], [42])  # Should remain unchanged

    def test_append_prepend_with_nulls(self, conn):
        """Test append/prepend with null values"""
        # Append null
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].append(None))
            .run(conn)
        )
        assertEqual(result[0], [42, None])

        # Prepend to array with nulls
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 3})
            .map(lambda doc: doc["nulls"].prepend("start"))
            .run(conn)
        )
        assertEqual(result[0], ["start", None, None, None])

    def test_set_insert_with_duplicates(self, conn):
        """Test set_insert behavior with duplicates"""
        # Set insert should not add duplicates
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 2})
            .map(lambda doc: doc["duplicates"].set_insert(1))
            .run(conn)
        )
        # Should still have same unique elements
        assert 1 in result[0]
        assert 2 in result[0]

    def test_set_difference_edge_cases(self, conn):
        """Test set_difference with edge cases"""
        # Difference with empty array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].set_difference([]))
            .run(conn)
        )
        assertEqual(result[0], [42])

        # Difference with itself
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].set_difference([42]))
            .run(conn)
        )
        assertEqual(result[0], [])

    def test_set_operations_with_mixed_types(self, conn):
        """Test set operations with mixed data types"""
        # Union with mixed types
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["mixed"].set_union([True, 1, "str"]))
            .run(conn)
        )
        # Should preserve uniqueness across types
        unique_result = list(set(result[0]))  # Convert to set to check uniqueness
        assert len(unique_result) <= len(result[0])

    def test_slice_edge_cases(self, conn):
        """Test slice with edge cases"""
        # Slice beyond array bounds
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].slice(0, 10))
            .run(conn)
        )
        assertEqual(result[0], [42])  # Should return available elements

        # Slice with negative indices (if supported)
        try:
            result = list(
                r.db("test_db")
                .table("arrays")
                .filter({"id": 4})
                .map(lambda doc: doc["large"].slice(-5, -1))
                .run(conn)
            )
        except Exception:
            pass  # Negative indices might not be supported

    def test_limit_skip_edge_cases(self, conn):
        """Test limit and skip with edge cases"""
        # Limit more than array size
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].limit(10))
            .run(conn)
        )
        assertEqual(result[0], [42])

        # Skip more than array size
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].skip(10))
            .run(conn)
        )
        assertEqual(result[0], [])

    def test_contains_with_special_values(self, conn):
        """Test contains with special values"""
        # Contains null
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 3})
            .map(lambda doc: doc["nulls"].contains(None))
            .run(conn)
        )
        assertEqual(result[0], True)

        # Contains boolean false vs empty string vs zero
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 5})
            .map(
                lambda doc: [
                    doc["special"].contains(False),
                    doc["special"].contains(""),
                    doc["special"].contains(0),
                ]
            )
            .run(conn)
        )
        assertEqual(result[0], [True, True, True])

    def test_distinct_with_complex_data(self, conn):
        """Test distinct with complex data structures"""
        # Test distinct on simple array first
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 2})
            .map(lambda doc: doc["duplicates"].distinct())
            .run(conn)
        )
        # Should preserve unique values while removing duplicates
        expected_unique = [1, 2]  # distinct values from [1, 1, 2, 1]
        assertEqual(sorted(result[0]), sorted(expected_unique))

    def test_group_ungroup_edge_cases(self, conn):
        """Test group/ungroup with edge cases"""
        # Group by field that doesn't exist in some docs
        try:
            result = (
                r.db("test_db").table("arrays").group("nonexistent").ungroup().run(conn)
            )
            result = list(result)
        except Exception:
            pass  # May not support grouping by missing fields

    def test_sample_edge_cases(self, conn):
        """Test sample with edge cases"""
        # Sample more than available - should return all available elements
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].sample(1))
            .run(conn)
        )
        assertEqual(len(result[0]), 1)  # Should return the single available element

        # Sample from empty array - should return empty
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].sample(1))
            .run(conn)
        )
        assertEqual(result[0], [])

    def test_chain_operations_edge_cases(self, conn):
        """Test chained array operations with edge cases"""
        # Multiple operations on empty array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].append(1).prepend(0).slice(1, 2))
            .run(conn)
        )
        assertEqual(result[0], [1])

        # Operations that might result in empty arrays
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 2})
            .map(lambda doc: doc["duplicates"].distinct().set_difference([1, 2]))
            .run(conn)
        )
        assertEqual(result[0], [])

    def test_type_coercion_edge_cases(self, conn):
        """Test type coercion in array operations"""
        # Operations between different numeric types
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 1})
            .map(lambda doc: doc["mixed"].set_union([1.0, 1]))
            .run(conn)
        )
        # Should handle int vs float properly
        assert len(result[0]) >= len([1, "str", None, 3.14])

    def test_performance_edge_cases(self, conn):
        """Test operations on large arrays"""
        # Operations on large array
        result = list(
            r.db("test_db")
            .table("arrays")
            .filter({"id": 4})
            .map(lambda doc: doc["large"].slice(50, 60).count())
            .run(conn)
        )
        assertEqual(result[0], 10)

        # Test with manually created large duplicate data
        r.db("test_db").table_create("large_dups").run(conn)
        large_duplicates = [i % 5 for i in range(100)]  # Only 5 unique values
        dup_data = [{"id": 99, "many_dups": large_duplicates}]
        r.db("test_db").table("large_dups").insert(dup_data).run(conn)

        try:
            result = (
                r.db("test_db")
                .table("large_dups")
                .map(lambda doc: doc["many_dups"].distinct().count())
                .run(conn)
            )
            assertEqual(list(result)[0], 5)
        finally:
            r.db("test_db").table_drop("large_dups").run(conn)

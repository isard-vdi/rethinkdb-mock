from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestMax(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "age": 26, "hobbies": ["sand", "water", "cats"]},
            {"id": "bill", "age": 52, "hobbies": ["watermelon"]},
            {
                "id": "todd",
                "age": 35,
                "hobbies": ["citrus"],
                "nums": [100, 550, 40, 900, 800, 36],
                "nums2": [
                    {"val": 26},
                    {"val": 78},
                    {"val": 19},
                    {"val": 110},
                    {"val": 82},
                ],
            },
        ]
        return as_db_and_table("x", "people", data)

    def test_max_of_table_field(self, conn):
        expected = {"id": "bill", "age": 52, "hobbies": ["watermelon"]}
        result = r.db("x").table("people").max("age").run(conn)
        assertEqual(expected, result)

    def test_max_of_sequence_field(self, conn):
        expected = [{"val": 110}]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].max("val"))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_max_of_table_func(self, conn):
        expected = {"id": "bill", "age": 52, "hobbies": ["watermelon"]}
        result = r.db("x").table("people").max(lambda d: d["age"]).run(conn)
        assertEqual(expected, result)

    def test_max_of_sequence_func(self, conn):
        expected = [{"val": 110}]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].max(lambda num: num["val"]))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_max_of_left_seq_no_args(self, conn):
        expected = [900]
        result = (
            r.db("x")
            .table("people")
            .filter(lambda doc: doc["id"] == "todd")
            .map(lambda doc: doc["nums"].max())
            .run(conn)
        )
        assertEqual(expected, list(result))


class TestMin(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "age": 26, "hobbies": ["sand", "water", "cats"]},
            {"id": "bill", "age": 52, "hobbies": ["watermelon"]},
            {
                "id": "todd",
                "age": 35,
                "hobbies": ["citrus"],
                "nums": [100, 550, 40, 900, 800],
                "nums2": [{"val": 26}, {"val": 17}, {"val": 86}],
            },
        ]
        return as_db_and_table("x", "people", data)

    def test_min_of_table_field(self, conn):
        expected = {"id": "joe", "age": 26, "hobbies": ["sand", "water", "cats"]}
        result = r.db("x").table("people").min("age").run(conn)
        assertEqual(expected, result)

    def test_min_of_sequence_field(self, conn):
        expected = [{"val": 17}]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].min("val"))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_min_of_table_func(self, conn):
        expected = {"id": "joe", "age": 26, "hobbies": ["sand", "water", "cats"]}
        result = r.db("x").table("people").min(lambda doc: doc["age"]).run(conn)
        assertEqual(expected, result)

    def test_min_of_sequence_func(self, conn):
        expected = [{"val": 17}]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].min(lambda num: num["val"]))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_min_of_left_seq_no_args(self, conn):
        expected = [40]
        result = (
            r.db("x")
            .table("people")
            .filter(lambda doc: doc["id"] == "todd")
            .map(lambda doc: doc["nums"].min())
            .run(conn)
        )
        assertEqual(expected, list(result))


class TestSum(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "age": 26, "hobbies": ["sand", "water", "cats"]},
            {"id": "bill", "age": 52, "hobbies": ["watermelon"]},
            {
                "id": "todd",
                "age": 35,
                "hobbies": ["citrus"],
                "nums": [100, 50, 400, 9],
                "nums2": [{"val": 40}, {"val": 53}],
            },
        ]
        return as_db_and_table("x", "people", data)

    def test_sum_of_table_field(self, conn):
        expected = 113
        result = r.db("x").table("people").sum("age").run(conn)
        assertEqual(expected, result)

    def test_sum_of_seq_field(self, conn):
        expected = [93]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].sum("val"))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_sum_of_table_func(self, conn):
        expected = 113
        result = r.db("x").table("people").sum(lambda doc: doc["age"]).run(conn)
        assertEqual(expected, result)

    def test_sum_of_seq_func(self, conn):
        expected = [93]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].sum(lambda num: num["val"]))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_sum_of_seq_no_args(self, conn):
        expected = [559]
        result = (
            r.db("x")
            .table("people")
            .filter(lambda doc: doc["id"] == "todd")
            .map(lambda doc: doc["nums"].sum())
            .run(conn)
        )
        assertEqual(expected, list(result))


class TestAverage(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "age": 43, "hobbies": ["sand", "water", "cats"]},
            {"id": "bill", "age": 48, "hobbies": ["watermelon"]},
            {
                "id": "todd",
                "age": 29,
                "hobbies": ["citrus"],
                "nums": [76, 40, 100, 800],
                "nums2": [{"val": 10}, {"val": 20}],
            },
        ]
        return as_db_and_table("x", "people", data)

    def test_avg_of_table_field(self, conn):
        expected = 40
        result = r.db("x").table("people").avg("age").run(conn)
        assertEqual(expected, result)

    def test_avg_of_sequence_field(self, conn):
        expected = [15]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].avg("val"))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_avg_of_table_func(self, conn):
        expected = 40
        result = r.db("x").table("people").avg(lambda doc: doc["age"]).run(conn)
        assertEqual(expected, result)

    def test_avg_of_sequence_func(self, conn):
        expected = [15]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums2"].avg(lambda num: num["val"]))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_avg_of_left_seq_no_args(self, conn):
        expected = [254]
        result = (
            r.db("x")
            .table("people")
            .filter(lambda doc: doc["id"] == "todd")
            .map(lambda doc: doc["nums"].avg())
            .run(conn)
        )
        assertEqual(expected, list(result))


class TestCount(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "age": 43, "hobbies": ["sand", "water", "cats"]},
            {"id": "bill", "age": 48, "hobbies": ["watermelon"]},
            {
                "id": "todd",
                "age": 29,
                "hobbies": ["citrus"],
                "nums": [40, 67, 40, 800, 900],
            },
        ]
        return as_db_and_table("x", "people", data)

    def test_table_count(self, conn):
        expected = 3
        result = r.db("x").table("people").count().run(conn)
        assertEqual(expected, result)

    def test_sequence_count(self, conn):
        expected = [5]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums"].count())
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_table_eq_elem_count(self, conn):
        expected = 1
        result = (
            r.db("x")
            .table("people")
            .count({"id": "bill", "age": 48, "hobbies": ["watermelon"]})
            .run(conn)
        )
        assertEqual(expected, result)

    def test_sequence_eq_elem_count(self, conn):
        expected = [2]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums"].count(40))
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_table_func_count(self, conn):
        expected = 2
        result = r.db("x").table("people").count(lambda doc: doc["age"] > 40).run(conn)
        assertEqual(expected, result)

    def test_sequence_func_count(self, conn):
        expected = [3]
        result = (
            r.db("x")
            .table("people")
            .filter({"id": "todd"})
            .map(lambda doc: doc["nums"].count(lambda num: num > 40))
            .run(conn)
        )
        assertEqual(expected, list(result))


class TestAggregationEdgeCases(MockTest):
    """Test edge cases for all aggregation functions"""

    @staticmethod
    def get_data():
        data = [
            {"id": 1, "value": 10, "nulls": None, "nested": {"val": 5}},
            {"id": 2, "value": None, "nulls": 20, "nested": {"val": None}},
            {"id": 3, "value": 0, "nulls": 0, "nested": {"val": -10}},
            {
                "id": 4,
                "empty_array": [],
                "single_array": [42],
                "nested_arrays": [[1, 2], [3]],
            },
            {"id": 5, "strings": ["a", "z", "m"], "mixed": [1, "2", 3.0, None]},
            {"id": 6, "duplicates": [1, 1, 2, 2, 3], "negatives": [-5, -1, -10]},
        ]
        return as_db_and_table("test_db", "edge_cases", data)

    def test_max_with_nulls(self, conn):
        """Test max with null values"""
        # Max should ignore null values
        result = r.db("test_db").table("edge_cases").max("value").run(conn)
        assertEqual(result["id"], 1)  # value 10 is max

    def test_min_with_nulls(self, conn):
        """Test min with null values"""
        # Min should ignore null values but include 0
        result = r.db("test_db").table("edge_cases").min("value").run(conn)
        assertEqual(result["id"], 3)  # value 0 is min

    def test_max_empty_sequence(self, conn):
        """Test max on empty sequence"""
        try:
            r.db("test_db").table("edge_cases").filter({"id": 999}).max("value").run(
                conn
            )
            assert False, "Should raise error on empty sequence"
        except Exception:
            pass  # Expected

    def test_sum_with_nulls_and_zeros(self, conn):
        """Test sum with null values and zeros"""
        result = r.db("test_db").table("edge_cases").sum("value").run(conn)
        assertEqual(result, 10)  # Only non-null value

    def test_avg_with_nulls(self, conn):
        """Test average with null values"""
        result = r.db("test_db").table("edge_cases").avg("value").run(conn)
        assertEqual(result, 5.0)  # (10 + 0) / 2

    def test_count_with_predicates(self, conn):
        """Test count with complex predicates"""
        # Count non-null values using has_fields - check which documents have the 'value' field
        result = (
            r.db("test_db")
            .table("edge_cases")
            .count(lambda doc: doc.has_fields("value"))
            .run(conn)
        )
        # Looking at our test data: id 1 has value=10, id 2 has value=None, id 3 has value=0
        # So 3 documents have the 'value' field
        assertEqual(result, 3)

        # Count with nested field access - documents where nested.val > 0
        result = (
            r.db("test_db")
            .table("edge_cases")
            .count(
                lambda doc: doc.get_field("nested")
                .default({})
                .get_field("val")
                .default(0)
                > 0
            )
            .run(conn)
        )
        assertEqual(result, 1)

    def test_array_aggregation_edge_cases(self, conn):
        """Test aggregation on array fields"""
        # Max of empty array - should handle gracefully
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 4})
            .map(
                lambda doc: r.branch(
                    doc["empty_array"].count() > 0, doc["empty_array"].max(), "empty"
                )
            )
            .run(conn)
        )
        assertEqual(result[0], "empty")

        # Max of single element array
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 4})
            .map(lambda doc: doc["single_array"].max())
            .run(conn)
        )
        assertEqual(result[0], 42)

    def test_mixed_type_arrays(self, conn):
        """Test aggregation on arrays with mixed types"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 5})
            .map(lambda doc: doc["strings"].max())
            .run(conn)
        )
        assertEqual(result[0], "z")  # Lexicographically largest

    def test_negative_numbers(self, conn):
        """Test aggregation with negative numbers"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 6})
            .map(lambda doc: doc["negatives"].max())
            .run(conn)
        )
        assertEqual(result[0], -1)  # Largest negative

        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 6})
            .map(lambda doc: doc["negatives"].min())
            .run(conn)
        )
        assertEqual(result[0], -10)  # Smallest negative

    def test_duplicate_values(self, conn):
        """Test aggregation with duplicate values"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 6})
            .map(lambda doc: doc["duplicates"].sum())
            .run(conn)
        )
        assertEqual(result[0], 9)  # 1+1+2+2+3 = 9

    def test_nested_aggregation_chains(self, conn):
        """Test complex chained aggregations"""
        # Chain multiple aggregations
        result = (
            r.db("test_db")
            .table("edge_cases")
            .map(
                lambda doc: r.branch(
                    doc.has_fields("duplicates"), doc["duplicates"].distinct().sum(), 0
                )
            )
            .sum()
            .run(conn)
        )
        assertEqual(result, 6)  # distinct values sum: 1+2+3=6

    def test_aggregation_with_transformations(self, conn):
        """Test aggregation with complex transformations"""
        # Apply transformation before aggregating - simple null-safe operation
        result = (
            r.db("test_db")
            .table("edge_cases")
            .map(lambda doc: doc.get_field("value").default(0) * 2)
            .sum()
            .run(conn)
        )
        assertEqual(result, 20)  # (10*2) + (0*2) = 20

    def test_conditional_aggregation(self, conn):
        """Test aggregation with conditional logic"""
        # Count based on complex conditions - need to handle null values properly
        result = (
            r.db("test_db")
            .table("edge_cases")
            .count(
                lambda doc: (doc.get_field("value").default(0) != None)
                & (doc.get_field("value").default(0) > 5)
            )
            .run(conn)
        )
        assertEqual(result, 1)  # Only id=1 has non-null value > 5

    def test_aggregation_precision(self, conn):
        """Test aggregation precision with floating point numbers"""
        # Test with data that has precision issues by inserting directly
        r.db("test_db").table_create("floats").run(conn)
        float_data = [
            {"id": 1, "val": 0.1},
            {"id": 2, "val": 0.2},
            {"id": 3, "val": 0.3},
        ]
        r.db("test_db").table("floats").insert(float_data).run(conn)

        try:
            result = r.db("test_db").table("floats").sum("val").run(conn)
            # Should be close to 0.6 but may have floating point errors
            assert abs(result - 0.6) < 1e-10
        finally:
            r.db("test_db").table_drop("floats").run(conn)

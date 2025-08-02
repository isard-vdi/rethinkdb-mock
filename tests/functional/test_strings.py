from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestStrings(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "a", "text": "something  with spaces"},
            {"id": "b", "text": "some,csv,file"},
            {"id": "c", "text": "someething"},
        ]
        return as_db_and_table("library", "texts", data)

    def test_upcase(self, conn):
        expected = set(["SOMETHING  WITH SPACES", "SOME,CSV,FILE", "SOMEETHING"])
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].upcase())
            .run(conn)
        )
        assertEqual(expected, set(list(result)))

    def test_downcase(self, conn):
        expected = set(["something  with spaces", "some,csv,file", "someething"])
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].downcase())
            .run(conn)
        )
        assertEqual(expected, set(list(result)))

    def test_split_1(self, conn):
        expected = [["something", "with", "spaces"], ["some,csv,file"], ["someething"]]
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].split())
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_split_2(self, conn):
        expected = [["something  with spaces"], ["some", "csv", "file"], ["someething"]]
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].split(","))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_split_3(self, conn):
        expected = [
            ["som", "thing  with spac", "s"],
            ["som", ",csv,fil", ""],
            ["som", "", "thing"],
        ]
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].split("e"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_split_4(self, conn):
        expected = [
            ["som", "thing  with spaces"],
            ["som", ",csv,file"],
            ["som", "ething"],
        ]
        result = (
            r.db("library")
            .table("texts")
            .map(lambda doc: doc["text"].split("e", 1))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestStringEdgeCases(MockTest):
    """Test edge cases for string manipulation functions"""

    @staticmethod
    def get_data():
        data = [
            {"id": 1, "empty": "", "single": "a", "unicode": "héllo wörld"},
            {"id": 2, "whitespace": "  \t\n  ", "mixed": "Hello123!@#"},
            {"id": 3, "nulls": None, "special": "line1\nline2\rline3\tline4"},
            {"id": 4, "long": "a" * 1000, "numbers": "12345"},
            {
                "id": 5,
                "punctuation": "Hello, World! How are you?",
                "case_mix": "CamelCaseString",
            },
        ]
        return as_db_and_table("test_db", "strings", data)

    def test_upcase_downcase_edge_cases(self, conn):
        """Test case conversion with edge cases"""
        # Empty string
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].upcase())
            .run(conn)
        )
        assertEqual(result[0], "")

        # Unicode characters
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["unicode"].upcase())
            .run(conn)
        )
        assertEqual(result[0], "HÉLLO WÖRLD")

        # Mixed case with numbers and symbols
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 2})
            .map(lambda doc: doc["mixed"].downcase())
            .run(conn)
        )
        assertEqual(result[0], "hello123!@#")

    def test_split_edge_cases(self, conn):
        """Test split with edge cases"""
        # Split empty string
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"].split())
            .run(conn)
        )
        assertEqual(result[0], [])

        # Split on non-existent delimiter
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["single"].split("x"))
            .run(conn)
        )
        assertEqual(result[0], ["a"])

        # Split with special characters
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 3})
            .map(lambda doc: doc["special"].split("\n"))
            .run(conn)
        )
        assertEqual(len(result[0]), 2)  # Should split on newline

    def test_concatenation_edge_cases(self, conn):
        """Test string concatenation with edge cases"""
        # Concatenate with empty string
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"] + doc["single"])
            .run(conn)
        )
        assertEqual(result[0], "a")

        # Concatenate unicode strings
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["unicode"] + " " + doc["single"])
            .run(conn)
        )
        assertEqual(result[0], "héllo wörld a")

    def test_string_comparison_edge_cases(self, conn):
        """Test string comparison edge cases"""
        # Compare empty strings
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["empty"] == "")
            .run(conn)
        )
        assertEqual(result[0], True)

        # Lexicographic comparison
        result = list(
            r.db("test_db")
            .table("strings")
            .filter({"id": 1})
            .map(lambda doc: doc["single"] < "b")
            .run(conn)
        )
        assertEqual(result[0], True)

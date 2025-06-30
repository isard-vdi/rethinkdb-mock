from rethinkdb import r
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestAdditionalDatetime(MockTest):
    @staticmethod
    def get_data():
        return {
            "dbs": {
                "test": {
                    "tables": {
                        "events": [
                            {"id": 1, "timestamp": r.iso8601("2023-01-15T10:30:00Z")},
                            {"id": 2, "timestamp": r.iso8601("2023-06-20T15:45:00Z")},
                        ]
                    }
                }
            }
        }

    def test_day_of_year(self, conn):
        # Test day of year extraction
        time_obj = r.iso8601("2023-01-15T10:30:00Z")
        result = time_obj.day_of_year().run(conn)
        assertEqual(result, 15)  # January 15th is the 15th day of the year

    def test_in_timezone(self, conn):
        # Test timezone conversion
        utc_time = r.iso8601("2023-01-15T10:30:00Z")
        est_time = utc_time.in_timezone("-05:00")
        # Should still be the same moment in time, just different representation
        result = est_time.to_iso8601().run(conn)
        assert "2023-01-15" in result  # Date should be the same or close

    def test_to_iso8601(self, conn):
        # Test ISO8601 string conversion
        time_obj = r.iso8601("2023-01-15T10:30:00Z")
        result = time_obj.to_iso8601().run(conn)
        assert "2023-01-15" in result
        assert "T" in result

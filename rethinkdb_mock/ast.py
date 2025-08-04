import datetime
import json
import operator
import random
import uuid

import dateutil.parser
from future.utils import iteritems
from future.utils import text_type
from past.utils import old_div
from rethinkdb.errors import ReqlNonExistenceError
from rethinkdb.errors import RqlRuntimeError

from rethinkdb_mock import ast_base
from rethinkdb_mock import joins
from rethinkdb_mock import rtime
from rethinkdb_mock import util
from rethinkdb_mock.ast_base import BinExp
from rethinkdb_mock.ast_base import ByFuncBase
from rethinkdb_mock.ast_base import LITERAL_OBJECT
from rethinkdb_mock.ast_base import MakeArray
from rethinkdb_mock.ast_base import MonExp
from rethinkdb_mock.ast_base import RBase
from rethinkdb_mock.ast_base import RFunc
from rethinkdb_mock.ast_base import Ternary
from rethinkdb_mock.scope import Scope

# #################
#   Query handlers
# #################


class Literal(MonExp):
    def do_run(self, obj, arg, scope):
        return LITERAL_OBJECT.from_dict(obj)


class RError0(RBase):
    def __init__(self, *args):
        pass

    def run(self, arg, conn):
        self.raise_rql_runtime_error("DEFAULT MESSAGE")


class RError1(MonExp):
    def do_run(self, msg, arg, scope):
        self.raise_rql_runtime_error(msg)


class Uuid(RBase):
    def run(self, arg, scope):
        return str(uuid.uuid4())


class RDb(MonExp):
    def do_run(self, db_name, arg, scope):
        if hasattr(self, "mockdb_ref"):
            db = self.mockdb_ref
        elif arg is not None:
            db = arg
        else:
            # Try to get database context from scope
            db = scope.get_current_db()
            if db is None:
                raise RuntimeError(
                    "No database context available. This usually happens when r.db() is used "
                    "inside a lambda function without proper context propagation."
                )
        return db.get_db(db_name)

    def find_db_scope(self):
        return self.left.run(None, Scope({}))


class TypeOf(MonExp):
    def do_run(self, val, arg, scope):
        type_map = {
            str: "STRING",
            dict: "OBJECT",
            int: "NUMBER",
            float: "NUMBER",
            bool: "BOOL",
        }
        if val is None:
            return "NULL"
        else:
            val_type = type(val)
            if val_type in type_map:
                return type_map[val_type]
            elif util.is_iterable(val):
                return "ARRAY"
        raise TypeError


class Distinct(MonExp):
    def do_run(self, table_or_seq, arg, scope):
        if "index" in self.optargs:
            # table
            table_or_seq = table_or_seq._index_values(self.optargs["index"])
        return list(util.dictable_distinct(table_or_seq))


class Zip(MonExp):
    def do_run(self, sequence, arg, scope):
        out = []
        for elem in sequence:
            out.append(util.extend(elem["left"], elem["right"]))
        return out


class IsEmpty(MonExp):
    def do_run(self, left, arg, scope):
        return len(left) == 0


class RVar(MonExp):
    def do_run(self, symbol_name, arg, scope):
        return scope.get_sym(symbol_name)


class Not(MonExp):
    def do_run(self, left, arg, scope):
        return not left


class Keys(MonExp):
    def do_run(self, left, arg, scope):
        return list(left.keys())


class Asc(MonExp):
    def do_run(self, left, arg, scope):
        return (left, "ASC")


class Desc(MonExp):
    def do_run(self, left, arg, scope):
        return (left, "DESC")


class Json(MonExp):
    def do_run(self, json_str, arg, scope):
        return json.loads(json_str)


class RTable(BinExp):
    def find_table_scope(self):
        return self.right.run(None, Scope({}))

    def has_table_scope(self):
        return True

    def do_run(self, data, table_name, arg, scope):
        return data.get_table(table_name)


class Bracket(BinExp):
    def do_run(self, thing, thing_attr, arg, scope):
        from rethinkdb_mock import util
        from rethinkdb_mock.db import MockTableData

        # If thing is a MockTableData (table), map the bracket operation over its rows
        if isinstance(thing, MockTableData):
            return [row[thing_attr] for row in thing]
        else:
            # For everything else (documents, lists, etc.), just access the attribute/index
            if isinstance(thing, dict):
                if thing_attr in thing:
                    return thing[thing_attr]
                else:
                    # RethinkDB raises an error for missing fields on single documents
                    raise RqlRuntimeError(f"No attribute `{thing_attr}` in object")
            else:
                return thing[thing_attr]  # For arrays, still throw IndexError


class Get(BinExp):
    def do_run(self, left, right, arg, scope):
        return util.find_first(util.match_attr("id", right), left)


class GetAll(BinExp):
    def do_run(self, left, right, arg, scope):
        if "index" in self.optargs and self.optargs["index"] != "id":
            index_func, is_multi = self.find_index_func_for_scope(
                self.optargs["index"], arg
            )

            if isinstance(index_func, RFunc):

                def map_fn(d):
                    return index_func.run([d], scope)

            else:
                map_fn = index_func

            result = []
            left = list(left)

            # Evaluate right if it's an AST node
            if hasattr(right, "run"):
                search_keys = right.run([], scope)
            else:
                search_keys = right

            # For compound indexes, we need to handle the case where search_keys is a single compound key
            # vs multiple separate keys. If search_keys is a list of non-list items, and we're dealing with
            # a compound index, then search_keys might be a single compound key
            if is_multi and isinstance(search_keys, list) and len(search_keys) > 0:
                # Check if this looks like a single compound key vs multiple simple keys
                # If all elements are simple (not lists), and we get no matches treating them as separate keys,
                # we should try treating the whole thing as a single compound key
                first_elem_index_value = None
                if len(left) > 0:
                    first_elem_index_value = map_fn(left[0])

                # If the index produces compound values (lists), and our search_keys is a list of simple values,
                # treat search_keys as a single compound key
                if (
                    first_elem_index_value
                    and isinstance(first_elem_index_value, list)
                    and len(first_elem_index_value) > 0
                    and isinstance(first_elem_index_value[0], list)
                    and not any(isinstance(key, list) for key in search_keys)
                ):
                    # This looks like a single compound key
                    search_keys = [search_keys]

            if is_multi:
                # For multi-indexes, each document can appear multiple times
                # if it matches multiple search keys
                for elem in left:
                    indexed = map_fn(elem)

                    if not isinstance(indexed, (tuple, list)):
                        indexed = [indexed]

                    # Convert lists to tuples for hashability when using sets
                    indexed_hashable = []
                    for item in indexed:
                        if isinstance(item, list):
                            indexed_hashable.append(tuple(item))
                        else:
                            indexed_hashable.append(item)
                    indexed_set = set(indexed_hashable)

                    # Check each search key separately - document can match multiple times
                    for match_item in search_keys:
                        # Convert match_item to tuple if it's a list for comparison
                        if isinstance(match_item, list):
                            match_item_comparable = tuple(match_item)
                        else:
                            match_item_comparable = match_item

                        if match_item_comparable in indexed_set:
                            result.append(elem)  # Allow duplicates for multi-index
            else:
                for elem in left:
                    elem_index_value = map_fn(elem)

                    # Check if elem_index_value matches any of the search keys
                    matched = False

                    # Handle compound indexes (arrays) specially
                    if isinstance(elem_index_value, (list, tuple)):
                        # Check if we have multiple compound keys or a single compound key
                        # Multiple compound keys: [["Smith", "John"], ["Doe", "John"]]
                        # Single compound key: ["Smith", "John"]

                        # If search_keys is a list where all elements are lists/tuples,
                        # then we have multiple compound keys
                        if (
                            isinstance(search_keys, list)
                            and len(search_keys) > 0
                            and all(
                                isinstance(key, (list, tuple)) for key in search_keys
                            )
                        ):
                            # Multiple compound keys to search for
                            for search_value in search_keys:
                                if len(elem_index_value) == len(search_value) and all(
                                    a == b
                                    for a, b in zip(elem_index_value, search_value)
                                ):
                                    matched = True
                                    break
                        else:
                            # Single compound key: search_keys is the compound key itself
                            if (
                                isinstance(search_keys, (list, tuple))
                                and len(elem_index_value) == len(search_keys)
                                and all(
                                    a == b
                                    for a, b in zip(elem_index_value, search_keys)
                                )
                            ):
                                matched = True
                    else:
                        # Simple value comparison for non-compound indexes
                        for search_value in search_keys:
                            if elem_index_value == search_value:
                                matched = True
                                break

                    if matched:
                        result.append(elem)
            return result

        else:
            # Handle non-indexed queries (regular ID-based get_all)
            if hasattr(right, "run"):
                search_keys = right.run([], scope)
            else:
                search_keys = right
            return list(filter(util.match_attr_multi("id", search_keys), left))


class BinOp(BinExp):
    def do_run(self, left, right, arg, scope):
        if isinstance(left, datetime.datetime) and isinstance(right, int):
            return self.__class__.binop(left, datetime.timedelta(seconds=right))

        return self.__class__.binop(left, right)


class Gt(BinOp):
    binop = operator.gt


class Gte(BinOp):
    binop = operator.ge


class Lt(BinOp):
    binop = operator.lt


class Lte(BinOp):
    binop = operator.le


class Eq(BinOp):
    binop = operator.eq


class Neq(BinOp):
    binop = operator.ne


class Add(BinOp):
    binop = operator.add

    def __init__(self, left, right=None, optargs=None):
        if right is None and isinstance(left, Args):
            # This is r.add(r.args([...])) - store the Args node
            self.args_node = left
            self.is_args_expansion = True
            # Initialize as RBase since we don't have left/right
            RBase.__init__(self, optargs)
        else:
            # Normal binary add
            self.is_args_expansion = False
            super().__init__(left, right, optargs)

    def run(self, arg, scope):
        if self.is_args_expansion:
            # Expand the args array and sum all values
            args_values = self.args_node.run(arg, scope)
            return sum(args_values)
        else:
            # Normal binary operation
            return super().run(arg, scope)


class MultiAdd(RBase):
    """Handle r.add(a, b, c, ...) with multiple arguments"""

    def __init__(self, args, optargs=None):
        self.args = args
        super().__init__(optargs)

    def run(self, arg, scope):
        values = [a.run(arg, scope) if hasattr(a, "run") else a for a in self.args]
        return sum(values)


class Sub(BinOp):
    binop = operator.sub


class Mul(BinOp):
    binop = operator.mul


class Div(BinOp):
    binop = staticmethod(old_div)


class Mod(BinOp):
    binop = operator.mod


# Math functions
class Round(MonExp):
    """Round a number to the nearest integer or to a specified number of decimal places"""

    def do_run(self, number, arg, scope):
        return round(number)


class RoundWithPrecision(BinExp):
    """Round a number to a specified number of decimal places"""

    def do_run(self, number, precision, arg, scope):
        return round(number, precision)


class Ceil(MonExp):
    """Round a number up to the nearest integer"""

    def do_run(self, number, arg, scope):
        import math

        return math.ceil(number)


class Floor(MonExp):
    """Round a number down to the nearest integer"""

    def do_run(self, number, arg, scope):
        import math

        return math.floor(number)


# Control structure functions
class Range1(MonExp):
    """Generate a range from 0 to n (exclusive)"""

    def do_run(self, end_val, arg, scope):
        return list(range(int(end_val)))


class Range2(BinExp):
    """Generate a range from start to end (exclusive)"""

    def do_run(self, start_val, end_val, arg, scope):
        return list(range(int(start_val), int(end_val)))


class Range3(Ternary):
    """Generate a range from start to end (exclusive) with step"""

    def do_run(self, start_val, end_val, step_val, arg, scope):
        return list(range(int(start_val), int(end_val), int(step_val)))


# Bitwise operations
class BitAnd(BinExp):
    """Bitwise AND operation"""

    def do_run(self, left_val, right_val, arg, scope):
        return int(left_val) & int(right_val)


class BitOr(BinExp):
    """Bitwise OR operation"""

    def do_run(self, left_val, right_val, arg, scope):
        return int(left_val) | int(right_val)


class BitXor(BinExp):
    """Bitwise XOR operation"""

    def do_run(self, left_val, right_val, arg, scope):
        return int(left_val) ^ int(right_val)


class BitNot(MonExp):
    """Bitwise NOT operation"""

    def do_run(self, val, arg, scope):
        return ~int(val)


class And(BinOp):
    binop = operator.and_


class Or(BinOp):
    binop = operator.or_


class Reduce(ByFuncBase):
    def do_run(self, sequence, reduce_fn, arg, scope):
        if len(sequence) == 0:
            raise ReqlNonExistenceError("Cannot reduce over an empty stream")

        if len(sequence) == 1:
            return sequence[0]

        first, second = sequence[0:2]
        result = reduce_fn([first, second])
        for elem in sequence[2:]:
            result = reduce_fn([elem, result])
        return result


class UpdateBase(object):
    def __init__(self, *args):
        pass

    def get_update_settings(self):
        defaults = {"durability": "hard", "return_changes": False, "non_atomic": False}
        return util.extend(defaults, self.optargs)

    def validate_nested_query_status(self):
        if self.right.has_table_scope() and (
            not self.get_update_settings()["non_atomic"]
        ):
            self.raise_rql_runtime_error(
                "attempted nested query in update without non-atomic flag"
            )

    def update_table(self, result_sequence, arg, scope):
        settings = self.get_update_settings()
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()
        result_sequence = util.ensure_list(result_sequence)
        result, report = arg.update_by_id_in_table_in_db(
            current_db, current_table, result_sequence
        )
        if not settings["return_changes"]:
            del report["changes"]
        return result, report


class UpdateByFunc(ByFuncBase, UpdateBase):
    def do_run(self, sequence, map_fn, arg, scope):
        self.validate_nested_query_status()

        def mapper(doc):
            ext_with = map_fn(doc)
            return ast_base.rql_merge_with(ext_with, doc)

        return self.update_table(util.maybe_map(mapper, sequence), arg, scope)


class UpdateWithObj(BinExp, UpdateBase):
    def do_run(self, sequence, to_update, arg, scope):
        self.validate_nested_query_status()
        return self.update_table(
            util.maybe_map(ast_base.rql_merge_with(to_update), sequence), arg, scope
        )


class Replace(BinExp, UpdateBase):
    def do_run(self, left, right, arg, scope):
        return self.update_table(right, arg, scope)


class Delete(MonExp):
    def get_delete_settings(self):
        defaults = {"durability": "hard", "return_changes": False}
        return util.extend(defaults, self.optargs)

    def do_run(self, sequence, arg, scope):
        current_table = self.find_table_scope()
        current_db = self.find_db_scope()
        if isinstance(sequence, dict):
            sequence = [sequence]
        else:
            sequence = list(sequence)
        result, report = arg.remove_by_id_in_table_in_db(
            current_db, current_table, sequence
        )
        if not self.get_delete_settings()["return_changes"]:
            del report["changes"]
        return result, report


class Insert(BinExp):
    def get_insert_settings(self):
        defaults = {"durability": "hard", "return_changes": False, "conflict": "error"}
        return util.extend(defaults, self.optargs)

    def do_run(self, sequence, to_insert, arg, scope):
        current_table = self.find_table_scope()
        current_db = self.find_db_scope()
        if isinstance(to_insert, dict):
            to_insert = [to_insert]
        generated_keys = list()

        def ensure_id(elem):
            if ("id" not in elem) or (elem["id"] is None):
                uid = text_type(uuid.uuid4())
                elem = util.extend(elem, {"id": uid})
                generated_keys.append(uid)
            return elem

        to_insert = list(map(ensure_id, list(to_insert)))
        settings = self.get_insert_settings()
        result, report = arg.insert_into_table_in_db(
            current_db, current_table, to_insert, conflict=settings["conflict"]
        )
        if not settings["return_changes"]:
            del report["changes"]
        if generated_keys:
            report["generated_keys"] = generated_keys
        return result, report


class FilterWithFunc(ByFuncBase):
    def do_run(self, sequence, filt_fn, arg, scope):
        return list(filter(filt_fn, sequence))


class FilterWithObj(BinExp):
    def do_run(self, sequence, to_match, arg, scope):
        return list(filter(util.match_attrs(to_match), sequence))


class MapWithRFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        try:
            result = list(map(map_fn, sequence))
        except KeyError as k:
            message = f"Missing field '{k}'"
            self.raise_rql_runtime_error(message)
        return result


class WithoutPoly(BinExp):
    def do_run(self, left, attrs, arg, scope):
        return util.maybe_map(util.without(attrs), left)


class PluckPoly(BinExp):
    def do_run(self, left, attrs, arg, scope):
        if isinstance(attrs, str):
            attrs = [attrs]

        return util.maybe_map(util.pluck_with(attrs), left)


class MergePolyWithRFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        def mapper(doc):
            ext_with = map_fn(doc)

            if ast_base.is_literal(ext_with):
                self.raise_rql_runtime_error("invalid top-level r.literal()")
            elif ast_base.has_nested_literal(ext_with):
                self.raise_rql_runtime_error("invalid nested r.literal()")

            return ast_base.rql_merge_with(ext_with, doc)

        return util.maybe_map(mapper, sequence)


class HasFields(BinExp):
    def do_run(self, left, fields, arg, scope):
        return util.maybe_filter(util.has_attrs(fields), left)


class WithFields(BinExp):
    def do_run(self, sequence, keys, arg, scope):
        # WithFields should select only the specified fields from each document
        # keys might be a single field name, a list of field names, or individual arguments

        # If keys is a list of AST nodes (from multiple arguments), evaluate them
        if isinstance(keys, list) and all(hasattr(k, "run") for k in keys):
            key_list = [k.run(arg, scope) for k in keys]
        elif hasattr(keys, "run"):
            # Single AST node
            evaluated_keys = keys.run(arg, scope)
            if isinstance(evaluated_keys, str):
                key_list = [evaluated_keys]
            elif isinstance(evaluated_keys, list):
                key_list = evaluated_keys
            else:
                key_list = [evaluated_keys]
        elif isinstance(keys, str):
            key_list = [keys]
        elif isinstance(keys, list):
            key_list = keys
        else:
            key_list = [keys]

        result = []
        for elem in sequence:
            if isinstance(elem, dict):
                # Create a new dict with only the specified fields
                filtered_elem = {k: elem[k] for k in key_list if k in elem}
                result.append(filtered_elem)
            else:
                # If not a dict, can't select fields
                result.append(elem)

        return result


class WithFieldsMulti(RBase):
    """Handle with_fields with multiple field arguments"""

    def __init__(self, sequence, field_args, optargs=None):
        self.sequence = sequence
        self.field_args = field_args  # List of RQL field name nodes
        super().__init__(optargs)

    def run(self, arg, scope):
        # Get the sequence
        sequence_data = self.sequence.run(arg, scope)

        # Evaluate each field name
        field_names = []
        for field_node in self.field_args:
            if hasattr(field_node, "run"):
                field_names.append(field_node.run(arg, scope))
            else:
                field_names.append(field_node)

        # Apply field selection
        result = []
        for elem in sequence_data:
            if isinstance(elem, dict):
                # Create a new dict with only the specified fields
                filtered_elem = {k: elem[k] for k in field_names if k in elem}
                result.append(filtered_elem)
            else:
                # If not a dict, can't select fields
                result.append(elem)

        return result


class ConcatMap(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.cat(*[util.map_with(map_fn, elem) for elem in sequence])


class Skip(BinExp):
    def do_run(self, sequence, num, arg, scope):
        return util.drop(num)(sequence)


class Limit(BinExp):
    def do_run(self, sequence, num, arg, scope):
        return util.take(num)(sequence)


class Slice(BinExp):
    def do_run(self, sequence, indices, arg, scope):
        # indices is now an RDatum containing [start, end] or [start]
        if hasattr(indices, "run"):
            indices_list = indices.run(arg, scope)
        else:
            indices_list = indices

        start = indices_list[0] if len(indices_list) > 0 else 0
        end = indices_list[1] if len(indices_list) > 1 else None

        return util.slice_with(start, end)(sequence)


class Nth(BinExp):
    def do_run(self, sequence, n, arg, scope):
        return util.nth(n)(sequence)


class Sum1(MonExp):
    def do_run(self, sequence, arg, scope):
        return util.safe_sum(sequence)


class SumByField(BinExp):
    def do_run(self, sequence, field, arg, scope):
        return util.safe_sum([util.getter(field)(elem) for elem in sequence])


class SumByFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.safe_sum(list(map(map_fn, sequence)))


class Max1(MonExp):
    def do_run(self, sequence, arg, scope):
        return max(list(sequence))


class MaxByField(BinExp):
    def do_run(self, sequence, field, arg, scope):
        return util.max_mapped(util.getter(field), sequence)


class MaxByFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.max_mapped(map_fn, sequence)


class Avg1(MonExp):
    def do_run(self, sequence, arg, scope):
        return util.safe_average(list(sequence))


class AvgByField(BinExp):
    def do_run(self, sequence, field, arg, scope):
        return util.safe_average(list(map(util.getter(field), sequence)))


class AvgByFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.safe_average(list(map(map_fn, sequence)))


class Count1(MonExp):
    def do_run(self, sequence, arg, scope):
        return len(list(sequence))


class CountGroup(MonExp):
    def do_run(self, sequence, arg, scope):
        return {k: len(v) for (k, v) in sequence.items()}


class CountByEq(BinExp):
    def do_run(self, sequence, to_match, arg, scope):
        return len([elem for elem in sequence if elem == to_match])


class CountByFunc(ByFuncBase):
    def do_run(self, sequence, filter_fn, arg, scope):
        return len(list(filter(filter_fn, list(sequence))))


class Min1(MonExp):
    def do_run(self, sequence, arg, scope):
        return min(list(sequence))


class MinByField(BinExp):
    def do_run(self, sequence, field, arg, scope):
        return util.min_mapped(util.getter(field), sequence)


class MinByFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.min_mapped(map_fn, sequence)


class GroupByField(BinExp):
    def do_run(self, elems, field, arg, scope):
        return util.group_by_func(util.getter(field), elems)


class GroupByFunc(ByFuncBase):
    def do_run(self, sequence, map_fn, arg, scope):
        return util.group_by_func(map_fn, sequence)


class Append(BinExp):
    def do_run(self, sequence, value, arg, scope):
        return util.append(value, sequence)


class Prepend(BinExp):
    def do_run(self, sequence, value, arg, scope):
        return util.prepend(value, sequence)


class OrderByFunc(ByFuncBase):
    def do_run(self, sequence, func, arg, scope):
        tups = [(item, func(item)) for item in sequence]
        tups.sort(key=lambda x: x[1])
        return [item[0] for item in tups]


class OrderByKeys(BinExp):
    def do_run(self, sequence, keys, arg, scope):
        # Handle index-based ordering if an index is specified in optargs
        if "index" in self.optargs:
            index_name = self.optargs["index"]
            # Get the index function
            index_func, _ = self.find_index_func_for_scope(index_name, arg)

            if isinstance(index_func, RFunc):

                def map_fn(d):
                    return index_func.run([d], scope)

            else:
                map_fn = index_func

            # Create a list of (document, sort_key) tuples
            tups = [(item, map_fn(item)) for item in sequence]

            # Sort by the index values
            tups.sort(key=lambda x: tuple(x[1]) if isinstance(x[1], list) else x[1])

            return [item[0] for item in tups]
        else:
            return util.sort_by_many(keys, sequence)


class Random0(RBase):
    def __init__(self, optargs={}):
        self.optargs = optargs

    def run(self, arg, scope):
        return random.random()


class Random1(MonExp):
    def do_run(self, max_num, arg, scope):
        if "float" in self.optargs and self.optargs["float"]:
            return random.uniform(0, max_num)
        else:
            return random.randint(0, max_num)


class Random2(BinExp):
    def do_run(self, min_num, max_num, arg, scope):
        if "float" in self.optargs and self.optargs["float"]:
            return random.uniform(min_num, max_num)
        else:
            return random.randint(min_num, max_num)


class Union(BinExp):
    def do_run(self, left, right, arg, scope):
        return list(left) + list(right)


class Sample(BinExp):
    def do_run(self, sequence, sample_n, arg, scope):
        sequence_list = list(sequence)
        # Handle edge case where sample size is larger than population
        if sample_n >= len(sequence_list):
            return sequence_list
        # Handle edge case where sequence is empty
        if len(sequence_list) == 0:
            return []
        return random.sample(sequence_list, sample_n)


class OffsetsOfValue(BinExp):
    def do_run(self, sequence, test_val, arg, scope):
        return util.indices_of_passing(util.eq(test_val), list(sequence))


class OffsetsOfFunc(ByFuncBase):
    def do_run(self, sequence, test_fn, arg, scope):
        return util.indices_of_passing(test_fn, list(sequence))


class SetInsert(BinExp):
    def do_run(self, left, right, arg, scope):
        return list(set(util.append(right, list(left))))


class SetUnion(BinExp):
    def do_run(self, left, right, arg, scope):
        return list(set(list(left)).union(set(list(right))))


class SetIntersection(BinExp):
    def do_run(self, left, right, arg, scope):
        return list(set(list(left)).intersection(set(list(right))))


class SetDifference(BinExp):
    def do_run(self, left, right, arg, scope):
        return list(set(list(left)) - set(list(right)))


class Do(ByFuncBase):
    def do_run(self, left, func, arg, scope):
        return func(left)


class UnGroup(MonExp):
    def do_run(self, grouped_seq, arg, scope):
        for group_name, group_vals in iteritems(grouped_seq):
            yield {"group": group_name, "reduction": group_vals}


class Branch(RBase):
    def __init__(self, test, if_true, if_false, optargs={}):
        self.test = test
        self.if_true = if_true
        self.if_false = if_false

    def run(self, arg, scope):
        test = self.test.run(arg, scope)
        if test is False or test is None:
            return self.if_false.run(arg, scope)
        else:
            return self.if_true.run(arg, scope)


class Difference(BinExp):
    def do_run(self, sequence, to_remove, arg, scope):
        to_remove = set(to_remove)
        result = []
        for elem in sequence:
            if elem not in to_remove:
                result.append(elem)
        return result


class ContainsElems(BinExp):
    def do_run(self, sequence, test_for, arg, scope):
        sequence = list(sequence)
        result = True
        for elem in test_for:
            if elem not in sequence:
                result = False
                break
        return result


class ContainsFuncs(RBase):
    def __init__(self, left, right, optargs={}):
        assert isinstance(right, MakeArray)
        self.left = left
        self.right = right
        self.optargs = optargs

    def iter_preds(self, scope):
        for pred in self.right.vals:
            yield (lambda doc: pred.run([doc], scope))

    def run(self, arg, scope):
        sequence = list(self.left.run(arg, scope))
        result = True
        for pred in self.iter_preds(scope):
            if not util.any_passing(pred, sequence):
                result = False
                break
        return result


#   #################################
#     Table and database manipulation
#   #################################


class TableCreate(BinExp):
    def do_run(self, left, table_name, arg, scope):
        db_name = self.find_db_scope()
        return arg.create_table_in_db(db_name, table_name)


class TableDrop(BinExp):
    def do_run(self, db, table_name, arg, scope):
        db_name = self.find_db_scope()
        return arg.drop_table_in_db(db_name, table_name)


class TableList(MonExp):
    def do_run(self, db, arg, scope):
        db_name = self.find_db_scope()
        return arg.list_tables_in_db(db_name)


class DbCreate(MonExp):
    def do_run(self, db_name, arg, scope):
        return arg.create_db(db_name)


class DbDrop(MonExp):
    def do_run(self, db_name, arg, scope):
        return arg.drop_db(db_name)


class DbList(RBase):
    def __init__(self, *args, **kwargs):
        pass

    def run(self, arg, scope):
        return arg.list_dbs()


class TableListTL(RBase):
    def __init__(self, *args, **kwargs):
        pass

    def run(self, arg, scope):
        tables = []
        for db in arg.list_dbs():
            tables += arg.list_tables_in_db(db)

        return tables


#   #################################
#     Index manipulation functions
#   #################################


class IndexCreateByField(BinExp):
    def do_run(self, sequence, field_name, arg, scope):
        index_func = util.getter(field_name)
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()
        multi = self.optargs.get("multi", False)
        return arg.create_index_in_table_in_db(
            current_db, current_table, field_name, index_func, multi=multi
        )


class IndexCreateByFunc(RBase):
    def __init__(self, left, middle, right, optargs=None):
        self.left = left
        self.middle = middle
        self.right = right
        self.optargs = optargs or {}

    def run(self, arg, scope):
        index_name = self.middle.run(arg, scope)
        index_func = self.right
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()
        multi = self.optargs.get("multi", False)
        return arg.create_index_in_table_in_db(
            current_db, current_table, index_name, index_func, multi=multi
        )


class Wait(MonExp):
    def do_run(self, table_or_seq, arg, scope):
        pass


class IndexRename(Ternary):
    def do_run(self, sequence, old_name, new_name, arg, scope):
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        exists = arg.index_exists_in_table_in_db(current_db, current_table, new_name)
        if exists:
            if not self.optargs.get("overwrite", False):
                raise Exception("tried to overwrite existing index!")

        return arg.rename_index_in_table_in_db(
            current_db, current_table, old_name, new_name
        )


class IndexDrop(BinExp):
    def do_run(self, sequence, index_name, arg, scope):
        assert isinstance(self.left, RTable)
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        return arg.drop_index_in_table_in_db(current_db, current_table, index_name)


class IndexList(MonExp):
    def do_run(self, table, arg, scope):
        assert isinstance(self.left, RTable)

        current_db = self.find_db_scope()
        current_table = self.find_table_scope()
        return arg.list_indexes_in_table_in_db(current_db, current_table)


class IndexWaitAll(MonExp):
    def do_run(self, table, arg, scope):
        assert isinstance(self.left, RTable)
        return table


class IndexWaitOne(BinExp):
    def do_run(self, table, index_name, arg, scope):
        assert isinstance(self.left, RTable)
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()
        exists = arg.index_exists_in_table_in_db(current_db, current_table, index_name)
        assert exists
        return table


class Sync(MonExp):
    def do_run(self, table, arg, scope):
        assert isinstance(self.left, RTable)
        return table


#   ####################
#     String functions
#   ####################


class StrUpcase(MonExp):
    def do_run(self, string, arg, scope):
        return string.upper()


class StrDowncase(MonExp):
    def do_run(self, string, arg, scope):
        return string.lower()


class StrSplitDefault(MonExp):
    def do_run(self, string, arg, scope):
        return string.split()


class StrSplitOn(BinExp):
    def do_run(self, string, split_on, arg, scope):
        return util.rql_str_split(string, split_on)


class StrSplitOnLimit(Ternary):
    def do_run(self, string, split_on, limit, arg, scope):
        return util.rql_str_split(string, split_on, limit)


def operators_for_bounds(left_bound, right_bound):
    if left_bound == "closed":
        left_oper = operator.ge
    else:
        left_oper = operator.gt

    if right_bound == "closed":
        right_oper = operator.le
    else:
        right_oper = operator.lt

    return left_oper, right_oper


def safe_compare_arrays(arr1, arr2, comparison_func):
    """Safely compare arrays that may contain infinity values"""
    if not isinstance(arr1, list) or not isinstance(arr2, list):
        return comparison_func(arr1, arr2)

    # Compare element by element
    for i in range(min(len(arr1), len(arr2))):
        val1, val2 = arr1[i], arr2[i]

        # Handle infinity values
        if val1 == float("-inf"):
            if val2 == float("-inf"):
                continue  # Equal, check next element
            else:
                return comparison_func == operator.le or comparison_func == operator.lt
        elif val1 == float("inf"):
            if val2 == float("inf"):
                continue  # Equal, check next element
            else:
                return comparison_func == operator.ge or comparison_func == operator.gt
        elif val2 == float("-inf"):
            return comparison_func == operator.ge or comparison_func == operator.gt
        elif val2 == float("inf"):
            return comparison_func == operator.le or comparison_func == operator.lt
        else:
            # Regular comparison
            if val1 != val2:
                return comparison_func(val1, val2)

    # If all compared elements are equal, compare by length
    return comparison_func(len(arr1), len(arr2))


class Between(Ternary):
    def do_run(self, table, lower_key, upper_key, arg, scope):
        defaults = {"left_bound": "closed", "right_bound": "open", "index": "id"}
        options = util.extend(defaults, self.optargs)

        if options["index"] == "id":
            map_fn = util.getter("id")
        else:
            index_func, _ = self.find_index_func_for_scope(options["index"], arg)

            if isinstance(index_func, RFunc):

                def map_fn(d):
                    return index_func.run([d], scope)

            else:
                map_fn = index_func

        left_test, right_test = operators_for_bounds(
            options["left_bound"], options["right_bound"]
        )
        for document in table:
            doc_val = map_fn(document)
            if safe_compare_arrays(
                doc_val, lower_key, left_test
            ) and safe_compare_arrays(doc_val, upper_key, right_test):
                yield document


class InsertAt(Ternary):
    def do_run(self, sequence, index, value, arg, scope):
        return util.insert_at(value, index, sequence)


class SpliceAt(Ternary):
    def do_run(self, sequence, index, value, arg, scope):
        return util.splice_at(value, index, sequence)


class DeleteAt(BinExp):
    def do_run(self, sequence, index, arg, scope):
        return util.delete_at(index, sequence)


class ChangeAt(Ternary):
    def do_run(self, sequence, index, value, arg, scope):
        return util.change_at(value, index, sequence)


class InnerOuterJoinBase(Ternary):
    def run(self, arg, scope):
        left_seq = self.left.run(arg, scope)
        right_seq = self.middle.run(arg, scope)

        def pred(x, y):
            return self.right.run([x, y], scope)

        return self.do_run(left_seq, right_seq, pred, arg, scope)


class EqJoin(Ternary):
    def do_run(self, left, middle, right, arg, scope):
        # left = left table, middle = field name, right = right table
        # EqJoin assumes joining on primary key ("id") of right table
        return joins.do_eq_join(middle, left, "id", right)


class InnerJoin(InnerOuterJoinBase):
    def do_run(self, left, right, pred, arg, scope):
        return joins.do_inner_join(pred, left, right)


class OuterJoin(InnerOuterJoinBase):
    def do_run(self, left, right, pred, arg, scope):
        return joins.do_outer_join(pred, left, right)


# ############
#   Time
# ############


class Year(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.year


class Month(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.month


class Day(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.day


class Hours(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.hour


class Minutes(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.minute


class Seconds(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.second


class Date(MonExp):
    def do_run(self, dtime, arg, scope):
        return rtime.to_date(dtime)


class TimeOfDay(MonExp):
    def do_run(self, dtime, arg, scope):
        return rtime.time_of_day_seconds(dtime)


class DayOfWeek(MonExp):
    def do_run(self, dtime, arg, scope):
        return dtime.isoweekday()


class Now(RBase):
    def __init__(self, optargs={}):
        self.optargs = optargs

    def run(self, db, scope):
        return rtime.now()


class ToEpochTime(MonExp):
    def do_run(self, dtime, arg, scope):
        return rtime.epoch_time(dtime)


class EpochTime(MonExp):
    """Create a time object from Unix epoch time (seconds since 1970-01-01)"""

    def do_run(self, timestamp, arg, scope):
        return rtime.from_epoch_time(timestamp)


class ISO8601(MonExp):
    def do_run(self, left, arg, scope):
        if not isinstance(left, str):
            left = left.run(arg, scope)
        return dateutil.parser.parse(left)


class Time(MonExp):
    def do_run(self, parts, arg, scope):
        parts = list(parts)
        if len(parts) < 4:
            self.raise_rql_compile_error("Expected between 4 and 7 arguments, got 3")
        return rtime.rql_compatible_time(*parts)


class During(Ternary):
    def do_run(self, to_test, left, right, arg, scope):
        defaults = {"left_bound": "closed", "right_bound": "open"}
        options = util.extend(defaults, self.optargs)
        left_test, right_test = operators_for_bounds(
            options["left_bound"], options["right_bound"]
        )
        return left_test(to_test, left) and right_test(to_test, right)


class StrMatch(BinExp):
    def do_run(self, string, pattern, arg, scope):
        import re

        try:
            match = re.search(pattern, string)
            if match:
                result = {
                    "str": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "groups": [],
                }

                # Add captured groups
                for i, group in enumerate(match.groups()):
                    group_info = {
                        "str": group if group is not None else None,
                        "start": match.start(i + 1) if group is not None else -1,
                        "end": match.end(i + 1) if group is not None else -1,
                    }
                    result["groups"].append(group_info)

                return result
            else:
                return None
        except re.error:
            # Invalid regex pattern
            self.raise_rql_runtime_error(f"Invalid regular expression: {pattern}")
            return None


class Args(RBase):
    pass


class Binary(RBase):
    def __init__(self, data):
        self.data = data

    def run(self, arg, scope):
        if self.data is None:
            return b""
        if hasattr(self.data, "run"):
            result = self.data.run(arg, scope)
        else:
            result = self.data

        # Convert to bytes if it's not already
        if isinstance(result, bytes):
            return result
        elif isinstance(result, str):
            return result.encode("utf-8")
        else:
            return bytes(result)


class ForEach(RBase):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def run(self, arg, scope=None):
        sequence = self.left.run(arg, scope)
        result = []

        for item in sequence:
            # Apply the function to each item
            function_result = self.right.run(item, scope)

            # Flatten the result - if it's a list/sequence, extend; otherwise append
            if isinstance(function_result, (list, tuple)):
                result.extend(function_result)
            else:
                result.append(function_result)

        return result


class RDefault(BinExp):
    def run(self, arg, scope):
        # Default needs to catch errors from the left side and return the right side value
        try:
            left_result = self.left.run(arg, scope)
            if left_result is None:
                return self.right.run(arg, scope)
            return left_result
        except (RqlRuntimeError, ReqlNonExistenceError):
            # If there's an error accessing the left side (e.g., missing field), return default
            return self.right.run(arg, scope)


class RExpr(RBase):
    pass


class Js(RBase):
    pass


class CoerceTo(BinExp):
    def do_run(self, left, right, arg, scope):
        res = self.left.run(arg, scope)
        rname = self.right.run(arg, scope)
        target_type = rname.upper()

        if target_type == "ARRAY":
            if isinstance(res, dict):
                return list(res.items())
            return list(res)
        elif target_type == "STRING":
            return str(res)
        elif target_type == "NUMBER":
            if isinstance(res, str):
                try:
                    # Try int first, then float
                    if "." in res:
                        return float(res)
                    else:
                        return int(res)
                except ValueError:
                    raise ValueError(f"Cannot convert '{res}' to number")
            return res
        elif target_type == "OBJECT":
            if isinstance(res, list):
                # Convert array of pairs to object
                if all(isinstance(item, list) and len(item) == 2 for item in res):
                    return {k: v for k, v in res}
            return res
        return res


class Info(RBase):
    pass


class Http(RBase):
    pass


class RRow(RBase):
    """r.row - Reference to the currently visited document"""

    def run(self, arg, scope):
        # In RethinkDB, r.row refers to the current document being processed
        # This is passed as the 'arg' parameter in function contexts
        return arg


class GetField(BinExp):
    """Get a single field from an object, alternative to bracket notation"""

    def do_run(self, obj, field_name, arg, scope):
        from rethinkdb_mock.db import MockTableData

        if isinstance(obj, MockTableData):
            # If obj is a table, apply get_field to all rows
            return [row.get(field_name) for row in obj.get_rows()]
        elif isinstance(obj, dict):
            if field_name in obj:
                return obj[field_name]
            else:
                # RethinkDB raises an error for missing fields on single documents
                raise ReqlNonExistenceError(f"No attribute `{field_name}` in object")
        else:
            raise ReqlNonExistenceError(f"No attribute `{field_name}` in object")


class Values(MonExp):
    """Return an array containing all of an object's values"""

    def do_run(self, obj, arg, scope):
        if isinstance(obj, dict):
            return list(obj.values())
        else:
            raise TypeError("Cannot call `values` on a non-object")


class RObject(RBase):
    """Creates an object from a list of key-value pairs"""

    def __init__(self, *args, optargs=None):
        self._args = args
        self.optargs = optargs if optargs is not None else {}
        super().__init__(*args)

    def run(self, arg, scope):
        # This function takes arguments in pairs: key1, value1, key2, value2, ...
        if hasattr(self, "_args") and self._args:
            args = [a.run(arg, scope) if hasattr(a, "run") else a for a in self._args]
            if len(args) % 2 != 0:
                raise ValueError(
                    "object() requires an even number of arguments (key-value pairs)"
                )

            result = {}
            for i in range(0, len(args), 2):
                key = args[i]
                value = args[i + 1]
                if not isinstance(key, str):
                    raise TypeError("Object keys must be strings")
                result[key] = value

            return result
        return {}


# Additional date/time functions
class InTimezone(BinExp):
    def do_run(self, dt_val, timezone_str, arg, scope):
        import datetime

        from .rtime import in_timezone

        if not isinstance(dt_val, datetime.datetime):
            raise TypeError("in_timezone() can only be called on datetime objects")

        return in_timezone(dt_val, timezone_str)


class Timezone(MonExp):
    def do_run(self, dt_val, arg, scope):
        import datetime

        from .rtime import get_timezone

        if not isinstance(dt_val, datetime.datetime):
            raise TypeError("timezone() can only be called on datetime objects")

        return get_timezone(dt_val)


class DayOfYear(MonExp):
    def do_run(self, dt_val, arg, scope):
        import datetime

        from .rtime import day_of_year

        if not isinstance(dt_val, datetime.datetime):
            raise TypeError("day_of_year() can only be called on datetime objects")

        return day_of_year(dt_val)


class ToIso8601(MonExp):
    def do_run(self, dt_val, arg, scope):
        import datetime

        from .rtime import to_iso8601

        if not isinstance(dt_val, datetime.datetime):
            raise TypeError("to_iso8601() can only be called on datetime objects")

        return to_iso8601(dt_val)


# Bit shift operations
class BitSal(BinExp):
    """Bit shift left (arithmetic shift left)"""

    def do_run(self, left_val, right_val, arg, scope):
        if not isinstance(left_val, int) or not isinstance(right_val, int):
            raise TypeError("bit_sal can only be applied to integers")

        if right_val < 0:
            raise ValueError("Shift amount must be non-negative")

        return left_val << right_val


class BitSar(BinExp):
    """Bit shift right (arithmetic shift right)"""

    def do_run(self, left_val, right_val, arg, scope):
        if not isinstance(left_val, int) or not isinstance(right_val, int):
            raise TypeError("bit_sar can only be applied to integers")

        if right_val < 0:
            raise ValueError("Shift amount must be non-negative")

        return left_val >> right_val


# JSON conversion functions
class ToJsonString(MonExp):
    def do_run(self, value, arg, scope):
        import json

        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot convert to JSON: {e}")


# Fold aggregation function
class Fold(Ternary):
    def run(self, arg, scope):
        # Handle the sequence and base value normally
        self.set_mock_ref(self.left)
        self.set_mock_ref(self.middle)
        # Don't run the function immediately - we'll call it later
        self.set_mock_ref(self.right)

        sequence = self.left.run(arg, scope)
        base = self.middle.run(arg, scope)
        fold_func = self.right  # Keep the function object, don't run it

        return self.do_run(sequence, base, fold_func, arg, scope)

    def do_run(self, sequence, base, fold_func, arg, scope):
        if not hasattr(sequence, "__iter__"):
            raise TypeError("fold() can only be applied to sequences")

        accumulator = base
        for item in sequence:
            # Call the fold function with accumulator and item
            # The function expects two arguments: accumulator and current item
            fold_result = fold_func.run([accumulator, item], scope)
            accumulator = fold_result

        return accumulator


class IndexStatus(MonExp):
    """Get the status of indexes on a table"""

    def do_run(self, table, arg, scope):
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        # Return status information for all indexes
        indexes = arg.list_indexes_in_table_in_db(current_db, current_table)

        status_list = []
        for index_name in indexes:
            status_list.append(
                {
                    "index": index_name,
                    "ready": True,  # Mock indexes are always ready
                    "function": index_name,  # Simplified representation
                    "multi": False,  # Default to single-value index
                    "progress": 1.0,  # Always 100% complete
                }
            )

        return status_list


class IndexStatusOne(BinExp):
    """Get the status of a specific index on a table"""

    def do_run(self, table, index_name, arg, scope):
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        # Check if index exists
        exists = arg.index_exists_in_table_in_db(current_db, current_table, index_name)
        if not exists:
            raise ReqlNonExistenceError(f"Index `{index_name}` does not exist")

        # Return status for the specific index
        return [
            {
                "index": index_name,
                "ready": True,  # Mock indexes are always ready
                "function": index_name,  # Simplified representation
                "multi": False,  # Default to single-value index
                "progress": 1.0,  # Always 100% complete
            }
        ]


class Config(MonExp):
    """Get configuration information for a table or database"""

    def do_run(self, obj, arg, scope):
        # For mock implementation, return basic config info
        current_table = self.find_table_scope()
        if current_table is not None:
            # Table config
            current_db = self.find_db_scope()
            return {
                "id": f"{current_db}.{current_table}",
                "name": current_table,
                "db": current_db,
                "primary_key": "id",
                "shards": [
                    {"primary_replica": "mock_server", "replicas": ["mock_server"]}
                ],
                "indexes": [],
                "write_acks": "majority",
                "durability": "hard",
            }
        else:
            # Database config
            db_name = self.find_db_scope()
            return {"id": db_name, "name": db_name}
            return {"id": db_name, "name": db_name}


class Status(MonExp):
    """Get status information for a table or database"""

    def do_run(self, obj, arg, scope):
        current_table = self.find_table_scope()
        if current_table is not None:
            # Table status
            current_db = self.find_db_scope()
            return {
                "id": f"{current_db}.{current_table}",
                "name": current_table,
                "db": current_db,
                "status": {
                    "ready_for_outdated_reads": True,
                    "ready_for_reads": True,
                    "ready_for_writes": True,
                    "all_replicas_ready": True,
                },
                "shards": [
                    {
                        "primary_replica": "mock_server",
                        "replicas": [{"server": "mock_server", "state": "ready"}],
                    }
                ],
            }
        else:
            # Database status
            db_name = self.find_db_scope()
            return {
                "id": db_name,
                "name": db_name,
                "status": {
                    "ready_for_outdated_reads": True,
                    "ready_for_reads": True,
                    "ready_for_writes": True,
                    "all_replicas_ready": True,
                },
            }


# Table write hook functions (simplified mock implementations)
class SetWriteHook(BinExp):
    """Set a write hook for a table (mock implementation)"""

    def do_run(self, table, hook_function, arg, scope):
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        # In a real implementation, this would store the hook function
        # For mock, we just return success
        return {
            "created": 1,
            "replaced": 0,
            "unchanged": 0,
            "errors": 0,
            "first_error": None,
            "inserted": 0,
            "deleted": 0,
        }


class GetWriteHook(MonExp):
    """Get the write hook for a table (mock implementation)"""

    def do_run(self, table, arg, scope):
        current_db = self.find_db_scope()
        current_table = self.find_table_scope()

        # For mock implementation, return null (no hook set)
        return None


class Args(RBase):
    """Expand an array into arguments for a function"""

    def __init__(self, array_expr):
        self.array_expr = array_expr

    def run(self, arg, scope):
        # Args is special - it's used to expand an array into function arguments
        # The actual expansion is handled by the calling function (like Add)
        # Here we just return the array values
        if hasattr(self.array_expr, "run"):
            result = self.array_expr.run(arg, scope)
        else:
            result = self.array_expr

        if not isinstance(result, (list, tuple)):
            raise TypeError("r.args() requires an array argument")

        return result

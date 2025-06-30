from pprint import pprint


class NotInScopeErr(Exception):
    def __init__(self, msg):
        print(msg)
        self.msg = msg


class Scope(object):
    def __init__(self, values):
        self.values = values

    def get_sym(self, x):
        result = None
        if x in self.values:
            result = self.values[x]
        elif hasattr(self, "parent"):
            result = self.parent.get_sym(x)
        if result is None:
            msg = f"symbol not defined: {x}"
            raise NotInScopeErr(msg)
        return result

    def push(self, vals):
        scope = Scope(vals)
        scope.parent = self
        return scope

    def get_flattened(self):
        vals = {k: v for k, v in list(self.values.items())}
        if not hasattr(self, "parent"):
            return vals
        parent_vals = self.parent.get_flattened()
        parent_vals.update(vals)
        return parent_vals

    def log(self):
        pprint(self.get_flattened())

    def get_current_row(self):
        """Get the current row/document being processed"""
        if hasattr(self, "current_row"):
            return self.current_row
        elif hasattr(self, "parent"):
            return self.parent.get_current_row()
        else:
            raise NotInScopeErr("No current row available in this context")

    def with_current_row(self, row):
        """Create a new scope with the current row set"""
        new_scope = Scope(self.values)
        new_scope.current_row = row
        if hasattr(self, "parent"):
            new_scope.parent = self.parent
        return new_scope

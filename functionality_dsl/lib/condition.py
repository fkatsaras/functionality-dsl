from typing import List, Any, Optional


class ConditionKeyValuePair:
    """
    Represents a key: value pair in a Dict literal or TermPool options.
    """
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value

    def __repr__(self):
        return f"<KeyValuePair key={self.key!r} value={self.value!r}>"


class ConditionList:
    """
    Represents a list literal in a condition or math expression.
    """
    def __init__(self, elements: List[Any]):
        self.elements = elements

    def __repr__(self):
        return f"<List elements={self.elements!r}>"


class ConditionDict:
    """
    Represents a dictionary literal in a condition.
    """
    def __init__(self, pairs: List[ConditionKeyValuePair]):
        self.pairs = pairs

    def __repr__(self):
        return f"<Dict pairs={self.pairs!r}>"


class Condition:
    """
    Represents a Boolean condition composed of one or more ConditionGroups joined by logical operators.
    """
    def __init__(
        self,
        r1: Any,
        operator: Optional[List[str]] = None,
        r2: Optional[List[Any]] = None,
    ):
        self.r1 = r1
        # operator and r2 lists are parallel: operator[i] joins r1 (or previous group) with r2[i]
        self.operator = operator or []
        self.r2 = r2 or []

    def __repr__(self):
        parts = [repr(self.r1)]
        for op, grp in zip(self.operator, self.r2):
            parts.append(op)
            parts.append(repr(grp))
        return f"<Condition {' '.join(parts)}>"


class ConditionGroup:
    """
    Represents a grouped condition, either a parenthesized Condition or a PrimitiveCondition or MathExpression.
    """
    def __init__(self, r: Any):
        self.r = r

    def __repr__(self):
        return f"<ConditionGroup {self.r!r}>"


class PrimitiveCondition:
    """
    Base class for all primitive condition types.
    """
    pass


class NumericCondition(PrimitiveCondition):
    """
    Represents a numeric comparison between two math expressions.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<NumericCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class StringCondition(PrimitiveCondition):
    """
    Represents a string comparison between attributes or literals.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<StringCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class BoolCondition(PrimitiveCondition):
    """
    Represents a boolean condition between attributes or literals.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<BoolCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class ListCondition(PrimitiveCondition):
    """
    Represents a condition involving list membership or comparison.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<ListCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class DictCondition(PrimitiveCondition):
    """
    Represents a condition involving dictionary membership or comparison.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<DictCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class TimeCondition(PrimitiveCondition):
    """
    Represents a time-based condition between attributes.
    """
    def __init__(self, operand1: Any, operator: str, operand2: Any):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __repr__(self):
        return f"<TimeCondition {self.operand1!r} {self.operator} {self.operand2!r}>"


class TermPool:
    """
    Groups conditions under a named pool.
    """
    def __init__(self, name: str, conditions: List[Condition]):
        self.name = name
        self.conditions = conditions

    def __repr__(self):
        return f"<TermPool name={self.name!r} conditions={self.conditions!r}>"

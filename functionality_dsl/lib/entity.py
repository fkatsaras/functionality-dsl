from typing import List, Optional

from functionality_dsl.lib.datasource import Datasource

class Attribute:
    def __init__(
        self,
        name: str,
        type: str,
        primaryKey: bool = False,
        required: bool = False,
        unique: bool = False,
    ):
        self.name = name
        self.type = type
        self.primaryKey = primaryKey
        self.required = required
        self.unique = unique

    def __repr__(self):
        flags = []
        if self.primaryKey:
            flags.append("primaryKey")
        if self.required:
            flags.append("required")
        if self.unique:
            flags.append("unique")
        flag_str = " ".join(flags)
        return f"<Attribute name={self.name} type={self.type} {flag_str}>"

class Relation:
    def __init__(
        self,
        name: str,
        target: 'Entity',
        multiplicity: Optional[str] = None,
    ):
        self.name = name
        self.target = target
        self.multiplicity = multiplicity

    def __repr__(self):
        mult = f" multiplicity={self.multiplicity}" if self.multiplicity else ""
        return f"<Relation name={self.name} target={self.target.name}{mult}>"

class Entity:
    def __init__(
        self,
        kind: str,
        name: str,
        datasource: Optional['Datasource'] = None,
        description: Optional[str] = None,
        attributes: Optional[List[Attribute]] = None,
        relations: Optional[List[Relation]] = None,
    ):
        self.kind = kind
        self.name = name
        self.datasource = datasource
        self.description = description
        self.attributes = attributes or []
        self.relations = relations or []

    def __repr__(self):
        ds = self.datasource.name if self.datasource else None
        return (
            f"<Entity kind={self.kind} name={self.name} "
            f"datasource={ds} attributes={self.attributes} relations={self.relations}>"
        )
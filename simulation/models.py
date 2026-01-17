"""
Neo4j Models and Utilities for Project Graph
Provides dataclasses for all layers and utility functions for merging into Neo4j.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from neo4j import Session


# ============================================================================
# LAYER 1: People & Teams
# ============================================================================

@dataclass
class Person:
    """Person node in the organizational graph."""
    id: str
    name: str
    email: str
    title: str
    role: str
    seniority: str
    hire_date: str  # ISO format string (YYYY-MM-DD)
    is_manager: bool
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties with proper type conversion."""
        props = asdict(self)
        return props


@dataclass
class Team:
    """Team node in the organizational graph."""
    id: str
    name: str
    focus_area: str
    target_size: int
    created_at: str  # ISO format string (YYYY-MM-DD)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties with proper type conversion."""
        return asdict(self)


@dataclass
class IdentityMapping:
    """Identity mapping node linking external provider identities to Person.
    
    This represents an external identity (GitHub, Jira, etc.) that maps to a Person.
    Multiple IdentityMapping nodes can point to the same Person via MAPS_TO relationships.
    
    Note: The 'person_id' field is NOT part of this dataclass. In batch loading scenarios
    where JSON includes person_id, that field should be extracted separately and used to
    create the MAPS_TO relationship.
    
    Example:
        identity = IdentityMapping(
            id="identity_github_alice",
            provider="GitHub",
            username="alicej",
            email="alice@company.com"
        )
        
        rel = Relationship(
            type="MAPS_TO",
            from_id=identity.id,
            to_id="person_alice",  # This is the person_id
            from_type="IdentityMapping",
            to_type="Person"
        )
        
        merge_identity_mapping(session, identity, relationships=[rel])
    """
    id: str
    provider: str
    username: str
    email: str
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties."""
        return asdict(self)


# ============================================================================
# LAYER 2: Jira Initiatives
# ============================================================================

@dataclass
class Project:
    """Project node representing a collection of initiatives."""
    id: str
    key: str
    name: str
    description: str
    start_date: str  # ISO format string (YYYY-MM-DD)
    end_date: str    # ISO format string (YYYY-MM-DD)
    status: str
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties."""
        return asdict(self)


@dataclass
class Initiative:
    """Initiative node representing a high-level Jira work item.
    
    Note: The 'assignee_id' and 'reporter_id' fields are NOT part of this dataclass.
    They should be extracted from JSON and used to create ASSIGNED_TO and REPORTED_BY
    relationships directly to Person nodes.
    
    Example:
        initiative = Initiative(
            id="initiative_init_1",
            key="INIT-1",
            summary="Platform Modernization",
            ...
        )
        
        # Relationships point directly to Person nodes
        assignee_rel = Relationship(
            type="ASSIGNED_TO",
            from_id=initiative.id,
            to_id="person_alice",  # Person node ID
            from_type="Initiative",
            to_type="Person"
        )
    """
    id: str
    key: str
    summary: str
    description: str
    priority: str
    status: str
    start_date: str   # ISO format string (YYYY-MM-DD)
    due_date: str     # ISO format string (YYYY-MM-DD)
    created_at: str   # ISO format string (YYYY-MM-DD)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties."""
        return asdict(self)


@dataclass
class Epic:
    """Epic node representing a Jira Epic.
    
    Note: The 'assignee_id', 'team_id', and 'initiative_id' fields are NOT part of this dataclass.
    They should be extracted from JSON and used to create relationships:
    - ASSIGNED_TO -> Person
    - TEAM -> Team
    - PART_OF -> Initiative
    
    Example:
        epic = Epic(
            id="epic_plat_1",
            key="PLAT-1",
            summary="Migrate to Kubernetes",
            ...
        )
        
        # Relationships point directly to Person, Team, and Initiative nodes
        assignee_rel = Relationship(
            type="ASSIGNED_TO",
            from_id=epic.id,
            to_id="person_alice",
            from_type="Epic",
            to_type="Person"
        )
    """
    id: str
    key: str
    summary: str
    description: str
    priority: str
    status: str
    start_date: str   # ISO format string (YYYY-MM-DD)
    due_date: str     # ISO format string (YYYY-MM-DD)
    created_at: str   # ISO format string (YYYY-MM-DD)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties."""
        return asdict(self)


# ============================================================================
# RELATIONSHIP DATACLASS
# ============================================================================

@dataclass
class Relationship:
    """Represents a relationship between two nodes."""
    type: str
    from_id: str
    to_id: str
    from_type: str
    to_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# BIDIRECTIONAL RELATIONSHIP MAPPINGS
# ============================================================================

BIDIRECTIONAL_RELATIONSHIPS = {
    # Layer 1
    "MEMBER_OF": "MEMBER_OF",       # Person ↔ Team
    "REPORTS_TO": "MANAGES",        # Person → Person (reports to) / Person ← Person (manages)
    "MANAGES": "MANAGED_BY",        # Person → Team (manages) / Team ← Person (managed by)
    "MAPS_TO": "MAPS_TO",           # IdentityMapping ↔ Person
    
    # Layer 2
    "PART_OF": "CONTAINS",          # Initiative → Project / Project ← Initiative
    "ASSIGNED_TO": "ASSIGNED_TO",   # Initiative ↔ Person
    "REPORTED_BY": "REPORTED_BY",   # Initiative ↔ Person
    
    # Layer 3
    # "PART_OF": "CONTAINS",        # Epic → Initiative / Initiative ← Epic (already defined in Layer 2)
    # "ASSIGNED_TO": "ASSIGNED_TO", # Epic ↔ Person (already defined in Layer 2)
    "TEAM": "TEAM",                 # Epic ↔ Team
}


# ============================================================================
# CONSTRAINT MANAGEMENT
# ============================================================================

def create_constraints(session: Session, layers: Optional[List[int]] = None) -> None:
    """Create uniqueness constraints for node types.
    
    Args:
        session: Neo4j session
        layers: Optional list of layer numbers to create constraints for.
                If None, creates constraints for all layers.
    """
    all_constraints = {
        1: [
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:IdentityMapping) REQUIRE i.id IS UNIQUE"
        ],
        2: [
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT initiative_id IF NOT EXISTS FOR (i:Initiative) REQUIRE i.id IS UNIQUE"
        ],
        3: [
            "CREATE CONSTRAINT epic_id IF NOT EXISTS FOR (e:Epic) REQUIRE e.id IS UNIQUE"
        ]
    }
    
    # Determine which constraints to create
    if layers is None:
        constraints = []
        for layer_constraints in all_constraints.values():
            constraints.extend(layer_constraints)
    else:
        constraints = []
        for layer in layers:
            if layer in all_constraints:
                constraints.extend(all_constraints[layer])
    
    for constraint in constraints:
        try:
            session.run(constraint)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise


# ============================================================================
# LAYER 1 MERGE FUNCTIONS
# ============================================================================

def merge_person(session: Session, person: Person, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge a Person node into Neo4j.
    
    Args:
        session: Neo4j session
        person: Person dataclass instance
        relationships: Optional list of relationships to create
    """
    props = person.to_neo4j_properties()
    
    # MERGE the Person node
    query = """
    MERGE (p:Person {id: $id})
    SET p.name = $name,
        p.email = $email,
        p.title = $title,
        p.role = $role,
        p.seniority = $seniority,
        p.hire_date = date($hire_date),
        p.is_manager = $is_manager
    RETURN p
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


def merge_team(session: Session, team: Team, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge a Team node into Neo4j.
    
    Args:
        session: Neo4j session
        team: Team dataclass instance
        relationships: Optional list of relationships to create
    """
    props = team.to_neo4j_properties()
    
    # MERGE the Team node
    query = """
    MERGE (t:Team {id: $id})
    SET t.name = $name,
        t.focus_area = $focus_area,
        t.target_size = $target_size,
        t.created_at = date($created_at)
    RETURN t
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


def merge_identity_mapping(session: Session, identity: IdentityMapping, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge an IdentityMapping node into Neo4j.
    
    Args:
        session: Neo4j session
        identity: IdentityMapping dataclass instance
        relationships: Optional list of relationships to create
    """
    props = identity.to_neo4j_properties()
    
    # MERGE the IdentityMapping node
    query = """
    MERGE (i:IdentityMapping {id: $id})
    SET i.provider = $provider,
        i.username = $username,
        i.email = $email
    RETURN i
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


# ============================================================================
# LAYER 2 MERGE FUNCTIONS
# ============================================================================

def merge_project(session: Session, project: Project, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge a Project node into Neo4j.
    
    Args:
        session: Neo4j session
        project: Project dataclass instance
        relationships: Optional list of relationships to create
    """
    props = project.to_neo4j_properties()
    
    # MERGE the Project node
    query = """
    MERGE (p:Project {id: $id})
    SET p.key = $key,
        p.name = $name,
        p.description = $description,
        p.start_date = date($start_date),
        p.end_date = date($end_date),
        p.status = $status
    RETURN p
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


def merge_initiative(session: Session, initiative: Initiative, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge an Initiative node into Neo4j.
    
    Args:
        session: Neo4j session
        initiative: Initiative dataclass instance
        relationships: Optional list of relationships to create
    """
    props = initiative.to_neo4j_properties()
    
    # MERGE the Initiative node
    query = """
    MERGE (i:Initiative {id: $id})
    SET i.key = $key,
        i.summary = $summary,
        i.description = $description,
        i.priority = $priority,
        i.status = $status,
        i.start_date = date($start_date),
        i.due_date = date($due_date),
        i.created_at = date($created_at)
    RETURN i
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


def merge_epic(session: Session, epic: Epic, relationships: Optional[List[Relationship]] = None) -> None:
    """
    Merge an Epic node into Neo4j.
    
    Args:
        session: Neo4j session
        epic: Epic dataclass instance
        relationships: Optional list of relationships to create
    """
    props = epic.to_neo4j_properties()
    
    # MERGE the Epic node
    query = """
    MERGE (e:Epic {id: $id})
    SET e.key = $key,
        e.summary = $summary,
        e.description = $description,
        e.priority = $priority,
        e.status = $status,
        e.start_date = date($start_date),
        e.due_date = date($due_date),
        e.created_at = date($created_at)
    RETURN e
    """
    
    session.run(query, **props)
    
    # Create relationships if provided
    if relationships:
        for rel in relationships:
            merge_relationship(session, rel)


# ============================================================================
# GENERIC RELATIONSHIP MERGE
# ============================================================================

def merge_relationship(session: Session, relationship: Relationship) -> None:
    """
    Merge a relationship between two nodes, creating nodes if they don't exist.
    Automatically creates bidirectional relationships where applicable.
    
    Args:
        session: Neo4j session
        relationship: Relationship dataclass instance
    """
    rel_type = relationship.type
    from_id = relationship.from_id
    to_id = relationship.to_id
    from_type = relationship.from_type
    to_type = relationship.to_type
    props = relationship.properties
    
    # Build property string for Cypher
    props_str = ""
    if props:
        props_items = [f"{k}: ${k}" for k in props.keys()]
        props_str = "{" + ", ".join(props_items) + "}"
    
    # Create the forward relationship
    forward_query = f"""
    MERGE (from:{from_type} {{id: $from_id}})
    MERGE (to:{to_type} {{id: $to_id}})
    MERGE (from)-[r:{rel_type} {props_str}]->(to)
    RETURN r
    """
    
    params = {
        "from_id": from_id,
        "to_id": to_id,
        **props
    }
    
    session.run(forward_query, **params)
    
    # Create the bidirectional relationship if applicable
    if rel_type in BIDIRECTIONAL_RELATIONSHIPS:
        reverse_type = BIDIRECTIONAL_RELATIONSHIPS[rel_type]
        
        # Special case: Symmetric relationships (same type both ways)
        if rel_type == reverse_type:
            reverse_query = f"""
            MERGE (from:{to_type} {{id: $to_id}})
            MERGE (to:{from_type} {{id: $from_id}})
            MERGE (from)-[r:{reverse_type} {props_str}]->(to)
            RETURN r
            """
        else:
            # Asymmetric bidirectional (REPORTS_TO → MANAGES, etc.)
            reverse_query = f"""
            MERGE (from:{to_type} {{id: $to_id}})
            MERGE (to:{from_type} {{id: $from_id}})
            MERGE (from)-[r:{reverse_type} {props_str}]->(to)
            RETURN r
            """
        
        session.run(reverse_query, **params)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================



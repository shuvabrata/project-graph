"""
Layer 5 Neo4j Loader: Git Repositories
Loads repository nodes and COLLABORATOR relationships into Neo4j.
"""

import json
import os
from neo4j import GraphDatabase
from typing import Dict, Any

# Neo4j connection details
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')


def load_data_file() -> Dict[str, Any]:
    """Load the generated Layer 5 data."""
    with open('../data/layer5_repositories.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_repository_nodes(session, repositories: list):
    """Create Repository nodes in Neo4j."""
    query = """
    UNWIND $repositories as repo
    CREATE (r:Repository {
        id: repo.id,
        name: repo.name,
        full_name: repo.full_name,
        url: repo.url,
        language: repo.language,
        is_private: repo.is_private,
        description: repo.description,
        topics: repo.topics,
        created_at: date(repo.created_at)
    })
    """
    result = session.run(query, repositories=repositories)
    return result.consume().counters.nodes_created

def create_collaborator_relationships(session, relationships: list):
    """Create COLLABORATOR relationships in Neo4j (bidirectional)."""
    # Extended query with optional properties and bidirectional relationships
    query = """
    UNWIND $relationships as rel
    MATCH (from {id: rel.from_id})
    MATCH (to:Repository {id: rel.to_id})
    CREATE (from)-[c:COLLABORATOR]->(to)
    CREATE (to)-[r:COLLABORATOR]->(from)
    SET c.permission = rel.properties.permission,
        c.granted_at = date(rel.properties.granted_at),
        r.permission = rel.properties.permission,
        r.granted_at = date(rel.properties.granted_at)
    WITH c, r, rel
    FOREACH (_ IN CASE WHEN rel.properties.role IS NOT NULL THEN [1] ELSE [] END |
        SET c.role = rel.properties.role,
            r.role = rel.properties.role
    )
    FOREACH (_ IN CASE WHEN rel.properties.reason IS NOT NULL THEN [1] ELSE [] END |
        SET c.reason = rel.properties.reason,
            r.reason = rel.properties.reason
    )
    """
    
    result = session.run(query, relationships=relationships)
    return result.consume().counters.relationships_created

def run_validation_queries(session):
    """Run validation queries to verify the data."""
    print("\n" + "=" * 60)
    print("VALIDATION QUERIES")
    print("=" * 60)
    
    # 1. Repository count
    result = session.run("MATCH (r:Repository) RETURN count(r) as count")
    count = result.single()['count']
    print(f"\n1. Total Repositories: {count}")
    
    # 2. Repository collaborators by team (WRITE access)
    print("\n2. Repository WRITE Access by Team:")
    result = session.run("""
        MATCH (t:Team)-[c:COLLABORATOR]->(r:Repository)
        WHERE c.permission = 'WRITE'
        RETURN t.name as team, collect(r.name) as repositories
        ORDER BY team
    """)
    for record in result:
        print(f"   {record['team']}: {', '.join(record['repositories'])}")
    
    # 3. Repository maintainers (individuals with WRITE access)
    print("\n3. Repository Maintainers (Individual WRITE Access):")
    result = session.run("""
        MATCH (p:Person)-[c:COLLABORATOR]->(r:Repository)
        WHERE c.permission = 'WRITE'
        RETURN r.name as repository, 
               collect(p.name) as maintainers
        ORDER BY repository
    """)
    for record in result:
        print(f"   {record['repository']}: {', '.join(record['maintainers'])}")
    
    # 4. Cross-team access (teams with READ permission)
    print("\n4. Cross-Team READ Access:")
    result = session.run("""
        MATCH (t:Team)-[c:COLLABORATOR]->(r:Repository)
        WHERE c.permission = 'READ'
        RETURN r.name as repository, 
               collect(t.name) as teams_with_read_access
        ORDER BY repository
    """)
    for record in result:
        if record['teams_with_read_access']:
            print(f"   {record['repository']}: {', '.join(record['teams_with_read_access'])}")
    
    # 5. Permission summary per repository
    print("\n5. Permission Summary per Repository:")
    result = session.run("""
        MATCH (r:Repository)<-[c:COLLABORATOR]-(collaborator)
        RETURN r.name as repository,
               sum(CASE WHEN c.permission = 'WRITE' THEN 1 ELSE 0 END) as write_access,
               sum(CASE WHEN c.permission = 'READ' THEN 1 ELSE 0 END) as read_access,
               count(collaborator) as total_collaborators
        ORDER BY repository
    """)
    for record in result:
        print(f"   {record['repository']}: "
              f"WRITE={record['write_access']}, "
              f"READ={record['read_access']}, "
              f"Total={record['total_collaborators']}")
    
    # 6. People collaborating across multiple repos
    print("\n6. People Collaborating Across Multiple Repos:")
    result = session.run("""
        MATCH (p:Person)-[c:COLLABORATOR]->(r:Repository)
        WITH p, c.permission as perm, collect(r.name) as repos
        WHERE size(repos) > 1
        RETURN p.name, perm, repos, size(repos) as repo_count
        ORDER BY repo_count DESC, perm DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   {record['p.name']} ({record['perm']}): "
              f"{record['repo_count']} repos - {', '.join(record['repos'][:3])}{'...' if len(record['repos']) > 3 else ''}")
    
    # 7. Repos without WRITE collaborators (should be none)
    print("\n7. Repos Without WRITE Access (should be empty):")
    result = session.run("""
        MATCH (r:Repository)
        WHERE NOT exists((r)<-[:COLLABORATOR {permission: 'WRITE'}]-())
        RETURN r.name
    """)
    orphans = [record['r.name'] for record in result]
    if orphans:
        print(f"   ⚠️  Found repos without WRITE access: {', '.join(orphans)}")
    else:
        print("   ✓ All repositories have WRITE access")

def main():
    print("=" * 60)
    print("Layer 5: Loading Git Repositories into Neo4j")
    print("=" * 60)
    
    # Load data
    print("\nLoading data file...")
    data = load_data_file()
    
    print(f"✓ Loaded {len(data['nodes']['repositories'])} repositories")
    print(f"✓ Loaded {len(data['relationships'])} relationships")
    
    # Connect to Neo4j
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Create constraint for Repository
            print("\nCreating uniqueness constraint for Repository.id...")
            try:
                session.run("CREATE CONSTRAINT repository_id IF NOT EXISTS FOR (r:Repository) REQUIRE r.id IS UNIQUE")
                print("✓ Constraint created")
            except Exception as e:
                print(f"✓ Constraint already exists or created: {str(e)}")
            
            # Create Repository nodes
            print("\nCreating Repository nodes...")
            nodes_created = create_repository_nodes(session, data['nodes']['repositories'])
            print(f"✓ Created {nodes_created} Repository nodes")
            
            # Create COLLABORATOR relationships
            print("\nCreating COLLABORATOR relationships...")
            rels_created = create_collaborator_relationships(session, data['relationships'])
            print(f"✓ Created {rels_created} COLLABORATOR relationships")
            
            # Run validation queries
            run_validation_queries(session)
            
        print("\n" + "=" * 60)
        print("✓ Layer 5 loaded successfully!")
        print("=" * 60)
        print("\nYou can now explore the data in Neo4j Browser:")
        print("  http://localhost:7474")
        print("\nSample query to try:")
        print("  MATCH (t:Team)-[c:COLLABORATOR {permission:'WRITE'}]->(r:Repository)")
        print("  RETURN t.name, r.name, r.language")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()

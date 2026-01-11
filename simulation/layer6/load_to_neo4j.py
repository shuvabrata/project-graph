"""
Layer 6 Neo4j Loader: Git Branches
Loads branch nodes and BRANCH_OF relationships into Neo4j.
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
    """Load the generated Layer 6 data."""
    with open('../data/layer6_branches.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_branch_nodes(session, branches: list):
    """Create Branch nodes in Neo4j."""
    query = """
    UNWIND $branches as branch
    CREATE (b:Branch {
        id: branch.id,
        name: branch.name,
        is_default: branch.is_default,
        is_protected: branch.is_protected,
        is_deleted: branch.is_deleted,
        last_commit_sha: branch.last_commit_sha,
        last_commit_timestamp: datetime(branch.last_commit_timestamp),
        created_at: datetime(branch.created_at)
    })
    """
    result = session.run(query, branches=branches)
    return result.consume().counters.nodes_created

def create_branch_of_relationships(session, relationships: list):
    """Create BRANCH_OF relationships in Neo4j."""
    query = """
    UNWIND $relationships as rel
    MATCH (b:Branch {id: rel.from_id})
    MATCH (r:Repository {id: rel.to_id})
    CREATE (b)-[:BRANCH_OF]->(r)
    """
    result = session.run(query, relationships=relationships)
    return result.consume().counters.relationships_created

def run_validation_queries(session):
    """Run validation queries to verify the data."""
    print("\n" + "=" * 60)
    print("VALIDATION QUERIES")
    print("=" * 60)
    
    # 1. Total branches
    result = session.run("MATCH (b:Branch) RETURN count(b) as count")
    count = result.single()['count']
    print(f"\n1. Total Branches: {count}")
    
    # 2. Branches per repository
    print("\n2. Total Branches per Repository:")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        RETURN r.name, 
               count(b) as total_branches,
               sum(CASE WHEN b.is_default THEN 1 ELSE 0 END) as default_branches,
               sum(CASE WHEN b.is_deleted THEN 1 ELSE 0 END) as deleted_branches
        ORDER BY total_branches DESC
    """)
    for record in result:
        print(f"   {record['r.name']}: {record['total_branches']} total "
              f"(default: {record['default_branches']}, deleted: {record['deleted_branches']})")
    
    # 3. Active branches (non-default, not deleted)
    print("\n3. Active Branches per Repository:")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        WHERE b.is_default = false AND NOT b.is_deleted
        RETURN r.name, count(b) as active_branches
        ORDER BY active_branches DESC
    """)
    for record in result:
        print(f"   {record['r.name']}: {record['active_branches']} active branches")
    
    # 4. Stale branches (> 30 days old)
    print("\n4. Stale Branches (last commit > 30 days ago):")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        WHERE b.last_commit_timestamp < datetime() - duration({days: 30})
          AND b.is_default = false
          AND NOT b.is_deleted
        RETURN b.name, r.name as repo, b.last_commit_timestamp,
               duration.between(b.last_commit_timestamp, datetime()).days as days_old
        ORDER BY days_old DESC
        LIMIT 10
    """)
    stale_count = 0
    for record in result:
        print(f"   {record['b.name']} ({record['repo']}): {record['days_old']} days old")
        stale_count += 1
    if stale_count == 0:
        print("   (None found)")
    
    # 5. Branches linked to Jira by naming convention
    print("\n5. Branches Linked to Jira (by naming pattern):")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        WHERE b.name =~ '.*/(PLAT|PORT|DATA)-[0-9]+.*'
        WITH b, r, 
             [x in split(b.name, '/') WHERE x =~ '(PLAT|PORT|DATA)-[0-9]+'][0] as jira_key
        RETURN r.name, count(b) as branch_count, collect(DISTINCT jira_key) as jira_keys
        ORDER BY branch_count DESC
    """)
    for record in result:
        print(f"   {record['r.name']}: {record['branch_count']} branches -> {', '.join(record['jira_keys'])}")
    
    # 6. Protected branches
    print("\n6. Protected Branches:")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        WHERE b.is_protected = true
        RETURN r.name, collect(b.name) as protected_branches
        ORDER BY r.name
    """)
    for record in result:
        print(f"   {record['r.name']}: {', '.join(record['protected_branches'])}")
    
    # 7. Deleted branches summary
    print("\n7. Deleted Branches Summary:")
    result = session.run("""
        MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
        WHERE b.is_deleted = true
        RETURN r.name, count(b) as deleted_count
        ORDER BY deleted_count DESC
    """)
    for record in result:
        print(f"   {record['r.name']}: {record['deleted_count']} deleted branches")

def main():
    print("=" * 60)
    print("Layer 6: Loading Git Branches into Neo4j")
    print("=" * 60)
    
    # Load data
    print("\nLoading data file...")
    data = load_data_file()
    
    print(f"✓ Loaded {len(data['nodes']['branches'])} branches")
    print(f"✓ Loaded {len(data['relationships'])} relationships")
    
    # Connect to Neo4j
    print(f"\nConnecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Create constraint for Branch
            print("\nCreating uniqueness constraint for Branch.id...")
            try:
                session.run("CREATE CONSTRAINT branch_id IF NOT EXISTS FOR (b:Branch) REQUIRE b.id IS UNIQUE")
                print("✓ Constraint created")
            except Exception as e:
                print(f"✓ Constraint already exists or created: {str(e)}")
            
            # Create Branch nodes
            print("\nCreating Branch nodes...")
            nodes_created = create_branch_nodes(session, data['nodes']['branches'])
            print(f"✓ Created {nodes_created} Branch nodes")
            
            # Create BRANCH_OF relationships
            print("\nCreating BRANCH_OF relationships...")
            rels_created = create_branch_of_relationships(session, data['relationships'])
            print(f"✓ Created {rels_created} BRANCH_OF relationships")
            
            # Run validation queries
            run_validation_queries(session)
            
        print("\n" + "=" * 60)
        print("✓ Layer 6 loaded successfully!")
        print("=" * 60)
        print("\nYou can now explore the data in Neo4j Browser:")
        print("  http://localhost:7474")
        print("\nSample query to try:")
        print("  MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)")
        print("  WHERE NOT b.is_default AND NOT b.is_deleted")
        print("  RETURN r.name, b.name, b.last_commit_timestamp")
        print("  ORDER BY b.last_commit_timestamp DESC")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()

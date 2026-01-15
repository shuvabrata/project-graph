"""
Layer 3 Neo4j Loader: Load Jira Epics into Neo4j
Loads Epic nodes and creates relationships to existing Initiative, Person, and Team nodes.
DOES NOT clear existing data - this is an incremental load.
"""

import json
import os
import sys
import traceback
from neo4j import GraphDatabase

class Layer3Loader:
    def __init__(self, uri: str, user: str, password: str):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    def create_constraints(self):
        """Create uniqueness constraints for node IDs."""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT epic_id IF NOT EXISTS FOR (e:Epic) REQUIRE e.id IS UNIQUE"
            ]
            
            print("\nCreating constraints...")
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"   ✓ {constraint.split('(')[1].split(')')[0]}")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"   - {constraint.split('(')[1].split(')')[0]} (already exists)")
                    else:
                        raise
    
    def verify_layer1_data(self):
        """Verify that Layer 1 data exists in the database."""
        with self.driver.session() as session:
            print("\nVerifying Layer 1 data...")
            
            # Check for people
            result = session.run("MATCH (p:Person) RETURN count(p) as count")
            person_count = result.single()['count']
            
            if person_count == 0:
                raise Exception("No Person nodes found! Please load Layer 1 first.")
            
            print(f"   ✓ Found {person_count} Person nodes")
            
            # Check for teams
            result = session.run("MATCH (t:Team) RETURN count(t) as count")
            team_count = result.single()['count']
            print(f"   ✓ Found {team_count} Team nodes")
    
    def verify_layer2_data(self):
        """Verify that Layer 2 data exists in the database."""
        with self.driver.session() as session:
            print("\nVerifying Layer 2 data...")
            
            # Check for initiatives
            result = session.run("MATCH (i:Initiative) RETURN count(i) as count")
            initiative_count = result.single()['count']
            
            if initiative_count == 0:
                raise Exception("No Initiative nodes found! Please load Layer 2 first.")
            
            print(f"   ✓ Found {initiative_count} Initiative nodes")
    
    def load_epics(self, epics: list):
        """Load Epic nodes into Neo4j."""
        with self.driver.session() as session:
            print(f"\nLoading {len(epics)} epics...")
            
            for epic in epics:
                query = """
                CREATE (e:Epic {
                    id: $id,
                    key: $key,
                    summary: $summary,
                    description: $description,
                    priority: $priority,
                    status: $status,
                    start_date: date($start_date),
                    due_date: date($due_date),
                    created_at: date($created_at)
                })
                """
                
                # Remove relationship IDs from params as they're not properties
                params = {k: v for k, v in epic.items() 
                         if k not in ['initiative_id', 'assignee_id', 'team_id']}
                
                result = session.run(query, **params)
                summary = result.consume()
                print(f"   ✓ Created {epic['key']}: {epic['summary']}")
    
    def load_relationships(self, relationships: list):
        """Load all relationships into Neo4j."""
        with self.driver.session() as session:
            print(f"\nLoading {len(relationships)} relationships...")
            
            # Group by relationship type for better reporting
            rel_counts = {}
            
            for rel in relationships:
                rel_type = rel['type']
                if rel_type not in rel_counts:
                    rel_counts[rel_type] = 0
                
                # Create relationship based on type (with bidirectional relationships)
                if rel_type == "PART_OF":
                    query = """
                    MATCH (e:Epic {id: $from_id})
                    MATCH (i:Initiative {id: $to_id})
                    CREATE (e)-[:PART_OF]->(i)
                    CREATE (i)-[:CONTAINS]->(e)
                    """
                elif rel_type == "ASSIGNED_TO":
                    query = """
                    MATCH (e:Epic {id: $from_id})
                    MATCH (p:Person {id: $to_id})
                    CREATE (e)-[:ASSIGNED_TO]->(p)
                    CREATE (p)-[:ASSIGNED_TO]->(e)
                    """
                elif rel_type == "TEAM":
                    query = """
                    MATCH (e:Epic {id: $from_id})
                    MATCH (t:Team {id: $to_id})
                    CREATE (e)-[:TEAM]->(t)
                    CREATE (t)-[:TEAM]->(e)
                    """
                else:
                    print(f"   ⚠️  Unknown relationship type: {rel_type}")
                    continue
                
                result = session.run(query, from_id=rel['from_id'], to_id=rel['to_id'])
                summary = result.consume()
                rel_counts[rel_type] += summary.counters.relationships_created
            
            # Report results
            for rel_type, count in rel_counts.items():
                print(f"   ✓ {rel_type}: {count}")
    
    def run_validation_queries(self):
        """Run validation queries from the simulation plan."""
        print("\n" + "=" * 60)
        print("VALIDATION QUERIES")
        print("=" * 60)
        
        with self.driver.session() as session:
            # Query 1: Epics by initiative
            print("\n1. Epics by initiative:")
            query1 = """
            MATCH (e:Epic)-[:PART_OF]->(i:Initiative)
            RETURN i.key, i.summary, collect(e.key) as epics
            ORDER BY i.key
            """
            result = session.run(query1)
            for record in result:
                print(f"   {record['i.key']}: {record['i.summary']}")
                print(f"      Epics: {', '.join(record['epics'])}")
            
            # Query 2: Epic ownership distribution
            print("\n2. Epic ownership distribution:")
            query2 = """
            MATCH (e:Epic)-[:ASSIGNED_TO]->(p:Person)
            RETURN p.name, p.role, p.title, count(e) as epic_count
            ORDER BY epic_count DESC, p.name
            """
            result = session.run(query2)
            for record in result:
                print(f"   {record['p.name']} ({record['p.title']}): {record['epic_count']} epic(s)")
            
            # Query 3: Epics by team
            print("\n3. Epics by team:")
            query3 = """
            MATCH (e:Epic)-[:TEAM]->(t:Team)
            RETURN t.name, collect(e.key) as epics
            ORDER BY t.name
            """
            result = session.run(query3)
            for record in result:
                print(f"   {record['t.name']}: {', '.join(record['epics'])}")
            
            # Query 4: Cross-team epics
            print("\n4. Cross-team epics (should be none with current model):")
            query4 = """
            MATCH (e:Epic)-[:TEAM]->(t:Team)
            WITH e, count(t) as team_count
            WHERE team_count > 1
            RETURN e.key, e.summary, team_count
            """
            result = session.run(query4)
            records = list(result)
            if not records:
                print("   ✓ No cross-team epics (as expected)")
            else:
                for record in records:
                    print(f"   {record['e.key']}: {record['e.summary']} ({record['team_count']} teams)")
            
            # Node counts
            print("\n5. Total node counts:")
            query5 = """
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY label
            """
            result = session.run(query5)
            for record in result:
                print(f"   {record['label']:20} {record['count']:3}")

def main():
    """Main loader function."""
    print("=" * 60)
    print("Layer 3 Neo4j Loader - Incremental Load")
    print("=" * 60)
    
    # Read environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    
    # Read data file
    data_path = "../data/layer3_epics.json"
    print(f"\nReading data from {data_path}...")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("   ✓ Data loaded successfully")
    except FileNotFoundError:
        print(f"   ✗ Error: {data_path} not found!")
        print("   Please run generate_data.py first.")
        sys.exit(1)
    
    # Initialize loader
    print(f"\nConnecting to Neo4j at {neo4j_uri}...")
    loader = Layer3Loader(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # Verify Layer 1 and Layer 2 data exists
        loader.verify_layer1_data()
        loader.verify_layer2_data()
        
        # Create constraints
        loader.create_constraints()
        
        # Load nodes
        loader.load_epics(data['nodes']['epics'])
        
        # Load relationships
        loader.load_relationships(data['relationships'])
        
        # Run validation
        loader.run_validation_queries()
        
        print("\n" + "=" * 60)
        print("✓ Layer 3 loaded successfully!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Open Neo4j Browser at http://localhost:7474")
        print("2. Run queries to explore epics and their relationships")
        print("3. Proceed to Layer 4 (Jira Stories & Bugs)")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        loader.close()

if __name__ == "__main__":
    main()

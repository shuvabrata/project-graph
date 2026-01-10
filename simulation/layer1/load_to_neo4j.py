"""
Layer 1 Neo4j Loader: Load People & Teams data into Neo4j
Reads the generated JSON and creates nodes and relationships in Neo4j.
"""

import json
import os
import sys
import traceback

from neo4j import GraphDatabase

class Layer1Loader:
    def __init__(self, uri: str, user: str, password: str):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        """Close the driver connection."""
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution!)."""
        with self.driver.session() as session:
            print("⚠️  Clearing database...")
            session.run("MATCH (n) DETACH DELETE n")
            print("   ✓ Database cleared")
    
    def create_constraints(self):
        """Create uniqueness constraints for node IDs."""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:IdentityMapping) REQUIRE i.id IS UNIQUE"
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
    
    def load_people(self, people: list):
        """Load Person nodes into Neo4j."""
        with self.driver.session() as session:
            print(f"\nLoading {len(people)} people...")
            
            query = """
            UNWIND $people AS person
            CREATE (p:Person {
                id: person.id,
                name: person.name,
                email: person.email,
                title: person.title,
                role: person.role,
                seniority: person.seniority,
                hire_date: date(person.hire_date),
                is_manager: person.is_manager
            })
            """
            
            result = session.run(query, people=people)
            summary = result.consume()
            print(f"   ✓ Created {summary.counters.nodes_created} Person nodes")
    
    def load_teams(self, teams: list):
        """Load Team nodes into Neo4j."""
        with self.driver.session() as session:
            print(f"\nLoading {len(teams)} teams...")
            
            query = """
            UNWIND $teams AS team
            CREATE (t:Team {
                id: team.id,
                name: team.name,
                focus_area: team.focus_area,
                target_size: team.target_size,
                created_at: date(team.created_at)
            })
            """
            
            result = session.run(query, teams=teams)
            summary = result.consume()
            print(f"   ✓ Created {summary.counters.nodes_created} Team nodes")
    
    def load_identity_mappings(self, mappings: list):
        """Load IdentityMapping nodes into Neo4j."""
        with self.driver.session() as session:
            print(f"\nLoading {len(mappings)} identity mappings...")
            
            query = """
            UNWIND $mappings AS mapping
            CREATE (i:IdentityMapping {
                id: mapping.id,
                provider: mapping.provider,
                username: mapping.username,
                email: mapping.email
            })
            """
            
            result = session.run(query, mappings=mappings)
            summary = result.consume()
            print(f"   ✓ Created {summary.counters.nodes_created} IdentityMapping nodes")
    
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
                
                # Create relationship based on type
                if rel_type == "MEMBER_OF":
                    query = """
                    MATCH (p:Person {id: $from_id})
                    MATCH (t:Team {id: $to_id})
                    CREATE (p)-[:MEMBER_OF]->(t)
                    """
                elif rel_type == "REPORTS_TO":
                    query = """
                    MATCH (p1:Person {id: $from_id})
                    MATCH (p2:Person {id: $to_id})
                    CREATE (p1)-[:REPORTS_TO]->(p2)
                    """
                elif rel_type == "MANAGES":
                    query = """
                    MATCH (p:Person {id: $from_id})
                    MATCH (t:Team {id: $to_id})
                    CREATE (p)-[:MANAGES]->(t)
                    """
                elif rel_type == "MAPS_TO":
                    query = """
                    MATCH (i:IdentityMapping {id: $from_id})
                    MATCH (p:Person {id: $to_id})
                    CREATE (i)-[:MAPS_TO]->(p)
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
            # Query 1: Count people by role and seniority
            print("\n1. People by role and seniority:")
            query1 = """
            MATCH (p:Person)
            RETURN p.role as role, p.seniority as seniority, count(*) as count
            ORDER BY role, seniority
            """
            result = session.run(query1)
            for record in result:
                print(f"   {record['role']:20} {record['seniority']:10} {record['count']:3}")
            
            # Query 2: Org hierarchy (sample)
            print("\n2. Org hierarchy (sample - first 10):")
            query2 = """
            MATCH (p:Person)-[:REPORTS_TO]->(m:Person)
            RETURN p.name, m.name as manager, p.title
            LIMIT 10
            """
            result = session.run(query2)
            for record in result:
                print(f"   {record['p.name']:20} → {record['manager']:20} ({record['p.title']})")
            
            # Query 3: Team sizes
            print("\n3. Team sizes:")
            query3 = """
            MATCH (t:Team)<-[:MEMBER_OF]-(p:Person)
            RETURN t.name, count(p) as team_size
            ORDER BY team_size DESC
            """
            result = session.run(query3)
            for record in result:
                print(f"   {record['t.name']:20} {record['team_size']:3} members")
            
            # Additional validation: Managers
            print("\n4. Managers and their teams:")
            query4 = """
            MATCH (m:Person)-[:MANAGES]->(t:Team)
            RETURN m.name, t.name as team
            """
            result = session.run(query4)
            for record in result:
                print(f"   {record['m.name']:20} → {record['team']}")
            
            # Additional validation: Identity mappings
            print("\n5. Identity mapping providers:")
            query5 = """
            MATCH (i:IdentityMapping)
            RETURN i.provider, count(*) as count
            """
            result = session.run(query5)
            for record in result:
                print(f"   {record['i.provider']:10} {record['count']:3} mappings")

def main():
    """Main loader function."""
    print("=" * 60)
    print("Layer 1 Neo4j Loader")
    print("=" * 60)
    
    # Read environment variables
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    
    # Read data file
    data_path = "../data/layer1_people_teams.json"
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
    loader = Layer1Loader(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # Ask for confirmation before clearing
        print("\n⚠️  WARNING: This will delete all existing data in Neo4j!")
        response = input("Do you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Aborted.")
            return
        
        # Clear database
        loader.clear_database()
        
        # Create constraints
        loader.create_constraints()
        
        # Load nodes
        loader.load_people(data['nodes']['people'])
        loader.load_teams(data['nodes']['teams'])
        loader.load_identity_mappings(data['nodes']['identity_mappings'])
        
        # Load relationships
        loader.load_relationships(data['relationships'])
        
        # Run validation
        loader.run_validation_queries()
        
        print("\n" + "=" * 60)
        print("✓ Layer 1 loaded successfully!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Open Neo4j Browser at http://localhost:7474")
        print("2. Run queries to explore the data")
        print("3. Proceed to Layer 2 (Jira Initiatives)")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        loader.close()

if __name__ == "__main__":
    main()

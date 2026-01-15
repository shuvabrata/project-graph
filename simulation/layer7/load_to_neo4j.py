"""
Layer 7: Load Git Commits & Files to Neo4j
"""

import json
import os
from pathlib import Path
from neo4j import GraphDatabase


class Layer7Loader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def load_layer7(self, data):
        with self.driver.session() as session:
            # Clear existing Layer 7 data
            print("🧹 Clearing existing Layer 7 data...")
            session.run("MATCH (c:Commit) DETACH DELETE c")
            session.run("MATCH (f:File) DETACH DELETE f")
            print("   ✓ Cleared existing data\n")
            
            # Create constraints
            print("📋 Creating constraints...")
            session.run("CREATE CONSTRAINT commit_id IF NOT EXISTS FOR (c:Commit) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT commit_sha IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE")
            session.run("CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE")
            print("   ✓ Constraints created\n")
            
            # Load Commit nodes
            print("💾 Loading Commit nodes...")
            for commit in data["nodes"]["commits"]:
                session.run("""
                    CREATE (c:Commit {
                        id: $id,
                        sha: $sha,
                        message: $message,
                        timestamp: datetime($timestamp),
                        additions: $additions,
                        deletions: $deletions,
                        files_changed: $files_changed
                    })
                """, **commit)
            print(f"   ✓ Created {len(data['nodes']['commits'])} Commit nodes\n")
            
            # Load File nodes
            print("📁 Loading File nodes...")
            for file in data["nodes"]["files"]:
                session.run("""
                    CREATE (f:File {
                        id: $id,
                        path: $path,
                        name: $name,
                        extension: $extension,
                        language: $language,
                        is_test: $is_test,
                        size: $size,
                        created_at: datetime($created_at)
                    })
                """, **file)
            print(f"   ✓ Created {len(data['nodes']['files'])} File nodes\n")
            
            # Load relationships
            print("🔗 Loading relationships...")
            rels_by_type = {}
            for rel in data["relationships"]:
                rel_type = rel["type"]
                if rel_type not in rels_by_type:
                    rels_by_type[rel_type] = []
                rels_by_type[rel_type].append(rel)
            
            # PART_OF: Commit → Branch (bidirectional)
            for rel in rels_by_type.get("PART_OF", []):
                session.run("""
                    MATCH (c:Commit {id: $from_id})
                    MATCH (b:Branch {id: $to_id})
                    CREATE (c)-[:PART_OF]->(b)
                    CREATE (b)-[:CONTAINS]->(c)
                """, from_id=rel["from_id"], to_id=rel["to_id"])
            print(f"   ✓ Created {len(rels_by_type.get('PART_OF', []))} PART_OF relationships")
            
            # AUTHORED_BY: Commit → Person (bidirectional)
            for rel in rels_by_type.get("AUTHORED_BY", []):
                session.run("""
                    MATCH (c:Commit {id: $from_id})
                    MATCH (p:Person {id: $to_id})
                    CREATE (c)-[:AUTHORED_BY]->(p)
                    CREATE (p)-[:AUTHORED_BY]->(c)
                """, from_id=rel["from_id"], to_id=rel["to_id"])
            print(f"   ✓ Created {len(rels_by_type.get('AUTHORED_BY', []))} AUTHORED_BY relationships")
            
            # MODIFIES: Commit → File (with properties, bidirectional)
            for rel in rels_by_type.get("MODIFIES", []):
                props = rel.get("properties", {})
                session.run("""
                    MATCH (c:Commit {id: $from_id})
                    MATCH (f:File {id: $to_id})
                    CREATE (c)-[:MODIFIES {additions: $additions, deletions: $deletions}]->(f)
                    CREATE (f)-[:MODIFIES {additions: $additions, deletions: $deletions}]->(c)
                """, from_id=rel["from_id"], to_id=rel["to_id"],
                    additions=props.get("additions", 0), deletions=props.get("deletions", 0))
            print(f"   ✓ Created {len(rels_by_type.get('MODIFIES', []))} MODIFIES relationships")
            
            # REFERENCES: Commit → Issue (bidirectional)
            for rel in rels_by_type.get("REFERENCES", []):
                session.run("""
                    MATCH (c:Commit {id: $from_id})
                    MATCH (i:Issue {id: $to_id})
                    CREATE (c)-[:REFERENCES]->(i)
                    CREATE (i)-[:REFERENCES]->(c)
                """, from_id=rel["from_id"], to_id=rel["to_id"])
            print(f"   ✓ Created {len(rels_by_type.get('REFERENCES', []))} REFERENCES relationships\n")
    
    def validate(self):
        print("✅ Running validation queries...\n")
        
        with self.driver.session() as session:
            # Total counts
            result = session.run("MATCH (c:Commit) RETURN count(c) as count")
            print(f"📊 Total commits: {result.single()['count']}")
            
            result = session.run("MATCH (f:File) RETURN count(f) as count")
            print(f"📁 Total files: {result.single()['count']}")
            
            result = session.run("""
                MATCH (c:Commit)-[:REFERENCES]->(i:Issue)
                RETURN count(DISTINCT c) as count
            """)
            print(f"🔗 Commits with Jira refs: {result.single()['count']}\n")
            
            # Top contributors
            print("👥 Top 5 contributors:")
            result = session.run("""
                MATCH (p:Person)<-[:AUTHORED_BY]-(c:Commit)
                RETURN p.name as name, p.title as title, count(c) as commits
                ORDER BY commits DESC
                LIMIT 5
            """)
            for record in result:
                print(f"   • {record['name']} ({record['title']}): {record['commits']} commits")
            
            # Commits per repo
            print("\n📦 Commits per repository:")
            result = session.run("""
                MATCH (c:Commit)-[:PART_OF]->(b:Branch)-[:BRANCH_OF]->(r:Repository)
                WHERE b.is_default = true
                RETURN r.name as repo, count(c) as commits
                ORDER BY commits DESC
            """)
            for record in result:
                print(f"   • {record['repo']}: {record['commits']} commits")
            
            # Hotspot files
            print("\n🔥 Top 5 hotspot files:")
            result = session.run("""
                MATCH (f:File)<-[:MODIFIES]-(c:Commit)
                RETURN f.path as path, f.language as lang, count(c) as mods
                ORDER BY mods DESC
                LIMIT 5
            """)
            for record in result:
                print(f"   • {record['path']} ({record['lang']}): {record['mods']} modifications")
            
            # Files by language
            print("\n🗂️  Files by language:")
            result = session.run("""
                MATCH (f:File)
                RETURN f.language as lang, count(f) as count
                ORDER BY count DESC
            """)
            for record in result:
                print(f"   • {record['lang']}: {record['count']} files")
            
            print("\n✅ Layer 7 loaded successfully!")


def main():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    
    data_path = Path(__file__).parent.parent / "data" / "layer7_commits.json"
    
    if not data_path.exists():
        print(f"❌ Error: {data_path} not found!")
        print("   Run generate_data.py first.")
        return
    
    print(f"📖 Loading data from {data_path}...\n")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    
    loader = Layer7Loader(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        loader.load_layer7(data)
        loader.validate()
    finally:
        loader.close()


if __name__ == "__main__":
    main()

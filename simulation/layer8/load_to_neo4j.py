"""
Layer 8: Load Pull Requests to Neo4j
Loads PR nodes and relationships into Neo4j database.
"""

import json
from typing import Dict, Any

from neo4j import GraphDatabase

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"


def load_data_file() -> Dict[str, Any]:
    """Load the generated Layer 8 data."""
    with open('../data/layer8_pull_requests.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def create_pull_request_nodes(session, pull_requests: list):
    """Create PullRequest nodes in Neo4j."""
    query = """
    UNWIND $pull_requests as pr
    CREATE (p:PullRequest {
        id: pr.id,
        number: pr.number,
        title: pr.title,
        description: pr.description,
        state: pr.state,
        created_at: datetime(pr.created_at),
        updated_at: datetime(pr.updated_at),
        merged_at: CASE WHEN pr.merged_at IS NOT NULL THEN datetime(pr.merged_at) ELSE null END,
        closed_at: CASE WHEN pr.closed_at IS NOT NULL THEN datetime(pr.closed_at) ELSE null END,
        commits_count: pr.commits_count,
        additions: pr.additions,
        deletions: pr.deletions,
        changed_files: pr.changed_files,
        comments: pr.comments,
        review_comments: pr.review_comments,
        head_branch_name: pr.head_branch_name,
        base_branch_name: pr.base_branch_name,
        labels: pr.labels,
        mergeable_state: pr.mergeable_state
    })
    """
    result = session.run(query, pull_requests=pull_requests)
    return result.consume().counters.nodes_created


def create_pr_relationships(session, relationships: list):
    """Create all PR-related relationships in Neo4j."""
    
    relationship_types = {
        'INCLUDES': 0,
        'TARGETS': 0,
        'FROM': 0,
        'CREATED_BY': 0,
        'REVIEWED_BY': 0,
        'REQUESTED_REVIEWER': 0,
        'MERGED_BY': 0
    }
    
    # Group relationships by type
    rels_by_type = {}
    for rel in relationships:
        rel_type = rel['type']
        if rel_type not in rels_by_type:
            rels_by_type[rel_type] = []
        rels_by_type[rel_type].append(rel)
    
    # INCLUDES: PullRequest → Commit (for merged PRs only)
    if 'INCLUDES' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (c:Commit {id: rel.to_id})
        CREATE (pr)-[:INCLUDES]->(c)
        """
        result = session.run(query, relationships=rels_by_type['INCLUDES'])
        relationship_types['INCLUDES'] = result.consume().counters.relationships_created
    
    # TARGETS: PullRequest → Branch (base branch)
    if 'TARGETS' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (b:Branch {id: rel.to_id})
        CREATE (pr)-[:TARGETS]->(b)
        """
        result = session.run(query, relationships=rels_by_type['TARGETS'])
        relationship_types['TARGETS'] = result.consume().counters.relationships_created
    
    # FROM: PullRequest → Branch (head branch)
    if 'FROM' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (b:Branch {id: rel.to_id})
        CREATE (pr)-[:FROM]->(b)
        """
        result = session.run(query, relationships=rels_by_type['FROM'])
        relationship_types['FROM'] = result.consume().counters.relationships_created
    
    # CREATED_BY: PullRequest → Person
    if 'CREATED_BY' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (p:Person {id: rel.to_id})
        CREATE (pr)-[:CREATED_BY]->(p)
        """
        result = session.run(query, relationships=rels_by_type['CREATED_BY'])
        relationship_types['CREATED_BY'] = result.consume().counters.relationships_created
    
    # REVIEWED_BY: PullRequest → Person (with state property)
    if 'REVIEWED_BY' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (p:Person {id: rel.to_id})
        CREATE (pr)-[:REVIEWED_BY {state: rel.properties.state}]->(p)
        """
        result = session.run(query, relationships=rels_by_type['REVIEWED_BY'])
        relationship_types['REVIEWED_BY'] = result.consume().counters.relationships_created
    
    # REQUESTED_REVIEWER: PullRequest → Person
    if 'REQUESTED_REVIEWER' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (p:Person {id: rel.to_id})
        CREATE (pr)-[:REQUESTED_REVIEWER]->(p)
        """
        result = session.run(query, relationships=rels_by_type['REQUESTED_REVIEWER'])
        relationship_types['REQUESTED_REVIEWER'] = result.consume().counters.relationships_created
    
    # MERGED_BY: PullRequest → Person (for merged PRs only)
    if 'MERGED_BY' in rels_by_type:
        query = """
        UNWIND $relationships as rel
        MATCH (pr:PullRequest {id: rel.from_id})
        MATCH (p:Person {id: rel.to_id})
        CREATE (pr)-[:MERGED_BY]->(p)
        """
        result = session.run(query, relationships=rels_by_type['MERGED_BY'])
        relationship_types['MERGED_BY'] = result.consume().counters.relationships_created
    
    return relationship_types


def run_validation_queries(session):
    """Run validation queries to verify the data."""
    print("\n" + "=" * 70)
    print("VALIDATION QUERIES")
    print("=" * 70)
    
    # 1. Total PRs by state
    print("\n1. Pull Requests by State:")
    result = session.run("""
        MATCH (pr:PullRequest)
        RETURN pr.state as state, count(pr) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"   {record['state']}: {record['count']} PRs")
    
    # 2. PRs per repository
    print("\n2. Pull Requests per Repository:")
    result = session.run("""
        MATCH (pr:PullRequest)-[:TARGETS]->(b:Branch)-[:BRANCH_OF]->(r:Repository)
        RETURN r.name as repo, 
               count(pr) as total_prs,
               sum(CASE WHEN pr.state = 'merged' THEN 1 ELSE 0 END) as merged,
               sum(CASE WHEN pr.state = 'open' THEN 1 ELSE 0 END) as open,
               sum(CASE WHEN pr.state = 'closed' THEN 1 ELSE 0 END) as closed
        ORDER BY total_prs DESC
    """)
    for record in result:
        print(f"   {record['repo']}: {record['total_prs']} total "
              f"(merged: {record['merged']}, open: {record['open']}, closed: {record['closed']})")
    
    # 3. Top PR creators
    print("\n3. Top 10 PR Creators:")
    result = session.run("""
        MATCH (pr:PullRequest)-[:CREATED_BY]->(p:Person)
        RETURN p.name as creator, p.title as title, count(pr) as pr_count
        ORDER BY pr_count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   {record['creator']} ({record['title']}): {record['pr_count']} PRs")
    
    # 4. Top reviewers
    print("\n4. Top 10 Reviewers:")
    result = session.run("""
        MATCH (pr:PullRequest)-[:REVIEWED_BY]->(p:Person)
        RETURN p.name as reviewer, p.title as title, count(pr) as reviews
        ORDER BY reviews DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   {record['reviewer']} ({record['title']}): {record['reviews']} reviews")
    
    # 5. Average PR metrics
    print("\n5. Average PR Metrics:")
    result = session.run("""
        MATCH (pr:PullRequest)
        WHERE pr.state = 'merged'
        RETURN avg(pr.commits_count) as avg_commits,
               avg(pr.additions) as avg_additions,
               avg(pr.deletions) as avg_deletions,
               avg(pr.changed_files) as avg_files
    """)
    record = result.single()
    print(f"   Average commits per PR: {record['avg_commits']:.1f}")
    print(f"   Average additions per PR: {record['avg_additions']:.0f}")
    print(f"   Average deletions per PR: {record['avg_deletions']:.0f}")
    print(f"   Average files changed per PR: {record['avg_files']:.1f}")
    
    # 6. PR cycle time (merged PRs only)
    print("\n6. PR Cycle Time (created to merged):")
    result = session.run("""
        MATCH (pr:PullRequest)
        WHERE pr.state = 'merged'
        WITH duration.between(pr.created_at, pr.merged_at).days as days
        RETURN avg(days) as avg_days, min(days) as min_days, max(days) as max_days
    """)
    record = result.single()
    print(f"   Average: {record['avg_days']:.1f} days")
    print(f"   Min: {record['min_days']:.1f} days")
    print(f"   Max: {record['max_days']:.1f} days")
    
    # 7. PRs with most commits
    print("\n7. PRs with Most Commits (Top 5):")
    result = session.run("""
        MATCH (pr:PullRequest)-[:TARGETS]->(b:Branch)-[:BRANCH_OF]->(r:Repository)
        RETURN pr.number as pr_num, pr.title as title, r.name as repo, pr.commits_count as commits
        ORDER BY commits DESC
        LIMIT 5
    """)
    for record in result:
        print(f"   #{record['pr_num']} ({record['repo']}): {record['commits']} commits - {record['title']}")
    
    # 8. Review bottleneck analysis
    print("\n8. Review Bottleneck Analysis (requested but not reviewed):")
    result = session.run("""
        MATCH (pr:PullRequest)-[:REQUESTED_REVIEWER]->(p:Person)
        WHERE NOT (pr)-[:REVIEWED_BY]->(p)
        WITH p.name as reviewer, count(pr) as pending_reviews
        RETURN reviewer, pending_reviews
        ORDER BY pending_reviews DESC
        LIMIT 10
    """)
    count = 0
    for record in result:
        print(f"   {record['reviewer']}: {record['pending_reviews']} pending reviews")
        count += 1
    if count == 0:
        print("   No pending reviews found")
    
    # 9. PRs with most code changes
    print("\n9. PRs with Most Code Changes (Top 5):")
    result = session.run("""
        MATCH (pr:PullRequest)-[:TARGETS]->(b:Branch)-[:BRANCH_OF]->(r:Repository)
        WITH pr, r, (pr.additions + pr.deletions) as total_changes
        RETURN pr.number as pr_num, pr.title as title, r.name as repo, 
               total_changes, pr.additions as adds, pr.deletions as dels
        ORDER BY total_changes DESC
        LIMIT 5
    """)
    for record in result:
        print(f"   #{record['pr_num']} ({record['repo']}): {record['total_changes']} changes "
              f"(+{record['adds']}/-{record['dels']}) - {record['title']}")
    
    # 10. Commits included in PRs (for merged PRs)
    print("\n10. Commit Integration Statistics:")
    result = session.run("""
        MATCH (pr:PullRequest)-[:INCLUDES]->(c:Commit)
        WITH count(DISTINCT pr) as prs_with_commits, count(c) as total_commits
        RETURN prs_with_commits, total_commits, total_commits * 1.0 / prs_with_commits as avg_commits_per_pr
    """)
    record = result.single()
    if record and record['prs_with_commits']:
        print(f"   PRs with commits: {record['prs_with_commits']}")
        print(f"   Total commits in PRs: {record['total_commits']}")
        print(f"   Average commits per PR: {record['avg_commits_per_pr']:.1f}")
    else:
        print("   No commits linked to PRs found")


def main():
    print("=" * 70)
    print("Layer 8: Pull Requests - Neo4j Loader")
    print("=" * 70)
    
    # Load data
    print("\n📂 Loading data from layer8_pull_requests.json...")
    data = load_data_file()
    
    pull_requests = data['nodes']['pull_requests']
    relationships = data['relationships']
    
    print(f"   • Pull Requests: {len(pull_requests)}")
    print(f"   • Relationships: {len(relationships)}")
    
    # Connect to Neo4j
    print(f"\n🔌 Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Clear existing Layer 8 data
            print("\n🧹 Clearing existing Layer 8 data...")
            session.run("MATCH (pr:PullRequest) DETACH DELETE pr")
            print("   ✓ Cleared existing PullRequest nodes and relationships")
            
            # Create constraints
            print("\n📋 Creating constraints...")
            session.run("CREATE CONSTRAINT pr_id IF NOT EXISTS FOR (pr:PullRequest) REQUIRE pr.id IS UNIQUE")
            print("   ✓ Created PullRequest id constraint")
            
            # Create nodes
            print("\n💾 Creating PullRequest nodes...")
            nodes_created = create_pull_request_nodes(session, pull_requests)
            print(f"   ✓ Created {nodes_created} PullRequest nodes")
            
            # Create relationships
            print("\n🔗 Creating relationships...")
            rel_counts = create_pr_relationships(session, relationships)
            for rel_type, count in rel_counts.items():
                if count > 0:
                    print(f"   ✓ Created {count} {rel_type} relationships")
            
            total_rels = sum(rel_counts.values())
            print(f"\n   Total relationships created: {total_rels}")
            
            # Run validation
            run_validation_queries(session)
            
    finally:
        driver.close()
    
    print("\n" + "=" * 70)
    print("✅ Layer 8 data loaded successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

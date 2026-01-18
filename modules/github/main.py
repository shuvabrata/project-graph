#!/usr/bin/env python3
"""
GitHub Repository Information Fetcher

Loads repository URLs from .config.json and fetches repository properties
using the GitHub API.
"""

import json
import os
from pathlib import Path
from github import Github
from neo4j import GraphDatabase
from db.models import (
    Person, Team, Repository, IdentityMapping, Relationship,
    merge_person, merge_team, merge_repository, merge_identity_mapping, merge_relationship
)


def load_config():
    """Load repository configuration from .config.json"""
    config_path = Path(__file__).parent / ".config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_github_client(repo_config):
    """
    Get GitHub client with appropriate authentication.
    
    Uses repo-specific token if provided, otherwise falls back to 
    GITHUB_TOKEN_FOR_PUBLIC_REPOS environment variable.
    """
    token = repo_config.get('access_token')
    
    if not token:
        token = os.getenv('GITHUB_TOKEN_FOR_PUBLIC_REPOS')
    
    if not token:
        raise ValueError("No GitHub token found. Please provide token in config or set GITHUB_TOKEN_FOR_PUBLIC_REPOS")
    
    return Github(token)


def map_permissions_to_general(permissions):
    """
    Map GitHub permissions to general READ or WRITE access.
    
    Args:
        permissions: Dictionary of permission flags (with underscore prefixes)
    
    Returns:
        str: "WRITE" or "READ" based on permissions
    """
    # WRITE permissions (in order of precedence)
    write_permissions = ['_admin', '_maintain', '_push']
    
    # Check if user has any write permissions
    for perm in write_permissions:
        if permissions.get(perm, False):
            return "WRITE"
    
    # Default to READ (includes '_pull', '_triage', or any read-only access)
    return "READ"


def new_user_handler(session, collaborator, repo_id, repo_created_at):
    """Handle a new user collaborator by creating Person, IdentityMapping nodes and COLLABORATOR relationship.
    
    Args:
        session: Neo4j session
        collaborator: GitHub collaborator object with attributes like login, name, email, type, permissions
        repo_id: Repository ID to create COLLABORATOR relationship with
        repo_created_at: Repository creation date for relationship timestamp
    """
    try:
        # Extract available information from collaborator
        github_login = collaborator.login
        github_name = collaborator.name if hasattr(collaborator, 'name') and collaborator.name else github_login
        github_email = collaborator.email if hasattr(collaborator, 'email') and collaborator.email else ""
        
        # Create Person node (prefix with person_github_ for global uniqueness)
        # Eg: A GitHub user "alice" and a Jira user "alice" could be actually different people
        person_id = f"person_github_{github_login}"
        person = Person(
            id=person_id,
            name=github_name,
            email=github_email,
            title="",
            role="",
            seniority="",
            hire_date="",
            is_manager=False
        )
        
        # Create IdentityMapping node
        identity = IdentityMapping(
            id=f"identity_github_{github_login}",
            provider="GitHub",
            username=github_login,
            email=github_email
        )
        
        # Create MAPS_TO relationship from IdentityMapping to Person
        maps_to_relationship = Relationship(
            type="MAPS_TO",
            from_id=identity.id,
            to_id=person_id,
            from_type="IdentityMapping",
            to_type="Person"
        )
        
        # Merge into Neo4j (MERGE handles deduplication)
        merge_person(session, person)
        person.print_cli()

        merge_identity_mapping(session, identity, relationships=[maps_to_relationship])
        identity.print_cli()
        maps_to_relationship.print_cli()
        
        # Extract permissions and map to general READ/WRITE
        permission = map_permissions_to_general(collaborator.permissions.__dict__)
        
        # Determine role based on permissions
        role = None
        if collaborator.permissions.admin:
            role = "admin"
        elif collaborator.permissions.maintain:
            role = "maintainer"
        elif collaborator.permissions.push:
            role = "contributor"
        
        # Create COLLABORATOR relationship from Person to Repository
        collab_properties = {
            "permission": permission,
            "granted_at": repo_created_at
        }
        if role:
            collab_properties["role"] = role
        
        collaborator_relationship = Relationship(
            type="COLLABORATOR",
            from_id=person_id,
            to_id=repo_id,
            from_type="Person",
            to_type="Repository",
            properties=collab_properties
        )
        
        merge_relationship(session, collaborator_relationship)
        collaborator_relationship.print_cli()
        
    except Exception as e:
        print(f"    Warning: Failed to create Person/IdentityMapping/COLLABORATOR for {collaborator.login}: {str(e)}")


def new_team_handler(session, team, repo_id, repo_created_at):
    """Handle a new team by creating Team node and COLLABORATOR relationship to repository.
    
    Args:
        session: Neo4j session
        team: GitHub team object with attributes like name, slug, permission
        repo_id: Repository ID to create relationship with
        repo_created_at: Repository creation date for relationship timestamp
    """
    try:
        # Extract available information from team
        team_slug = team.slug
        team_name = team.name
        
        # Map GitHub permission to general READ/WRITE
        # GitHub team permissions: pull, push, admin, maintain, triage
        permission_mapping = {
            'pull': 'READ',
            'triage': 'READ',
            'push': 'WRITE',
            'maintain': 'WRITE',
            'admin': 'WRITE'
        }
        permission = permission_mapping.get(team.permission, 'READ')
        
        # Create Team node (prefix with team_github_ for global uniqueness)
        team_id = f"team_github_{team_slug}"
        team_node = Team(
            id=team_id,
            name=team_name,
            focus_area="",  # GitHub API doesn't provide this
            target_size=0,   # GitHub API doesn't provide this
            created_at=repo_created_at  # Use repo creation as proxy
        )
        
        # Create COLLABORATOR relationship from Team to Repository
        relationship = Relationship(
            type="COLLABORATOR",
            from_id=team_id,
            to_id=repo_id,
            from_type="Team",
            to_type="Repository",
            properties={
                "permission": permission,
                "granted_at": repo_created_at
            }
        )
        
        # Merge into Neo4j (MERGE handles deduplication)
        merge_team(session, team_node)
        team_node.print_cli()
        
        merge_relationship(session, relationship)
        relationship.print_cli()

        #Todo: Add members of the team as Persons and link them to the Team?
        
    except Exception as e:
        print(f"    Warning: Failed to create Team/COLLABORATOR for {team.slug}: {str(e)}")


def new_repo_handler(session, repo):
    """Handle a repository by creating Repository node in Neo4j.
    
    Args:
        session: Neo4j session
        repo: GitHub repository object
        
    Returns:
        tuple: (repo_id, repo_created_at) or (None, None) if failed
    """
    try:
        # Extract repository information
        repo_id = f"repo_{repo.name.replace('-', '_')}"
        repo_created_at = repo.created_at.strftime("%Y-%m-%d") if repo.created_at else None
        
        # Create Repository node
        repository = Repository(
            id=repo_id,
            name=repo.name,
            full_name=repo.full_name,
            url=repo.html_url,
            language=repo.language or "",
            is_private=repo.private,
            description=repo.description or "",
            topics=repo.get_topics(),
            created_at=repo_created_at
        )
        
        # Merge into Neo4j
        merge_repository(session, repository)
        repository.print_cli()
        
        return repo_id, repo_created_at
        
    except Exception as e:
        print(f"    ✗ Error: Failed to create Repository for {repo.name}: {str(e)}")
        return None, None


def process_repo(repo, session):
    """Process repository: create repo node, collaborators, and teams in Neo4j."""
    # Step 1: Create Repository node FIRST
    repo_id, repo_created_at = new_repo_handler(session, repo)
    
    # If repo creation failed, skip collaborators/teams
    if repo_id is None:
        print(f"    Warning: Skipping collaborators/teams due to repo creation failure")
        raise Exception("Repository node creation failed")
    
    # Step 2: Process collaborators (creates Person, IdentityMapping, and COLLABORATOR relationships)
    try:
        collaborators = repo.get_collaborators()
        for collab in collaborators:
            if collab.type == 'User':
                new_user_handler(session, collab, repo_id, repo_created_at)
    except Exception as e:
        # Collaborators might not be accessible for certain repos
        print(f"    Warning: Could not fetch collaborators - {str(e)}")
    
    # Step 3: Fetch teams (only available for organization repositories)
    try:
        teams = repo.get_teams()
        for team in teams:
            # Create Team node and COLLABORATOR relationship
            new_team_handler(session, team, repo_id, repo_created_at)
    except Exception as e:
        # Teams might not be accessible for personal repos or due to permissions
        print(f"    Warning: Could not fetch teams - {str(e)}")


def parse_repo_url(url):
    """
    Extract owner and repo name from GitHub URL.
    
    Example: https://github.com/owner/repo -> (owner, repo)
    Example: https://github.com/owner/* -> (owner, *)
    """
    parts = url.rstrip('/').split('/')
    return parts[-2], parts[-1]


def is_wildcard_url(url):
    """
    Check if the URL is a wildcard pattern (e.g., https://github.com/owner/*)
    """
    return url.rstrip('/').endswith('/*') or url.rstrip('/').endswith('%2F*')


def get_all_repos_for_owner(client, owner):
    """
    Get all repositories for a given owner (user or organization).
    
    Args:
        client: GitHub client instance
        owner: GitHub username or organization name
    
    Returns:
        list: List of repository objects
    """
    repos = []
    try:
        # Try as organization first
        org = client.get_organization(owner)
        repos = list(org.get_repos())
        print(f"Found {len(repos)} repositories for organization: {owner}")
    except Exception:
        # If not an organization, try as user
        try:
            user = client.get_user(owner)
            repos = list(user.get_repos())
            print(f"Found {len(repos)} repositories for user: {owner}")
        except Exception as e:
            print(f"Error fetching repositories for {owner}: {str(e)}")
    
    return repos


def main():
    """Main execution function"""
    print("GitHub Repository Information Fetcher")
    print("=" * 50)
    
    # Initialize Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    
    print(f"\nConnecting to Neo4j at {neo4j_uri}...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Verify connection
        driver.verify_connectivity()
        print("✓ Neo4j connection established\n")
        
        # Load configuration
        config = load_config()
        print(f"Loaded {len(config['repos'])} repositories from config\n")
        
        # Counters for tracking
        repos_processed = 0
        repos_failed = 0
        
        # Create a session for the entire operation
        with driver.session() as session:
            # Process each repository
            for idx, repo_config in enumerate(config['repos'], 1):
                repo_url = repo_config['url']
                print(f"\n[{idx}] Processing: {repo_url}")
                print("-" * 50)
                
                try:
                    # Get GitHub client
                    client = get_github_client(repo_config)
                    
                    # Check if this is a wildcard URL (e.g., https://github.com/owner/*)
                    if is_wildcard_url(repo_url):
                        # Extract owner and enumerate all repos
                        owner, _ = parse_repo_url(repo_url)
                        print(f"Wildcard pattern detected. Fetching all repositories for: {owner}")
                        
                        repos = get_all_repos_for_owner(client, owner)
                        
                        for repo in repos:
                            try:
                                # Process repository (creates nodes and relationships)
                                print(f"\n  ↳ {repo.name}")
                                process_repo(repo, session)
                                repos_processed += 1
                                
                            except Exception as e:
                                print(f"    ✗ Error processing {repo.name}: {str(e)}")
                                repos_failed += 1
                                continue
                                
                    else:
                        # Single repository
                        # Parse URL and get repository
                        owner, repo_name = parse_repo_url(repo_url)
                        repo = client.get_repo(f"{owner}/{repo_name}")
                        
                        # Process repository (creates nodes and relationships)
                        process_repo(repo, session)
                        repos_processed += 1
                    
                except Exception as e:
                    print(f"✗ Error: {str(e)}")
                    repos_failed += 1
                    continue
        
        print("\n" + "=" * 50)
        print("\nSummary:")
        print(f"  ✓ Successfully processed: {repos_processed}")
        print(f"  ✗ Failed: {repos_failed}")
        print(f"  Total: {repos_processed + repos_failed}")
        
    finally:
        # Close Neo4j connection
        driver.close()
        print("\n✓ Neo4j connection closed")


if __name__ == "__main__":
    main()

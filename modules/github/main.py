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
from db.models import Person, IdentityMapping, Relationship, merge_person, merge_identity_mapping


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


def new_user_handler(session, collaborator):
    """
    Handle a new user collaborator by creating Person and IdentityMapping nodes.
    
    Args:
        session: Neo4j session
        collaborator: GitHub collaborator object with attributes like login, name, email, type
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
        relationship = Relationship(
            type="MAPS_TO",
            from_id=identity.id,
            to_id=person_id,
            from_type="IdentityMapping",
            to_type="Person"
        )
        
        # Merge into Neo4j (MERGE handles deduplication)
        merge_person(session, person)
        merge_identity_mapping(session, identity, relationships=[relationship])
        
    except Exception as e:
        print(f"    Warning: Failed to create Person/IdentityMapping for {collaborator.login}: {str(e)}")


def extract_repo_info(repo, session):
    """Extract relevant repository information including collaborators and teams"""
    repo_info = {
        "id": f"repo_{repo.name.replace('-', '_')}",
        "name": repo.name,
        "full_name": repo.full_name,
        "url": repo.html_url,
        "language": repo.language,
        "is_private": repo.private,
        "description": repo.description or "",
        "topics": repo.get_topics(),
        "created_at": repo.created_at.strftime("%Y-%m-%d") if repo.created_at else None,
        "teams": []
    }
    
    # Process collaborators
    try:
        collaborators = repo.get_collaborators()
        for collab in collaborators:
            if collab.type == 'User':
                new_user_handler(session, collab)
    except Exception as e:
        # Collaborators might not be accessible for certain repos
        print(f"Warning: Could not fetch collaborators - {str(e)}")
    
    # Fetch teams (only available for organization repositories)
    try:
        teams = repo.get_teams()
        repo_info["teams"] = [
            {
                "name": team.name,
                "slug": team.slug,
                "permission": team.permission
            }
            for team in teams
        ]
    except Exception as e:
        # Teams might not be accessible for personal repos or due to permissions
        repo_info["teams_error"] = str(e)
    
    return repo_info


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


def print_repo_info(repo_info, indent=""):
    """
    Print repository information in a consistent format.
    
    Args:
        repo_info: Dictionary containing repository information
        indent: String to prepend to each line for indentation
    """
    print(f"{indent}ID:          {repo_info['id']}")
    print(f"{indent}Name:        {repo_info['name']}")
    print(f"{indent}Full Name:   {repo_info['full_name']}")
    print(f"{indent}URL:         {repo_info['url']}")
    print(f"{indent}Language:    {repo_info['language']}")
    print(f"{indent}Private:     {repo_info['is_private']}")
    print(f"{indent}Description: {repo_info['description']}")
    print(f"{indent}Topics:      {', '.join(repo_info['topics']) if repo_info['topics'] else 'None'}")
    print(f"{indent}Created:     {repo_info['created_at']}")
    
    # Print teams
    if 'teams_error' in repo_info:
        print(f"{indent}Teams:        Error fetching ({repo_info['teams_error']})")
    else:
        print(f"{indent}Teams:        {len(repo_info['teams'])}")
        for team in repo_info['teams']:
            print(f"{indent}  - {team['name']} (@{team['slug']}) [{team['permission']}]")
    
    print(f"{indent}✓ Successfully fetched")


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
        
        repositories = []
        
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
                                # Extract information
                                repo_info = extract_repo_info(repo, session)
                                repositories.append(repo_info)
                                
                                # Print repository information
                                print(f"\n  ↳ {repo_info['name']}")
                                print_repo_info(repo_info, indent="    ")
                                
                            except Exception as e:
                                print(f"    ✗ Error processing {repo.name}: {str(e)}")
                                continue
                                
                    else:
                        # Single repository
                        # Parse URL and get repository
                        owner, repo_name = parse_repo_url(repo_url)
                        repo = client.get_repo(f"{owner}/{repo_name}")
                        
                        # Extract information
                        repo_info = extract_repo_info(repo, session)
                        repositories.append(repo_info)
                        
                        # Print repository information
                        print_repo_info(repo_info)
                    
                except Exception as e:
                    print(f"✗ Error: {str(e)}")
                    continue
        
        print("\n" + "=" * 50)
        print(f"\nTotal repositories processed: {len(repositories)}/{len(config['repos'])}")
        
    finally:
        # Close Neo4j connection
        driver.close()
        print("\n✓ Neo4j connection closed")


if __name__ == "__main__":
    main()

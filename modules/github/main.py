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
from datetime import datetime


def load_config():
    """Load repository configuration from .config.json"""
    config_path = Path(__file__).parent / ".config.json"
    with open(config_path, 'r') as f:
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


def extract_repo_info(repo):
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
        "collaborators": [],
        "teams": []
    }
    
    # Fetch collaborators
    try:
        collaborators = repo.get_collaborators()
        repo_info["collaborators"] = [
            {
                "login": collab.login,
                "name": collab.name or collab.login,
                "permissions": collab.permissions.__dict__ if hasattr(collab, 'permissions') else {},
                "general_permission": map_permissions_to_general(
                    collab.permissions.__dict__ if hasattr(collab, 'permissions') else {}
                )
            }
            for collab in collaborators
        ]
    except Exception as e:
        # Collaborators might not be accessible for certain repos
        repo_info["collaborators_error"] = str(e)
    
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
    
    # Print collaborators
    if 'collaborators_error' in repo_info:
        print(f"{indent}Collaborators: Error fetching ({repo_info['collaborators_error']})")
    else:
        print(f"{indent}Collaborators: {len(repo_info['collaborators'])}")
        for collab in repo_info['collaborators']:
            permissions = collab.get('permissions', {})
            perm_str = ', '.join([k for k, v in permissions.items() if v]) if permissions else 'N/A'
            general_perm = collab.get('general_permission', 'N/A')
            print(f"{indent}  - {collab['name']} (@{collab['login']}) [{perm_str}] -> {general_perm}")
    
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
    
    # Load configuration
    config = load_config()
    print(f"\nLoaded {len(config['repos'])} repositories from config\n")
    
    repositories = []
    
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
                        repo_info = extract_repo_info(repo)
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
                repo_info = extract_repo_info(repo)
                repositories.append(repo_info)
                
                # Print repository information
                print_repo_info(repo_info)
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            continue
    
    print("\n" + "=" * 50)
    print(f"\nTotal repositories processed: {len(repositories)}/{len(config['repos'])}")


if __name__ == "__main__":
    main()

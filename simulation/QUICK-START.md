# Quick Start Guide - Project Graph Simulation

This guide provides step-by-step instructions to set up and run the simulation from scratch.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8 or higher
- Neo4j running (via Docker Compose)

## Initial Setup

### 1. Start Neo4j Database

```bash
# From project root
docker compose up -d
```

Verify Neo4j is running:
- Open http://localhost:7474 in your browser
- Login with username: `neo4j`, password: `password123`

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Loading Data Layer by Layer

### Layer 1: People & Teams (Foundation)

```bash
cd simulation/layer1
python generate_data.py
python load_to_neo4j.py
```

**What this creates:**
- 57 people (50 engineers, 5 managers, 2 PMs)
- 5 teams
- 114 identity mappings (GitHub + Jira)

### Layer 2: Jira Initiatives

```bash
cd ../layer2
python generate_data.py
python load_to_neo4j.py
```

**What this creates:**
- 1 project
- 3 high-level initiatives

### Layer 3: Jira Epics

```bash
cd ../layer3
python generate_data.py
python load_to_neo4j.py
```

**What this creates:**
- 12 epics across 3 initiatives

### Layer 4: Jira Stories & Bugs

```bash
cd ../layer4
python generate_data.py
python load_to_neo4j.py
```

**What this creates:**
- 80 issues (stories, bugs, tasks)
- 4 sprints

### Layer 5: Git Repositories

```bash
cd ../layer5
python generate_data.py
python load_to_neo4j.py
```

**What this creates:**
- 8 repositories
- Collaborator relationships (teams and people with READ/WRITE permissions)

### Layer 6: Git Branches (Coming Soon)

```bash
cd ../layer6
python generate_data.py
python load_to_neo4j.py
```

### Layer 7: Git Commits (Coming Soon)

```bash
cd ../layer7
python generate_data.py
python load_to_neo4j.py
```

## Reload All Data from Scratch

If you need to start over:

```bash
# Layer 1 clears the entire database
cd simulation/layer1
echo "yes" | python load_to_neo4j.py

# Then reload subsequent layers
cd ../layer2 && python load_to_neo4j.py
cd ../layer3 && python load_to_neo4j.py
cd ../layer4 && python load_to_neo4j.py
cd ../layer5 && python load_to_neo4j.py
```

## Verify Installation

### Check Data in Neo4j Browser

Open http://localhost:7474 and try these queries:

```cypher
// Count all nodes
MATCH (n) RETURN labels(n) as type, count(*) as count

// View org structure
MATCH (p:Person)-[:MEMBER_OF]->(t:Team)
RETURN t.name, count(p) as team_size
ORDER BY team_size DESC

// View initiatives
MATCH (i:Initiative)
RETURN i.key, i.summary, i.status

// View repository ownership
MATCH (t:Team)-[c:COLLABORATOR {permission:'WRITE'}]->(r:Repository)
RETURN t.name, collect(r.name) as repos
```

## Common Issues

### Neo4j Connection Error

```
ModuleNotFoundError: No module named 'neo4j'
```
**Solution:** Make sure virtual environment is activated: `source .venv/bin/activate`

### Docker Not Running

```
Could not connect to bolt://localhost:7687
```
**Solution:** Start Neo4j with `docker compose up -d`

### Data Already Exists

```
Node already exists with id: person_xxx
```
**Solution:** Clear database by reloading Layer 1 (it clears all data first)

## Next Steps

After loading all layers:

1. Explore the [graph-simulation.md](graph-simulation.md) for detailed documentation
2. Try the validation queries in each layer's README
3. Experiment with your own analytical queries
4. Review [design/high-level-design.md](../design/high-level-design.md) for use cases

## Useful Commands

```bash
# Check Neo4j logs
docker compose logs -f neo4j

# Stop Neo4j
docker compose down

# Remove all data (including volumes)
docker compose down -v

# Restart Neo4j
docker compose restart neo4j
```

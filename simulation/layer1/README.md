# Layer 1: People & Teams Foundation

This layer establishes the organizational structure that serves as the foundation for all subsequent layers.

## Overview

**Nodes Created:**
- 57 Person nodes (50 engineers, 5 managers, 2 product managers)
- 5 Team nodes
- 114 IdentityMapping nodes (GitHub and Jira for each person)

**Relationships Created:**
- `MEMBER_OF`: Person → Team (57 relationships)
- `REPORTS_TO`: Person → Person (52 relationships - engineers and PMs report to managers)
- `MANAGES`: Person → Team (5 relationships - each manager manages one team)
- `MAPS_TO`: IdentityMapping → Person (114 relationships)

## Team Structure

| Team | Size | Focus Area |
|------|------|------------|
| Platform Team | 12 | Infrastructure, DevOps, Security |
| API Team | 10 | Backend Services, Microservices |
| Frontend Team | 10 | Web UI, React, TypeScript |
| Mobile Team | 8 | iOS, Android, React Native |
| Data Team | 10 | Data Engineering, Analytics, ML |

## Engineer Distribution by Seniority

- **Junior Software Engineer**: 10 people
- **Software Engineer (Mid-level)**: 25 people
- **Senior Software Engineer**: 10 people
- **Staff Software Engineer**: 5 people
- **Engineering Managers**: 5 people
- **Product Managers**: 2 people

## Usage

### Step 1: Generate the Data

```bash
cd simulation/layer1
python generate_data.py
```

This creates `data/layer1_people_teams.json` with all the nodes and relationships.

### Step 2: Start Neo4j

Make sure your Neo4j instance is running:

```bash
docker compose up -d
```

### Step 3: Load into Neo4j

```bash
cd simulation/layer1
python load_to_neo4j.py
```

**⚠️ Warning:** This script will clear all existing data in your Neo4j database!

### Step 4: Validate

The loader automatically runs validation queries, but you can also explore in Neo4j Browser:

```cypher
// View all teams and their members
MATCH (t:Team)<-[:MEMBER_OF]-(p:Person)
RETURN t.name, collect(p.name) as members

// View organizational hierarchy
MATCH (p:Person)-[:REPORTS_TO]->(m:Person)
RETURN p, m

// Find all identity mappings for a person
MATCH (p:Person {name: "Add a valid name here"})<-[:MAPS_TO]-(i:IdentityMapping)
RETURN p.name, i.provider, i.username, i.email
```

## Data Quality Checks

After loading, verify:

1. **Total people count**: Should be exactly 57
2. **Team membership**: Each team should have its target size
3. **Reporting structure**: All engineers and PMs should report to someone
4. **Identity mappings**: Each person should have exactly 2 mappings (GitHub + Jira)
5. **Managers**: Each of 5 teams should have exactly 1 manager

## Generated Data Structure

### Person Node Properties
```json
{
  "id": "person_alex_smith",
  "name": "Alex Smith",
  "email": "alex.smith@company.com",
  "title": "Senior Software Engineer",
  "role": "Engineer",
  "seniority": "Senior",
  "hire_date": "2022-06-15",
  "is_manager": false
}
```

### Team Node Properties
```json
{
  "id": "team_platform_team",
  "name": "Platform Team",
  "focus_area": "Infrastructure, DevOps, Security",
  "target_size": 12,
  "created_at": "2024-01-01"
}
```

### IdentityMapping Node Properties
```json
{
  "id": "identity_github_person_alex_smith",
  "provider": "GitHub",
  "username": "alexs",
  "email": "alex.smith@company.com"
}
```

## Next Steps

Once Layer 1 is validated:

1. ✅ Organizational structure is established
2. ➡️ Proceed to **Layer 2: Jira Initiatives** to add high-level business goals
3. All future layers will reference these Person and Team nodes

## Troubleshooting

**Issue**: "Connection refused" when running loader
- Solution: Ensure Neo4j is running: `docker-compose up -d`

**Issue**: "Authentication failed"  
- Solution: Check `.env` file for correct NEO4J_USERNAME and NEO4J_PASSWORD

**Issue**: Script fails with missing module
- Solution: Install dependencies: `pip install neo4j`

**Issue**: Data already exists
- Solution: The loader will prompt to clear the database before loading

## Files

- `generate_data.py` - Generates synthetic people and team data
- `load_to_neo4j.py` - Loads data into Neo4j database
- `README.md` - This file
- `../../data/layer1_people_teams.json` - Generated data file (created by generate_data.py)

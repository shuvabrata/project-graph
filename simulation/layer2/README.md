# Layer 2: Jira Initiatives

This layer adds high-level business initiatives that represent strategic work for 2026.

## Overview

**Nodes Created:**
- 1 Project node: "Engineering 2026"
- 3 Initiative nodes representing major business objectives

**Relationships Created:**
- `PART_OF`: Initiative → Project (3 relationships)
- `ASSIGNED_TO`: Initiative → Person (3 relationships - links to Senior/Staff engineers from Layer 1)
- `REPORTED_BY`: Initiative → Person (3 relationships - links to PMs or Staff engineers from Layer 1)

## Initiatives

| Key | Summary | Timeline | Priority |
|-----|---------|----------|----------|
| INIT-1 | Platform Modernization | Q1-Q2 2026 | High |
| INIT-2 | Customer Portal Rebuild | Q1-Q3 2026 | Critical |
| INIT-3 | Data Pipeline v2 | Q2-Q3 2026 | High |

## Usage

### Prerequisites

Layer 1 must be loaded first! This layer references Person nodes from Layer 1.

### Step 1: Generate the Data

```bash
cd simulation/layer2
python generate_data.py
```

This creates `data/layer2_initiatives.json` with Project, Initiative nodes, and relationships to Layer 1 people.

### Step 2: Load into Neo4j (Incremental)

```bash
cd simulation/layer2
python load_to_neo4j.py
```

**Note:** This is an **incremental load** - it does NOT clear existing data. It adds to Layer 1.

### Step 3: Validate

The loader automatically runs validation queries. You can also explore in Neo4j Browser:

```cypher
// View all initiatives with assignees and reporters
MATCH (i:Initiative)-[:ASSIGNED_TO]->(assignee:Person),
      (i)-[:REPORTED_BY]->(reporter:Person)
RETURN i.key, i.summary, 
       assignee.name as assignee, assignee.title as assignee_title,
       reporter.name as reporter, reporter.title as reporter_title,
       i.status

// Show project hierarchy
MATCH (p:Project)<-[:PART_OF]-(i:Initiative)
RETURN p.name, collect(i.summary) as initiatives

// Initiative timeline
MATCH (i:Initiative)
RETURN i.summary, i.start_date, i.due_date, i.priority
ORDER BY i.start_date
```

## Data Structure

### Project Node Properties
```json
{
  "id": "project_engineering_2026",
  "key": "ENG-2026",
  "name": "Engineering 2026",
  "description": "Engineering initiatives for 2026",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "status": "Active"
}
```

### Initiative Node Properties
```json
{
  "id": "initiative_init_1",
  "key": "INIT-1",
  "summary": "Platform Modernization",
  "description": "Modernize infrastructure with Kubernetes...",
  "priority": "High",
  "status": "In Progress",
  "start_date": "2026-01-01",
  "due_date": "2026-06-30",
  "created_at": "2025-12-01"
}
```

## Assignment Model

**Assignees** (technical owners):
- **Senior Software Engineers** (10 people from Layer 1)
- **Staff Software Engineers** (5 people from Layer 1)

**Reporters** (business stakeholders):
- **Product Managers** (2 people from Layer 1)
- **Staff Software Engineers** (5 people from Layer 1)

This reflects realistic ownership where initiatives have both technical leads (assignees) and business stakeholders (reporters) tracking progress.

## Validation Checks

After loading, verify:

1. **Project exists**: Exactly 1 Project node
2. **Initiatives count**: Exactly 3 Initiative nodes
3. **All initiatives have assignees**: Each Initiative has an ASSIGNED_TO relationship to a Person
4. **All initiatives have reporters**: Each Initiative has a REPORTED_BY relationship to a Person
5. **All initiatives part of project**: Each Initiative connected to Project via PART_OF
6. **Layer 1 preserved**: All Person, Team, IdentityMapping nodes still exist

## Next Steps

Once Layer 2 is validated:

1. ✅ Strategic initiatives are defined
2. ➡️ Proceed to **Layer 3: Jira Epics** to break down initiatives into actionable epics

## Troubleshooting

**Issue**: "No Person nodes found"
- Solution: Load Layer 1 first: `cd ../layer1 && python load_to_neo4j.py`

**Issue**: Script can't find layer1 data file
- Solution: Ensure `simulation/data/layer1_people_teams.json` exists

**Issue**: Constraint already exists error
- Solution: This is normal if you've loaded before - constraints persist

## Files

- `generate_data.py` - Generates initiative data referencing Layer 1 people
- `load_to_neo4j.py` - Incrementally loads data into Neo4j
- `README.md` - This file
- `../data/layer2_initiatives.json` - Generated data file

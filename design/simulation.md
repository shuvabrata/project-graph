# Project Graph Simulation Plan

**Version**: 0.1  
**Last Updated**: January 4, 2026  
**Status**: Planning Phase  
**Timeline**: Next few weeks

---

## 1. Purpose & Goals

### 1.1 Overview
Build a realistic simulation environment using synthetic test data to validate the graph model design and visibility layer before integrating with real enterprise systems.

### 1.2 Success Criteria
- [ ] Neo4j database populated with realistic relationships
- [ ] Can execute analytical queries from high-level-design.md
- [ ] Visibility layer demonstrates value with test data
- [ ] Model design gaps identified and documented
- [ ] Performance baseline established

### 1.3 Key Benefits
- **Risk Reduction**: Validate design decisions early
- **Iterative Development**: Test queries without API rate limits
- **Demo Environment**: Show stakeholders potential insights
- **Performance Testing**: Understand graph query patterns
- **Training Data**: Use for documentation and onboarding

---

## 2. Simulation Scope

### 2.1 In Scope (Phase 1)
We will simulate a realistic mid-sized engineering organization:
- **People**: 50 engineers, 5 managers, 2 product managers
- **Teams**: 5 engineering teams
- **Jira Hierarchy**: 3 Initiatives → 12 Epics → 80 Stories/Bugs
- **Git Repositories**: 8 repositories
- **Branches**: ~40 branches across repos
- **Commits**: ~500 commits (3 months of history)
- **Pull Requests**: ~100 PRs with reviews

### 2.2 Out of Scope (Future Phases)
- Confluence pages
- Cloud infrastructure (AWS/Azure)
- Meetings and calendar data
- Incident management
- Service deployments

---

## 3. Layer-by-Layer Build Plan

We will build the simulation incrementally, validating each layer before proceeding. Each layer adds more nodes and relationships.

### 3.1 Layer 1: People & Teams Foundation
**Goal**: Establish organizational structure and identity graph

#### Nodes to Create
- **Person** (57 total):
  - 50 Software Engineers (10 Junior, 25 Mid, 10 Senior, 5 Staff)
  - 5 Engineering Managers
  - 2 Product Managers
- **Team** (5 teams):
  - Platform Team (12 people)
  - API Team (10 people)
  - Frontend Team (10 people)
  - Mobile Team (8 people)
  - Data Team (10 people)
- **IdentityMapping**: Each person will have mappings for GitHub, Jira

#### Relationships
- `MEMBER_OF`: Person → Team
- `REPORTS_TO`: Person → Person (manager)
- `MANAGES`: Person → Team
- `MAPS_TO`: IdentityMapping → Person

#### Test Data File
- `data/layer1_people_teams.json`

#### Validation Queries
```cypher
// Count people by role
MATCH (p:Person)
RETURN p.role, p.seniority, count(*) as count

// Show org hierarchy
MATCH (p:Person)-[:REPORTS_TO]->(m:Person)
RETURN p.name, m.name, p.title

// Team sizes
MATCH (t:Team)<-[:MEMBER_OF]-(p:Person)
RETURN t.name, count(p) as team_size
ORDER BY team_size DESC
```

---

### 3.2 Layer 2: Jira Initiatives
**Goal**: Create high-level business initiatives

#### Nodes to Create
- **Project** (1 project): "Engineering 2026"
- **Initiative** (represented as Epic with special label):
  - Initiative 1: "Platform Modernization" (Q1-Q2 2026)
  - Initiative 2: "Customer Portal Rebuild" (Q1-Q3 2026)
  - Initiative 3: "Data Pipeline v2" (Q2-Q3 2026)

#### Relationships
- `PART_OF`: Initiative → Project
- `OWNED_BY`: Initiative → Person (PM or Senior Leader)

#### Test Data File
- `data/layer2_initiatives.json`

#### Validation Queries
```cypher
// List all initiatives with owners
MATCH (i:Initiative)-[:OWNED_BY]->(p:Person)
RETURN i.key, i.summary, p.name, i.status

// Timeline view
MATCH (i:Initiative)
RETURN i.summary, i.created_at, i.due_date
ORDER BY i.due_date
```

---

### 3.3 Layer 3: Jira Epics
**Goal**: Break down initiatives into actionable epics

#### Nodes to Create
- **Epic** (12 total, distributed across 3 initiatives):
  - **Platform Modernization** (4 epics):
    - PLAT-1: "Migrate to Kubernetes"
    - PLAT-2: "Implement Service Mesh"
    - PLAT-3: "Observability Stack Upgrade"
    - PLAT-4: "CI/CD Pipeline Rewrite"
  - **Customer Portal Rebuild** (5 epics):
    - PORT-1: "Authentication & Authorization"
    - PORT-2: "Dashboard UI Components"
    - PORT-3: "API Gateway Layer"
    - PORT-4: "Mobile Responsive Design"
    - PORT-5: "Analytics Integration"
  - **Data Pipeline v2** (3 epics):
    - DATA-1: "Streaming Architecture"
    - DATA-2: "Data Warehouse Migration"
    - DATA-3: "Real-time Analytics Engine"

#### Relationships
- `PART_OF`: Epic → Initiative
- `OWNED_BY`: Epic → Person (epic owner - engineer or PM)
- `RELATES_TO`: Epic → Team (team working on it)

#### Test Data File
- `data/layer3_epics.json`

#### Validation Queries
```cypher
// Epics by initiative
MATCH (e:Epic)-[:PART_OF]->(i:Initiative)
RETURN i.summary, collect(e.key) as epics

// Epic ownership distribution
MATCH (e:Epic)-[:OWNED_BY]->(p:Person)
RETURN p.name, p.role, count(e) as epic_count
ORDER BY epic_count DESC

// Cross-team epics
MATCH (e:Epic)-[:RELATES_TO]->(t:Team)
WITH e, count(t) as team_count
WHERE team_count > 1
RETURN e.key, e.summary, team_count
```

---

### 3.4 Layer 4: Jira Stories & Bugs
**Goal**: Create granular work items with realistic distribution

#### Nodes to Create
- **Issue** (80 total):
  - 60 Stories (distributed across epics)
  - 15 Bugs (some linked to existing stories, some standalone)
  - 5 Tasks (technical debt, spikes)
- **Sprint** (4 sprints - 2 weeks each, covering last 2 months)

#### Distribution Strategy
- Stories: 4-8 stories per epic (varied sizes)
- Story points: Range from 1-13 (fibonacci)
- Bugs: 
  - 5 linked to specific stories (found during testing)
  - 10 production bugs (linked to components)
- Status distribution:
  - 40% Done
  - 25% In Progress
  - 20% To Do
  - 10% In Review
  - 5% Blocked

#### Relationships
- `PART_OF`: Issue → Epic
- `ASSIGNED_TO`: Issue → Person
- `REPORTED_BY`: Issue → Person
- `IN_SPRINT`: Issue → Sprint
- `BLOCKS`: Issue → Issue (dependencies)
- `DEPENDS_ON`: Issue → Issue
- `RELATES_TO`: Bug → Story (bug found in story)
- `PARENT_OF`: Story → Bug (for sub-tasks)

#### Test Data File
- `data/layer4_stories_bugs.json`
- `data/layer4_sprints.json`

#### Validation Queries
```cypher
// Sprint burndown data
MATCH (s:Sprint)<-[:IN_SPRINT]-(i:Issue)
RETURN s.name, 
       sum(i.story_points) as total_points,
       sum(CASE WHEN i.status = 'Done' THEN i.story_points ELSE 0 END) as completed_points

// Find blocked work
MATCH (i:Issue {status: 'Blocked'})-[:BLOCKS]->(blocked:Issue)
RETURN i.key, i.summary, collect(blocked.key) as blocking

// Bug distribution by team
MATCH (bug:Issue {type: 'Bug'})-[:ASSIGNED_TO]->(p:Person)-[:MEMBER_OF]->(t:Team)
RETURN t.name, count(bug) as bug_count
ORDER BY bug_count DESC

// Unassigned critical issues
MATCH (i:Issue)
WHERE i.priority = 'Critical' AND NOT exists((i)-[:ASSIGNED_TO]->())
RETURN i.key, i.summary, i.status
```

---

### 3.5 Layer 5: Git Repositories
**Goal**: Create repository structure aligned with teams and work

#### Nodes to Create
- **Repository** (8 repos):
  - `platform/k8s-infrastructure` (Platform Team)
  - `platform/service-mesh` (Platform Team)
  - `api/gateway` (API Team)
  - `api/user-service` (API Team)
  - `api/order-service` (API Team)
  - `frontend/web-app` (Frontend Team)
  - `mobile/ios-app` (Mobile Team)
  - `data/streaming-pipeline` (Data Team)

#### Relationships
- `OWNED_BY`: Repository → Team
- `MAINTAINED_BY`: Repository → Person (tech leads)
- `RELATES_TO`: Epic → Repository (many-to-many)

#### Test Data File
- `data/layer5_repositories.json`

#### Validation Queries
```cypher
// Repository ownership
MATCH (r:Repository)-[:OWNED_BY]->(t:Team)
RETURN r.name, t.name

// Epics mapped to repos
MATCH (e:Epic)-[:RELATES_TO]->(r:Repository)
RETURN e.key, e.summary, collect(r.name) as repositories

// Repos without owners (should be none)
MATCH (r:Repository)
WHERE NOT exists((r)-[:OWNED_BY]->())
RETURN r.name
```

---

### 3.6 Layer 6: Git Branches
**Goal**: Create realistic branching patterns

#### Nodes to Create
- **Branch** (~40 branches total):
  - 1 `main` branch per repo (8 default branches)
  - ~4 feature branches per repo (32 branches)
    - Pattern: `feature/EPIC-123-description`
    - Pattern: `bugfix/BUG-456-description`
    - Some long-lived, some merged
  
#### Branch Naming Strategy
- Feature branches linked to Jira keys
- Mix of active and merged branches
- Some stale branches (last commit > 30 days)

#### Relationships
- `BRANCH_OF`: Branch → Repository
- `MERGED_TO`: Branch → Branch (feature → main)
- `CREATED_BY`: Branch → Person

#### Test Data File
- `data/layer6_branches.json`

#### Validation Queries
```cypher
// Active branches per repo
MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
WHERE b.is_default = false
RETURN r.name, count(b) as branch_count
ORDER BY branch_count DESC

// Stale branches (simulation will mark some)
MATCH (b:Branch)
WHERE b.last_commit_timestamp < datetime() - duration({days: 30})
  AND b.is_default = false
RETURN b.name, b.last_commit_timestamp, duration.between(b.last_commit_timestamp, datetime()).days as days_old
ORDER BY days_old DESC

// Branches linked to Jira
MATCH (b:Branch)
WHERE b.name CONTAINS 'PLAT-' OR b.name CONTAINS 'PORT-' OR b.name CONTAINS 'DATA-'
RETURN b.name, 
       substring(b.name, 8, 7) as jira_key
```

---

### 3.7 Layer 7: Git Commits (Final Layer)
**Goal**: Create realistic commit history with relationships to people and work items

#### Nodes to Create
- **Commit** (~500 commits over 3 months):
  - Distribution: ~60 commits per week
  - Varied commit sizes (small fixes to large features)
  - Mix of merge commits and regular commits
  
#### Commit Patterns to Simulate
- **By Team**:
  - Platform: 100 commits (infrastructure, config-heavy)
  - API: 150 commits (most active, 3 services)
  - Frontend: 120 commits (rapid UI iterations)
  - Mobile: 80 commits (careful releases)
  - Data: 50 commits (large, complex changes)

- **By Time**:
  - Sprint 1 (Dec 9-20, 2025): 100 commits
  - Sprint 2 (Dec 23-Jan 3): 80 commits (holidays)
  - Sprint 3 (Jan 6-17): 130 commits (back to work)
  - Sprint 4 (Jan 20-31): 140 commits (sprint end push)
  - Recent week: 50 commits

- **By Author**:
  - Top 10 contributors: 60% of commits
  - Middle 30 contributors: 35% of commits
  - Remaining 17: 5% of commits
  - Managers: Occasional commits (5 total)

#### Commit Message Patterns
- Good messages: `[PLAT-1] Add k8s deployment configs for auth service`
- Bug fixes: `Fix memory leak in user service (BUG-234)`
- No reference: `Update README` (20% of commits)
- Merge commits: `Merge pull request #42 from feature/PORT-3-api-gateway`

#### Relationships
- `PART_OF`: Commit → Branch
- `AUTHORED_BY`: Commit → Person
- `COMMITTED_BY`: Commit → Person (usually same as author)
- `PARENT`: Commit → Commit (git history)
- `MODIFIES`: Commit → File (we'll create File nodes for key files)
- `REFERENCES`: Commit → Issue (extracted from message)

#### File Simulation
Create ~50 key files across repos to track:
- High churn files (modified frequently)
- Files touched by many authors
- Files linked to bugs
- Stable files (rarely changed)

#### Test Data Files
- `data/layer7_commits.json`
- `data/layer7_files.json`

#### Validation Queries
```cypher
// Top contributors
MATCH (p:Person)<-[:AUTHORED_BY]-(c:Commit)
RETURN p.name, p.title, count(c) as commit_count
ORDER BY commit_count DESC
LIMIT 10

// Commits by week
MATCH (c:Commit)
WHERE c.timestamp >= datetime() - duration({days: 90})
WITH c, duration.inWeeks(datetime(), c.timestamp) as weeks_ago
RETURN weeks_ago, count(c) as commits
ORDER BY weeks_ago DESC

// Commits linked to Jira
MATCH (c:Commit)-[:REFERENCES]->(i:Issue)
RETURN i.type, count(c) as linked_commits

// Find hotspot files (high churn + many authors)
MATCH (f:File)<-[:MODIFIES]-(c:Commit)-[:AUTHORED_BY]->(p:Person)
WHERE c.timestamp >= datetime() - duration({days: 60})
RETURN f.path, 
       count(DISTINCT c) as commit_count,
       count(DISTINCT p) as author_count,
       f.language
ORDER BY commit_count DESC, author_count DESC
LIMIT 10

// Feature branch completion
MATCH (b:Branch)-[:BRANCH_OF]->(r:Repository)
MATCH (b)<-[:PART_OF]-(c:Commit)
WHERE b.name STARTS WITH 'feature/'
RETURN b.name, 
       r.name,
       count(c) as commits,
       max(c.timestamp) as last_commit
ORDER BY last_commit DESC

// Cross-reference: Stories completed but no commits
MATCH (story:Issue {type: 'Story', status: 'Done'})
WHERE NOT exists((story)<-[:REFERENCES]-(:Commit))
RETURN story.key, story.summary

// Identify code review patterns
MATCH (c:Commit)-[:AUTHORED_BY]->(author:Person)
MATCH (c)-[:COMMITTED_BY]->(committer:Person)
WHERE author <> committer
RETURN author.name as author, 
       committer.name as committer, 
       count(c) as commits
ORDER BY commits DESC
```

---

## 4. Implementation Plan

### 4.1 Tools & Scripts

#### Data Generation Scripts
```
scripts/
├── generate_layer1_people_teams.py
├── generate_layer2_initiatives.py
├── generate_layer3_epics.py
├── generate_layer4_stories_bugs.py
├── generate_layer5_repositories.py
├── generate_layer6_branches.py
├── generate_layer7_commits.py
└── utils/
    ├── faker_helpers.py      # Name, date generation
    ├── jira_key_generator.py # Realistic Jira keys
    └── git_helpers.py        # Commit messages, SHAs
```

#### Data Loading Scripts
```
scripts/
├── load_to_neo4j.py         # Generic loader
├── validate_layer.py        # Run validation queries
└── reset_database.py        # Clean slate
```

### 4.2 JSON Schema Design

Each layer will have a consistent JSON structure:

```json
{
  "metadata": {
    "layer": "layer1",
    "description": "People and Teams",
    "generated_at": "2026-01-04T10:00:00Z",
    "schema_version": "1.0"
  },
  "nodes": {
    "Person": [
      {
        "id": "person_001",
        "properties": {
          "name": "Alice Johnson",
          "primary_email": "alice.johnson@company.com",
          "title": "Senior Software Engineer",
          "seniority": "Senior",
          "role": "Engineer",
          "hire_date": "2022-03-15"
        }
      }
    ],
    "Team": [...]
  },
  "relationships": [
    {
      "type": "MEMBER_OF",
      "from": {"node_type": "Person", "id": "person_001"},
      "to": {"node_type": "Team", "id": "team_platform"},
      "properties": {
        "joined_at": "2022-03-15"
      }
    }
  ]
}
```

### 4.3 Development Workflow

#### Week 1: Foundation (Layers 1-2)
- Day 1-2: Setup Neo4j, create Python scripts structure
- Day 3: Generate Layer 1 (People & Teams)
- Day 4: Load Layer 1, validate queries
- Day 5: Generate & load Layer 2 (Initiatives)

#### Week 2: Jira Hierarchy (Layers 3-4)
- Day 1-2: Generate Layer 3 (Epics)
- Day 3: Generate Layer 4 (Stories & Bugs)
- Day 4-5: Load layers, validate cross-references

#### Week 3: Git Structure (Layers 5-6)
- Day 1-2: Generate Layer 5 (Repositories)
- Day 3: Generate Layer 6 (Branches)
- Day 4-5: Link repos/branches to Jira, validate

#### Week 4: Git History & Final Integration (Layer 7)
- Day 1-3: Generate Layer 7 (Commits & Files)
- Day 4: Full integration testing
- Day 5: Run analytical queries, document findings

---

## 5. Validation & Testing Strategy

### 5.1 Per-Layer Validation
After each layer, run:
1. **Schema validation**: All required properties present
2. **Relationship integrity**: All references resolve
3. **Count checks**: Expected number of nodes created
4. **Sample queries**: Spot-check data quality

### 5.2 Cross-Layer Integration Tests
- Jira → Git references (story keys in commits)
- People → Work distribution (commits per person matches activity)
- Time consistency (commits within sprint dates)
- Orphan detection (nodes without required relationships)

### 5.3 Analytical Validation
Run queries from high-level-design.md Section 2.2:
- Critical projects with junior talent
- Code hotspots analysis
- Blocked work identification
- Sprint velocity trends

### 5.4 Performance Testing
- Query response time for common patterns
- Full graph traversal performance
- Index effectiveness
- Memory usage at scale

---

## 6. Realistic Data Patterns

### 6.1 Making It Realistic

#### Work Distribution
- **Pareto Principle**: 20% of people do 80% of work
- **Specialization**: Frontend devs primarily in web-app repo
- **Managers**: Low commit volume, high review volume
- **Junior Engineers**: More bugs assigned, smaller stories

#### Time Patterns
- **Sprint Curves**: Slow start, end-of-sprint rush
- **Holiday Dip**: Lower activity Dec 23-Jan 2
- **Work Hours**: Commits during business hours (with some exceptions)
- **Code Review Lag**: PRs reviewed 1-3 days after creation

#### Jira Patterns
- **Status Transitions**: Realistic flow (To Do → In Progress → In Review → Done)
- **Story Point Accuracy**: Some stories underestimated, some overestimated
- **Scope Creep**: 10% of stories have increased estimates
- **Bug Spike**: More bugs reported after major releases

#### Git Patterns
- **Commit Size**: Mix of small fixes (1-10 lines) and features (100-500 lines)
- **Branch Lifetime**: Features 5-15 days, bugs 1-3 days
- **Merge Frequency**: Main branch gets 3-5 merges per day
- **Commit Messages**: 80% reference Jira, 20% don't

### 6.2 Edge Cases to Include
- **Stale branches**: 5 branches with no commits in 60+ days
- **Unassigned work**: 3 critical bugs with no assignee
- **Cross-team dependencies**: 2 epics blocked by other teams
- **Abandoned features**: 1 epic with no recent activity
- **Hotspot files**: 3 files touched by 10+ developers
- **Lone wolves**: 2 engineers working on isolated features
- **Context switching**: 3 people assigned to 5+ active stories

---

## 7. Success Metrics & Goals

### 7.1 Completion Criteria
- [ ] All 7 layers implemented and loaded
- [ ] Database contains ~700+ nodes
- [ ] Database contains ~2000+ relationships
- [ ] All validation queries pass
- [ ] Can answer 10+ analytical questions
- [ ] Performance: Queries complete in <500ms

### 7.2 Analytical Questions to Answer
Using the simulated data, we should be able to answer:

1. Which epic is most at risk of missing its deadline?
2. Which file is the biggest hotspot (churn + authors + bugs)?
3. Who are the top 5 contributors to the Platform Modernization initiative?
4. What percentage of critical bugs are assigned to junior engineers?
5. Which stories were marked Done but have no associated commits?
6. What is the average time from story creation to first commit?
7. Which team has the highest bug-to-story ratio?
8. Are there any circular dependencies between epics?
9. Which branches are stale and should be cleaned up?
10. What is the team velocity trend over the last 4 sprints?

### 7.3 Documentation Deliverables
- [ ] This simulation plan (this document)
- [ ] Data generation scripts with inline documentation
- [ ] Sample JSON files for each layer
- [ ] Neo4j query cookbook (useful queries)
- [ ] Findings document (design gaps, insights)
- [ ] Demo script for stakeholder presentations

---

## 8. Next Steps After Simulation

### 8.1 Design Refinements
Based on simulation learnings:
- Identify missing relationships
- Add/remove node properties
- Optimize for common query patterns
- Document performance considerations

### 8.2 Visibility Layer Design
- Dashboard wireframes
- Key metrics to surface
- Alert triggers (e.g., hotspots, blocked work)
- Drill-down navigation paths

### 8.3 Real Data Integration Planning
- API authentication requirements
- Rate limiting strategies
- Incremental sync vs full refresh
- Identity resolution testing with real data

---

## 9. Risk Mitigation

### 9.1 Potential Issues

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Data generation takes longer than expected | Timeline slip | Start with smaller dataset, parallelize scripts |
| Neo4j performance issues | Can't validate at scale | Use proper indexes, optimize queries early |
| Unrealistic data patterns | Invalid conclusions | Review with domain experts, iterate |
| Scope creep (too complex) | Never finish | Stick to 7 layers, defer enhancements |

### 9.2 Contingency Plans
- **If behind schedule**: Skip Layer 6 (branches), link commits directly to repos
- **If data quality low**: Regenerate specific layers, don't start over
- **If queries too slow**: Focus on schema optimization before adding more data

---

## 10. Appendices

### 10.1 Example Data Snippet (Layer 1)

```json
{
  "metadata": {
    "layer": "layer1",
    "description": "People and Teams"
  },
  "nodes": {
    "Person": [
      {
        "id": "person_001",
        "properties": {
          "name": "Alice Johnson",
          "primary_email": "alice.johnson@company.com",
          "github_username": "alicejohnson",
          "jira_username": "alice.johnson",
          "title": "Senior Software Engineer",
          "seniority": "Senior",
          "role": "Engineer",
          "type": "Employee",
          "hire_date": "2022-03-15",
          "skills": ["Python", "Go", "Kubernetes", "PostgreSQL"],
          "timezone": "America/New_York"
        }
      }
    ],
    "Team": [
      {
        "id": "team_platform",
        "properties": {
          "name": "Platform Team",
          "type": "Engineering",
          "mission": "Build and maintain infrastructure and developer tools"
        }
      }
    ]
  },
  "relationships": [
    {
      "type": "MEMBER_OF",
      "from": {"node_type": "Person", "id": "person_001"},
      "to": {"node_type": "Team", "id": "team_platform"}
    }
  ]
}
```

### 10.2 Quick Start Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install neo4j faker

# Generate all layers
python scripts/generate_all_layers.py

# Load to Neo4j
python scripts/load_to_neo4j.py --layer all

# Validate
python scripts/validate_layer.py --layer all

# Reset database (if needed)
python scripts/reset_database.py --confirm
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-04 | Copilot | Initial simulation plan |

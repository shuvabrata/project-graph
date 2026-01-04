# Project Graph Database - High Level Design

**Version**: 0.1  
**Last Updated**: January 4, 2026  
**Status**: Design Phase

---

## 1. Vision & Problem Statement

### 1.1 Vision
Build a graph-based analytics platform that surfaces hidden data points from enterprise systems (GitHub, Jira, Confluence, Org Structure, Cloud Infrastructure) to enable data-driven decision making for technical leaders, moving beyond gut-feel and experience.

### 1.2 Core Problem
Technical leaders today lack visibility into:
- Alignment between business plans and actual progress
- Resource allocation efficiency (are top talents on critical projects?)
- Impact of changing priorities
- Team efficiency metrics
- People manager focus areas
- Skill set gaps
- Hotspots and abnormal patterns across artifacts

### 1.3 Key Principles
1. **Comprehensive Capture**: Everything matters - more variables = more analytical potential
2. **Historical Context**: Time-series data essential for trend analysis and pattern detection
3. **Relationship-First**: Connections between entities reveal hidden insights
4. **Incremental Implementation**: Complete model definition, phased implementation
5. **Hotspot Detection**: Unexpected changes indicate risk or high-value areas

---

## 2. Use Cases & Analytics Goals

### 2.1 Strategic Questions (To Be Answered)

#### Resource & Talent Alignment
- Are top performers working on critical projects?
- Which teams/people are bottlenecks?
- Skill coverage: who can work on what?
- Skill gaps: what capabilities are missing?

#### Progress & Alignment
- Does business plan match ground reality?
- Which epics/initiatives are blocked or at risk?
- Dependency chains: what's the critical path?

#### Change & Efficiency
- How do teams adapt to changing priorities?
- What's the true cost of context switching?
- Team velocity trends over time
- Code ownership patterns and fragmentation

#### Risk & Quality
- Which components are hotspots? (high churn, many authors, frequent bugs)
- Cross-team dependencies creating risk?
- Where are people managers spending time? (meetings, reviews, incidents)

### 2.2 Example Analytical Queries
```cypher
// Find critical projects with junior talent assigned
MATCH (proj:Project)-[:HAS_EPIC]->(epic:Epic)-[:HAS_ISSUE]->(issue:Issue)
MATCH (issue)-[:ASSIGNED_TO]->(person:Person)
WHERE proj.priority = 'Critical' AND person.seniority = 'Junior'
RETURN proj, count(issue) as junior_assigned_count

// Identify code hotspots: high churn + many authors + bug fixes
MATCH (file:File)-[:HAS_COMMIT]->(commit:Commit)
MATCH (commit)-[:AUTHORED_BY]->(author:Person)
MATCH (commit)-[:REFERENCES]->(issue:Issue {type: 'Bug'})
WHERE commit.timestamp > date('2025-10-01')
RETURN file.path, 
       count(DISTINCT commit) as commit_count,
       count(DISTINCT author) as author_count,
       count(DISTINCT issue) as bug_count
ORDER BY commit_count DESC, author_count DESC
```

---

## 3. Graph Model Design

### 3.1 Node Types

#### 3.1.1 Source Control (GitHub/GitLab)

**Repository**
```yaml
Properties:
  - id: string (unique)
  - name: string
  - full_name: string (org/repo)
  - url: string
  - language: string (primary)
  - is_private: boolean
  - created_at: timestamp
  - archived: boolean
  - topics: string[] (tags)
  
Relationships:
  - OWNED_BY → Team
  - MAINTAINED_BY → Person
  - CONTAINS → Directory/File
  - DEPLOYS_TO → Service/Deployment
```

**Branch**
```yaml
Properties:
  - id: string
  - name: string
  - is_default: boolean
  - is_protected: boolean
  - last_commit_sha: string
  - created_at: timestamp
  
Relationships:
  - BRANCH_OF → Repository
  - HAS_COMMIT → Commit
  - MERGED_TO → Branch
```

**Commit**
```yaml
Properties:
  - sha: string (unique)
  - message: string
  - timestamp: timestamp
  - additions: int
  - deletions: int
  - files_changed: int
  - is_merge: boolean
  
Relationships:
  - AUTHORED_BY → Person
  - COMMITTED_BY → Person (can differ from author)
  - PARENT → Commit (for commit history)
  - MODIFIES → File
  - PART_OF → Branch
  - REFERENCES → Issue (extracted from commit message)
  - REVIEWED_IN → PullRequest
```

**PullRequest**
```yaml
Properties:
  - id: string
  - number: int
  - title: string
  - state: string (open/closed/merged)
  - created_at: timestamp
  - closed_at: timestamp
  - merged_at: timestamp
  - additions: int
  - deletions: int
  - changed_files: int
  - draft: boolean
  
Relationships:
  - CREATED_BY → Person
  - TARGETS → Branch (base branch)
  - FROM → Branch (head branch)
  - HAS_COMMIT → Commit
  - REVIEWED_BY → Person (with approval/changes/comment property)
  - REFERENCES → Issue
  - PART_OF → Repository
```

**File**
```yaml
Properties:
  - id: string
  - path: string
  - name: string
  - extension: string
  - size: int (bytes)
  - language: string
  - first_seen: timestamp
  - last_modified: timestamp
  - is_deleted: boolean
  
Relationships:
  - IN_DIRECTORY → Directory
  - IN_REPOSITORY → Repository
  - HAS_COMMIT → Commit (history)
  - MODIFIED_BY → Person (aggregated)
  - REFERENCED_BY → Issue (if file mentioned in issue)
```

**Directory**
```yaml
Properties:
  - path: string
  - name: string
  
Relationships:
  - IN_REPOSITORY → Repository
  - PARENT → Directory
  - CONTAINS → File/Directory
```

#### 3.1.2 Issue Tracking (Jira)

**Epic**
```yaml
Properties:
  - id: string (Jira key)
  - key: string
  - summary: string
  - description: string
  - status: string
  - priority: string
  - created_at: timestamp
  - updated_at: timestamp
  - resolved_at: timestamp
  - due_date: date
  - labels: string[]
  
Relationships:
  - OWNED_BY → Person (Epic owner)
  - PART_OF → Project
  - HAS_ISSUE → Story/Task/Bug
  - BLOCKS → Epic
  - DEPENDS_ON → Epic
  - RELATES_TO → Repository/Service
```

**Issue** (Story, Task, Bug, Subtask)
```yaml
Properties:
  - id: string
  - key: string
  - type: string (Story/Bug/Task/Subtask)
  - summary: string
  - description: string
  - status: string
  - priority: string
  - story_points: int
  - created_at: timestamp
  - updated_at: timestamp
  - resolved_at: timestamp
  - due_date: date
  - labels: string[]
  - components: string[]
  
Relationships:
  - ASSIGNED_TO → Person
  - REPORTED_BY → Person
  - PART_OF → Epic
  - IN_SPRINT → Sprint
  - BLOCKS → Issue
  - DEPENDS_ON → Issue
  - RELATES_TO → Issue
  - PARENT_OF → Issue (for subtasks)
  - FIXED_IN → Commit/PullRequest
  - RELATES_TO → Repository/Service/File
  - COMMENTED_BY → Person (with timestamp)
  - TRANSITIONED_BY → Person (status changes, with timestamp)
```

**Sprint**
```yaml
Properties:
  - id: string
  - name: string
  - start_date: date
  - end_date: date
  - state: string (active/closed/future)
  - goal: string
  - committed_points: int
  - completed_points: int
  
Relationships:
  - PART_OF → Board
  - HAS_ISSUE → Issue
  - ASSIGNED_TO → Team
```

**Project** (Jira Project)
```yaml
Properties:
  - id: string
  - key: string
  - name: string
  - type: string
  - priority: string (Critical/High/Medium/Low)
  - created_at: timestamp
  
Relationships:
  - OWNED_BY → Team/Person
  - HAS_EPIC → Epic
  - HAS_BOARD → Board
  - RELATES_TO → Repository (many-to-many)
```

**Board**
```yaml
Properties:
  - id: string
  - name: string
  - type: string (scrum/kanban)
  
Relationships:
  - PART_OF → Project
  - HAS_SPRINT → Sprint
  - USED_BY → Team
```

#### 3.1.3 People & Organization

**Person**
```yaml
Properties:
  - id: string (master_person_id - unique across systems)
  - name: string
  - primary_email: string
  - all_emails: string[] (all known emails)
  - github_username: string
  - jira_username: string
  - confluence_username: string
  - title: string
  - seniority: string (Junior/Mid/Senior/Staff/Principal)
  - role: string (Engineer/Manager/PM/Designer)
  - type: string (Employee/Contractor/External/Bot)
  - hire_date: date
  - skills: string[] (programming languages, domains)
  - location: string
  - timezone: string
  - identity_verified: boolean
  - created_at: timestamp
  - updated_at: timestamp
  
Relationships:
  - MEMBER_OF → Team
  - REPORTS_TO → Person (manager)
  - MANAGES → Team/Person
  - AUTHORED → Commit
  - CREATED → PullRequest/Issue
  - REVIEWED → PullRequest
  - ASSIGNED_TO → Issue
  - OWNS → Repository/Service
  - PARTICIPATED_IN → Meeting
  - CONTRIBUTED_TO → Document (Confluence)
  - HAS_IDENTITY → IdentityMapping (links to external systems)
```

**IdentityMapping**
```yaml
Properties:
  - id: string
  - system: string (github/jira/confluence/aws/azure)
  - external_id: string
  - external_username: string
  - external_email: string
  - match_method: string (email/manual/fuzzy)
  - match_confidence: float (0.0-1.0)
  - verified: boolean
  - created_at: timestamp
  - verified_at: timestamp
  - verified_by: string
  
Relationships:
  - MAPS_TO → Person (master identity)
  - VERIFIED_BY → Person (admin who verified)
```

**Team**
```yaml
Properties:
  - id: string
  - name: string
  - type: string (Engineering/ProductManagement/Design/etc)
  - mission: string
  - created_at: timestamp
  
Relationships:
  - PART_OF → Organization/Department
  - LED_BY → Person (team lead/manager)
  - HAS_MEMBER → Person
  - OWNS → Repository/Service
  - WORKS_ON → Project/Epic
  - USES_BOARD → Board
```

**Organization/Department**
```yaml
Properties:
  - id: string
  - name: string
  - level: string (Department/Division/BU)
  
Relationships:
  - PARENT_OF → Organization/Team
  - LED_BY → Person (VP/Director)
```

#### 3.1.4 Documentation (Confluence) - Future Phase

**Space**
```yaml
Properties:
  - id: string
  - key: string
  - name: string
  - type: string
  
Relationships:
  - OWNED_BY → Team
```

**Page**
```yaml
Properties:
  - id: string
  - title: string
  - content: string
  - created_at: timestamp
  - updated_at: timestamp
  - version: int
  
Relationships:
  - IN_SPACE → Space
  - CREATED_BY → Person
  - LAST_MODIFIED_BY → Person
  - PARENT_PAGE → Page
  - RELATES_TO → Project/Repository/Service
  - REFERENCES → Issue
```

#### 3.1.5 Infrastructure & Deployments (AWS/Azure) - Future Phase

**Service**
```yaml
Properties:
  - id: string
  - name: string
  - type: string (API/Web/Database/Queue/etc)
  - description: string
  - criticality: string (P0/P1/P2/P3)
  
Relationships:
  - DEPLOYED_FROM → Repository
  - OWNED_BY → Team
  - DEPENDS_ON → Service
  - RUNS_IN → Environment
  - HOSTED_ON → Infrastructure
```

**Deployment**
```yaml
Properties:
  - id: string
  - version: string
  - commit_sha: string
  - deployed_at: timestamp
  - deployed_by: string
  - status: string (success/failed/rollback)
  
Relationships:
  - OF_SERVICE → Service
  - TO_ENVIRONMENT → Environment
  - FROM_COMMIT → Commit
  - TRIGGERED_BY → PullRequest/Person
  - FIXES → Issue (if deployment fixes issues)
```

**Environment**
```yaml
Properties:
  - id: string
  - name: string (dev/staging/prod)
  - region: string
  
Relationships:
  - HOSTS → Service
  - PART_OF → Account
```

**Infrastructure** (EC2, Lambda, RDS, etc.)
```yaml
Properties:
  - id: string (resource id)
  - type: string
  - name: string
  - tags: map
  
Relationships:
  - HOSTS → Service
  - IN_ENVIRONMENT → Environment
  - OWNED_BY → Team
```

### 3.2 Temporal Model & History

**Design Decision**: How to handle time-series data?

#### Option A: Event Sourcing
- Store every state change as an event node
- Pros: Complete audit trail, point-in-time queries
- Cons: Large graph, complex queries

#### Option B: Temporal Properties
- Add versioned properties (status_history, assignee_history)
- Pros: Simpler model
- Cons: Limited query capability

#### Option C: Snapshot Nodes
- Create periodic snapshot nodes for key entities
- Pros: Balance between detail and complexity
- Cons: Lossy between snapshots

**Recommendation**: Hybrid approach
- Use temporal properties for lightweight tracking
- Create Event nodes for significant changes
- Periodic snapshots for complex entities

**Event Node** (for significant changes)
```yaml
Properties:
  - id: string
  - type: string (IssueTransitioned, CommitCreated, PRReviewed, etc.)
  - timestamp: timestamp
  - actor: string (person who triggered)
  - metadata: map (change details)
  
Relationships:
  - HAPPENED_TO → (any node)
  - PERFORMED_BY → Person
  - PREVIOUS_EVENT → Event (linked list)
```

---

## 4. Open Questions & Design Decisions

### 4.1 Identity Resolution
**Question**: How to unify identities across systems?
- GitHub user != Jira user != Confluence user
- Need mapping table or heuristics (email matching?)

**Solution**: Master Identity Table with Hybrid Matching

The application will maintain a master identity table that merges IDs from different systems into a single row for each unique identity.

**Three-Phase Approach**:

1. **Automatic Email Matching**
   - Primary strategy: Match users across systems by email address
   - Email is the canonical identifier when available
   - Handles ~80-90% of cases automatically

2. **Fuzzy Matching with Suggestions**
   - For unmatched identities, apply fuzzy matching on:
     - Name similarity (Levenshtein distance)
     - Username patterns (e.g., john.smith vs jsmith)
     - Domain context (same organization)
   - Present suggestions to end users for review
   - Confidence score threshold (e.g., >0.85 for auto-merge, 0.6-0.85 for suggestions)

3. **Manual Mapping**
   - Admin interface for manual identity linking
   - Override automatic matches if incorrect
   - Handle edge cases (contractors, name changes, duplicate accounts)
   - Audit trail for manual changes

**Implementation Details**:

```yaml
IdentityMapping Node:
  Properties:
    - master_id: string (canonical person ID)
    - system: string (github/jira/confluence/aws)
    - external_id: string (ID in external system)
    - external_username: string
    - external_email: string
    - match_method: string (email/manual/fuzzy)
    - match_confidence: float (0.0-1.0)
    - verified: boolean
    - created_at: timestamp
    - verified_at: timestamp
    - verified_by: string (admin user)
  
  Relationships:
    - MAPS_TO → Person (master identity)
```

**Workflow**:
1. Data ingestion extracts user info from each system
2. Identity resolver attempts email matching first
3. Unmatched identities go through fuzzy matching
4. High-confidence matches (>0.85) auto-link with review flag
5. Medium-confidence matches (0.6-0.85) queued for user approval
6. Low-confidence matches (<0.6) remain unlinked until manual review
7. Periodic review dashboard shows pending matches

**Edge Cases**:
- **No email available**: Use fuzzy matching + manual fallback
- **Multiple emails**: Link all emails to same master identity
- **Name changes**: Keep history, link to same master_id
- **Contractors/External**: Mark as external in Person.type
- **Bots/Service accounts**: Separate handling, exclude from analytics

**Database Schema** (supporting table):
```sql
CREATE TABLE identity_mappings (
  id UUID PRIMARY KEY,
  master_person_id UUID NOT NULL,
  system VARCHAR(50) NOT NULL,
  external_id VARCHAR(255) NOT NULL,
  external_username VARCHAR(255),
  external_email VARCHAR(255),
  match_method VARCHAR(20) NOT NULL, -- email, manual, fuzzy
  match_confidence DECIMAL(3,2),
  verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL,
  verified_at TIMESTAMP,
  verified_by VARCHAR(255),
  UNIQUE(system, external_id)
);
```

### 4.2 Data Freshness
**Question**: Real-time vs batch updates?
- Real-time: Webhooks from GitHub/Jira
- Batch: Periodic polling (easier to start)
- **Recommendation**: Start with batch (hourly/daily), add webhooks later

### 4.3 Graph Database Selection
**Question**: Which graph database?
- Neo4j: Industry standard, great for analytics
- Amazon Neptune: If AWS-native desired
- ArangoDB: Multi-model flexibility
- **TODO**: Evaluate based on query patterns and scale

### 4.4 Schema Evolution
**Question**: How to handle schema changes?
- Nodes/relationships will evolve
- Need migration strategy
- **TODO**: Document versioning approach

### 4.5 Data Volume Estimation
**Question**: What scale are we targeting?
- Typical enterprise: 100s of repos, 1000s of people, 100Ks of commits
- Need to estimate node/edge counts
- **TODO**: Calculate expected graph size

### 4.6 Privacy & Security
**Question**: What data should NOT be stored?
- Sensitive code content
- Personal information beyond work profile
- Private messages/comments?
- **TODO**: Define data retention and privacy policy

### 4.7 Deleted Entities
**Question**: How to handle deletions?
- Soft delete (is_deleted flag) vs hard delete
- Important for historical queries
- **Recommendation**: Soft delete for critical entities

### 4.8 Computed Metrics
**Question**: Store metrics in graph or compute on-demand?
- Examples: code churn, velocity, centrality scores
- Pre-compute: Faster queries, staleness risk
- On-demand: Always fresh, slower
- **Recommendation**: Pre-compute and cache hot metrics

---

## 5. Implementation Phases

### Phase 0: Foundation (Current)
- [ ] Complete design document
- [ ] Choose graph database
- [ ] Set up development environment
- [ ] Design data ingestion architecture

### Phase 1: MVP - GitHub + Jira Core
**Nodes**: Repository, Commit, Person, Issue, Team
**Relationships**: Basic ownership and authorship
**Goal**: Answer "Who works on what?"

### Phase 2: Detailed Git History
**Nodes**: File, Directory, Branch, PullRequest
**Relationships**: Complete code change tracking
**Goal**: Identify code hotspots

### Phase 3: Jira Deep Integration
**Nodes**: Epic, Sprint, Board, Project
**Relationships**: Sprint planning, dependency tracking
**Goal**: Progress and velocity tracking

### Phase 4: People & Org Structure
**Nodes**: Organization, Department, enhanced Person
**Relationships**: Reporting structure, team composition
**Goal**: Resource allocation analysis

### Phase 5: Confluence Integration
**Nodes**: Space, Page
**Relationships**: Documentation coverage
**Goal**: Knowledge management insights

### Phase 6: Infrastructure & Deployments
**Nodes**: Service, Deployment, Environment, Infrastructure
**Relationships**: Deploy lineage
**Goal**: Change impact analysis

### Phase 7: Analytics & ML
- Hotspot detection algorithms
- Anomaly detection
- Predictive analytics
- Recommendation engine

---

## 6. Key Algorithms & Analytics (Future Design)

### 6.1 Hotspot Detection
**Inputs**: Commit history, bug frequency, author diversity
**Outputs**: Risk score per file/component

### 6.2 Talent-Project Matching
**Inputs**: Person skills, project requirements, current allocation
**Outputs**: Optimal assignment recommendations

### 6.3 Critical Path Analysis
**Inputs**: Issue dependencies, team capacity
**Outputs**: Bottlenecks and at-risk deliverables

### 6.4 Knowledge Silos
**Inputs**: Code ownership concentration
**Outputs**: Bus factor, knowledge transfer needs

---

## 7. Technical Architecture (To Be Detailed)

### 7.1 Components
```
┌─────────────────────────────────────────────┐
│           Data Sources                       │
│  GitHub | Jira | Confluence | AWS | Azure   │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Data Extractors (ETL)                │
│  - API Clients                               │
│  - Webhooks                                  │
│  - Change Detection                          │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│      Transformation & Enrichment             │
│  - Identity Resolution                       │
│  - Relationship Inference                    │
│  - Metric Computation                        │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│           Graph Database                     │
│  - Node/Edge Storage                         │
│  - Query Engine                              │
│  - Temporal Support                          │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│        Analytics & Query Layer               │
│  - Pre-computed Metrics                      │
│  - Graph Algorithms                          │
│  - Query API                                 │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Visualization & UI                   │
│  - Dashboards                                │
│  - Graph Explorer                            │
│  - Reports                                   │
└─────────────────────────────────────────────┘
```

### 7.2 Technology Stack (To Be Decided)
- **Graph DB**: Neo4j / Neptune / ArangoDB
- **ETL**: Python (GitHub API, Jira API, Confluence API)
- **Analytics**: Python (NetworkX, Graph algorithms)
- **API**: FastAPI / GraphQL
- **UI**: React + D3.js / Grafana
- **Deployment**: Docker / Kubernetes

---

## 8. Next Steps & Research Items

### For Offline Research
1. **Graph Database Evaluation**
   - Compare Neo4j, Neptune, ArangoDB for your use case
   - Consider managed vs self-hosted
   - Licensing costs vs effort

2. **Identity Resolution Strategies**
   - Survey approaches for cross-system identity matching
   - Design schema for identity mapping

3. **Data Extraction Patterns**
   - GitHub API rate limits and pagination
   - Jira REST vs GraphQL APIs
   - Incremental vs full sync strategies

4. **Temporal Modeling Best Practices**
   - Research event sourcing in graph databases
   - Neo4j temporal query patterns

5. **Sample Queries**
   - Write 10-20 example Cypher queries
   - Validate graph model supports key analytics

6. **Privacy & Compliance**
   - GDPR considerations for people data
   - Data retention policies

### Questions to Answer Next Session
1. Do we want to track individual file changes or just commit-level?
2. Should PR reviews be weighted (approved vs commented)?
3. How to model "team changes" over time (people joining/leaving)?
4. What's the minimum viable schema for Phase 1?

---

## 9. Appendix

### 9.1 Glossary
- **Hotspot**: Code area with high churn, many authors, or frequent bugs
- **Bus Factor**: Number of people who can be "hit by a bus" before project fails
- **Velocity**: Story points completed per sprint
- **Centrality**: Graph measure of node importance

### 9.2 References
- Neo4j Graph Data Modeling Guidelines
- GitHub API Documentation
- Jira REST API Documentation
- Graph Database Design Patterns

---

**Document Status**: Active design phase - expect daily updates
**Next Review**: Add detailed Phase 1 implementation plan

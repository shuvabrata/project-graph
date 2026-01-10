# project-graph

A Neo4j graph database project with a simple movie database example.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14 or higher (for running the example)

## Quick Start

### 1. Start Neo4j with Docker

Start the Neo4j database using Docker Compose:

```bash
docker compose up -d
```

This will:
- Pull the Neo4j Community Edition image (version 5.26)
- Start Neo4j on ports 7474 (HTTP) and 7687 (Bolt)
- Set default credentials: username `neo4j`, password `password123`

### 2. Access Neo4j Browser

Open your web browser and navigate to:
```
http://localhost:7474
```

Login with:
- **Username**: `neo4j`
- **Password**: `**********`

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install neo4j
```


### Changing the Password

Edit the `NEO4J_AUTH` environment variable in [docker-compose.yml](docker-compose.yml):
```yaml
- NEO4J_AUTH=neo4j/your_new_password
```

Then update the password in [example.py](example.py):
```python
PASSWORD = "your_new_password"
```

## Useful Docker Commands

```bash
# Start Neo4j
docker compose up -d

# Stop Neo4j
docker compose down

# View logs
docker compose logs -f neo4j

# Stop and remove all data
docker compose down -v

# Restart Neo4j
docker compose restart
```

## Learn More

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Python Driver](https://neo4j.com/docs/api/python-driver/current/)
- [Graph Database Concepts](https://neo4j.com/docs/getting-started/current/graphdb-concepts/)

## License

See [LICENSE](LICENSE) file for details.

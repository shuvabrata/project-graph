"""
Simple Neo4j Example: Movie Database
This example demonstrates basic CRUD operations with Neo4j.
"""

from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MovieDatabase:
    def __init__(self, uri, user, password):
        """Initialize connection to Neo4j database"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close the database connection"""
        self.driver.close()
    
    def create_movie(self, title, released, tagline):
        """Create a movie node"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_movie_tx, title, released, tagline
            )
            logger.info(f"Created movie: {title}")
            return result
    
    @staticmethod
    def _create_movie_tx(tx, title, released, tagline):
        query = """
        CREATE (m:Movie {title: $title, released: $released, tagline: $tagline})
        RETURN m
        """
        result = tx.run(query, title=title, released=released, tagline=tagline)
        return result.single()[0]
    
    def create_person(self, name, born):
        """Create a person node"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_person_tx, name, born
            )
            logger.info(f"Created person: {name}")
            return result
    
    @staticmethod
    def _create_person_tx(tx, name, born):
        query = """
        CREATE (p:Person {name: $name, born: $born})
        RETURN p
        """
        result = tx.run(query, name=name, born=born)
        return result.single()[0]
    
    def create_acted_in_relationship(self, person_name, movie_title, roles):
        """Create ACTED_IN relationship between person and movie"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_acted_in_tx, person_name, movie_title, roles
            )
            logger.info(f"{person_name} acted in {movie_title}")
            return result
    
    @staticmethod
    def _create_acted_in_tx(tx, person_name, movie_title, roles):
        query = """
        MATCH (p:Person {name: $person_name})
        MATCH (m:Movie {title: $movie_title})
        CREATE (p)-[r:ACTED_IN {roles: $roles}]->(m)
        RETURN p, r, m
        """
        result = tx.run(query, person_name=person_name, movie_title=movie_title, roles=roles)
        return result.single()
    
    def find_all_movies(self):
        """Retrieve all movies"""
        with self.driver.session() as session:
            result = session.execute_read(self._find_all_movies_tx)
            return result
    
    @staticmethod
    def _find_all_movies_tx(tx):
        query = "MATCH (m:Movie) RETURN m.title AS title, m.released AS released"
        result = tx.run(query)
        return [{"title": record["title"], "released": record["released"]} 
                for record in result]
    
    def find_actors_in_movie(self, movie_title):
        """Find all actors in a specific movie"""
        with self.driver.session() as session:
            result = session.execute_read(
                self._find_actors_in_movie_tx, movie_title
            )
            return result
    
    @staticmethod
    def _find_actors_in_movie_tx(tx, movie_title):
        query = """
        MATCH (p:Person)-[r:ACTED_IN]->(m:Movie {title: $movie_title})
        RETURN p.name AS actor, r.roles AS roles
        """
        result = tx.run(query, movie_title=movie_title)
        return [{"actor": record["actor"], "roles": record["roles"]} 
                for record in result]
    
    def delete_all(self):
        """Delete all nodes and relationships (use with caution!)"""
        with self.driver.session() as session:
            session.execute_write(self._delete_all_tx)
            logger.info("Deleted all nodes and relationships")
    
    @staticmethod
    def _delete_all_tx(tx):
        query = "MATCH (n) DETACH DELETE n"
        tx.run(query)


def main():
    """Main function demonstrating Neo4j operations"""
    
    # Connection parameters
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = "password123"
    
    # Create database instance
    db = MovieDatabase(URI, USER, PASSWORD)
    
    try:
        # Clean slate
        print("\n=== Cleaning database ===")
        db.delete_all()
        
        # Create movies
        print("\n=== Creating movies ===")
        db.create_movie("The Matrix", 1999, "Welcome to the Real World")
        db.create_movie("The Matrix Reloaded", 2003, "Free your mind")
        db.create_movie("The Matrix Revolutions", 2003, "Everything that has a beginning has an end")
        
        # Create people
        print("\n=== Creating people ===")
        db.create_person("Keanu Reeves", 1964)
        db.create_person("Carrie-Anne Moss", 1967)
        db.create_person("Laurence Fishburne", 1961)
        
        # Create relationships
        print("\n=== Creating relationships ===")
        db.create_acted_in_relationship("Keanu Reeves", "The Matrix", ["Neo"])
        db.create_acted_in_relationship("Carrie-Anne Moss", "The Matrix", ["Trinity"])
        db.create_acted_in_relationship("Laurence Fishburne", "The Matrix", ["Morpheus"])
        
        db.create_acted_in_relationship("Keanu Reeves", "The Matrix Reloaded", ["Neo"])
        db.create_acted_in_relationship("Carrie-Anne Moss", "The Matrix Reloaded", ["Trinity"])
        
        # Query movies
        print("\n=== All Movies ===")
        movies = db.find_all_movies()
        for movie in movies:
            print(f"  - {movie['title']} ({movie['released']})")
        
        # Query actors in a movie
        print("\n=== Actors in 'The Matrix' ===")
        actors = db.find_actors_in_movie("The Matrix")
        for actor in actors:
            print(f"  - {actor['actor']} as {', '.join(actor['roles'])}")
        
        print("\n=== Success! ===")
        print("Check Neo4j Browser at http://localhost:7474")
        print("Try running: MATCH (n) RETURN n")
        
    finally:
        # Close connection
        db.close()


if __name__ == "__main__":
    main()

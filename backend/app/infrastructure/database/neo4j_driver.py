"""
Neo4j Graph Database client driver and connection management.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.core.config import get_settings
from app.core.exceptions import GraphDatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__, component="neo4j_driver")

_driver_instance: AsyncDriver | None = None


class Neo4jClient:
    """
    Async Neo4j Client managing connection pool, Cypher query execution,
    and schema index initialization.
    """

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        settings = get_settings().neo4j
        self.uri = uri or settings.uri
        self.user = user or settings.user
        self.password = password or settings.password.get_secret_value()
        self.database = settings.database
        self._driver: AsyncDriver | None = None

    async def get_driver(self) -> AsyncDriver:
        if self._driver is None:
            logger.info("connecting_to_neo4j", uri=self.uri, user=self.user)
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=get_settings().neo4j.max_connection_pool_size,
            )
        return self._driver

    async def check_health(self) -> bool:
        """Verify Neo4j database connectivity."""
        try:
            driver = await self.get_driver()
            await driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.error("neo4j_connectivity_failed", error=str(exc))
            return False

    async def is_reachable(self) -> bool:
        """Fast non-blocking socket probe to check if Neo4j port is listening."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                return sock.connect_ex(("127.0.0.1", 7687)) == 0
        except Exception:
            return False

    async def execute_query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        write: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return list of result records as dictionaries.
        """
        if not await self.is_reachable():
            raise GraphDatabaseError("Neo4j database is offline or unreachable on localhost:7687", query=cypher)

        driver = await self.get_driver()
        params = parameters or {}

        try:
            async with driver.session(database=self.database) as session:
                async def run_query(tx: Any) -> list[dict[str, Any]]:
                    result = await tx.run(cypher, params)
                    return [record.data() async for record in result]

                if write:
                    return await session.execute_write(run_query)
                return await session.execute_read(run_query)
        except Exception as exc:
            logger.error("cypher_execution_failed", cypher=cypher[:100], error=str(exc))
            raise GraphDatabaseError(f"Neo4j query execution failed: {exc}", query=cypher) from exc

    async def init_schema_constraints(self) -> None:
        """Initialize uniqueness constraints and indexes on Neo4j graph nodes."""
        constraints = [
            "CREATE CONSTRAINT employee_id IF NOT EXISTS FOR (e:Employee) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT team_name IF NOT EXISTS FOR (t:Team) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT repo_name IF NOT EXISTS FOR (r:Repository) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT api_endpoint IF NOT EXISTS FOR (a:APIEndpoint) REQUIRE a.path IS UNIQUE",
            "CREATE CONSTRAINT incident_key IF NOT EXISTS FOR (i:Incident) REQUIRE i.key IS UNIQUE",
            "CREATE CONSTRAINT ticket_key IF NOT EXISTS FOR (t:Ticket) REQUIRE t.key IS UNIQUE",
            "CREATE INDEX chunk_id_idx IF NOT EXISTS FOR (c:ChunkNode) ON (c.chunk_id)",
        ]

        logger.info("initializing_neo4j_schema_constraints")
        for cypher in constraints:
            try:
                await self.execute_query(cypher, write=True)
            except Exception as exc:
                logger.warning("neo4j_constraint_creation_warning", cypher=cypher, error=str(exc))

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("neo4j_driver_closed")


# Singleton Neo4j client instance
_neo4j_client_instance: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _neo4j_client_instance
    if _neo4j_client_instance is None:
        _neo4j_client_instance = Neo4jClient()
    return _neo4j_client_instance

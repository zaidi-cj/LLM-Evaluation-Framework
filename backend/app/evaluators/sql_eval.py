import sqlite3
import re
from typing import Dict, Any, Optional, List
from app.evaluators.base import BaseEvaluator

class SQLEvaluator(BaseEvaluator):
    """
    Evaluates generated SQL queries by running them against an in-memory SQLite sandbox
    and comparing the returned datasets to the expected query results.
    """
    
    def _clean_sql(self, sql: str) -> str:
        """
        Cleans markdown formatting and retrieves the SQL query.
        """
        # Remove markdown sql wrapping if present
        sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"```\s*", "", sql)
        return sql.strip()

    def evaluate(
        self,
        input_query: str,
        generated_output: str,
        expected_output: Optional[str] = None,
        context_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Runs generated SQL query and expected SQL query on a temporary SQLite database.
        Returns:
            - sql_valid: 1.0 if it compiles and runs, 0.0 otherwise.
            - execution_correctness: 1.0 if results match, 0.0 otherwise.
        """
        clean_gen = self._clean_sql(generated_output)
        clean_exp = self._clean_sql(expected_output or "")

        if not clean_gen:
            return {"sql_valid": 0.0, "execution_correctness": 0.0}
        
        # Create an in-memory database sandbox
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # DDL & Seed data should be provided in metadata under 'schema_ddl'
        schema_ddl = ""
        if metadata and "schema_ddl" in metadata:
            schema_ddl = metadata["schema_ddl"]
        elif metadata and "test_metadata" in metadata and "schema_ddl" in metadata["test_metadata"]:
            schema_ddl = metadata["test_metadata"]["schema_ddl"]

        try:
            # Setup sandbox schema
            if schema_ddl:
                cursor.executescript(schema_ddl)
                conn.commit()
        except Exception as e:
            conn.close()
            # If our sandbox schema fails to set up, it's a test configuration error, return 0
            return {"sql_valid": 0.0, "execution_correctness": 0.0, "error": 0.0}

        # Run Expected Query to get Ground Truth
        expected_rows = None
        try:
            if clean_exp:
                cursor.execute(clean_exp)
                expected_rows = cursor.fetchall()
        except Exception as e:
            # Expected query failed to run, test case definition error
            conn.close()
            return {"sql_valid": 1.0, "execution_correctness": 0.0, "error": 1.0}

        # Run Generated Query
        generated_rows = None
        sql_valid = 1.0
        try:
            cursor.execute(clean_gen)
            generated_rows = cursor.fetchall()
        except Exception as e:
            sql_valid = 0.0
            generated_rows = None

        conn.close()

        # Compare results
        execution_correctness = 0.0
        if sql_valid == 1.0 and expected_rows is not None and generated_rows is not None:
            # Sort row results to allow order-independent correctness, or strict matching
            # By default, we sort to verify value equivalence.
            # If query relies on order (e.g. ORDER BY), it should match directly.
            is_ordered = "order by" in clean_exp.lower()
            
            if is_ordered:
                if expected_rows == generated_rows:
                    execution_correctness = 1.0
            else:
                try:
                    if sorted(expected_rows) == sorted(generated_rows):
                        execution_correctness = 1.0
                except TypeError:
                    # In case of mixed datatypes that cannot be sorted directly
                    if set(expected_rows) == set(generated_rows):
                        execution_correctness = 1.0

        return {
            "sql_valid": sql_valid,
            "execution_correctness": execution_correctness
        }

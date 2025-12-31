"""End-to-end tests for upload and scoring flow.

These tests verify that the code matches the database schema,
catching issues like using non-existent columns.
"""

import ast
import re
from pathlib import Path


class TestSchemaCompatibility:
    """Tests to verify code matches database schema."""

    def get_migration_columns(self, table_name: str) -> set[str]:
        """Extract column names from a migration file."""
        migration_files = {
            "scored_photos": "003_scored_photos.sql",
            "credits": "001_credits.sql",
            "transactions": "002_transactions.sql",
            "inference_cache": "004_inference_cache.sql",
        }

        migration_path = Path(__file__).parent.parent / "migrations" / migration_files[table_name]
        migration_sql = migration_path.read_text()

        # Extract column definitions from CREATE TABLE
        columns = set()

        # Find CREATE TABLE block - handle IF NOT EXISTS
        create_match = re.search(
            rf"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{table_name}\s*\((.*?)\);",
            migration_sql,
            re.DOTALL | re.IGNORECASE,
        )

        if create_match:
            create_block = create_match.group(1)
            # Process line by line
            for line in create_block.split("\n"):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("--"):
                    continue
                # Skip constraints that aren't column definitions
                if line.upper().startswith(("UNIQUE(", "PRIMARY KEY(", "CONSTRAINT", "CHECK")):
                    continue
                # Extract column name (first word before space)
                # Column definitions look like: column_name TYPE ...
                match = re.match(
                    r"(\w+)\s+(?:UUID|TEXT|INTEGER|NUMERIC|JSONB|VARCHAR|TIMESTAMPTZ|BOOLEAN)",
                    line,
                    re.IGNORECASE,
                )
                if match:
                    columns.add(match.group(1).lower())

        return columns

    def get_code_columns_for_update(self, router_path: Path, function_name: str) -> set[str]:
        """Extract top-level column names used in .update() calls within a function.

        Uses AST parsing to correctly handle nested dicts (e.g., model_scores: {...}).
        """
        source = router_path.read_text()
        columns = set()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            # Find function definition
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # Walk inside the function
                for child in ast.walk(node):
                    # Look for method calls like .update({...})
                    if isinstance(child, ast.Call):
                        if (
                            isinstance(child.func, ast.Attribute)
                            and child.func.attr == "update"
                            and child.args
                            and isinstance(child.args[0], ast.Dict)
                        ):
                            # Extract only top-level keys from the dict
                            for key in child.args[0].keys:
                                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                    columns.add(key.value.lower())
                break

        return columns

    def get_code_columns_for_insert(self, router_path: Path, table_name: str) -> set[str]:
        """Extract column names used in .insert() calls for a specific table."""
        source = router_path.read_text()
        columns = set()

        # Find insert dicts for the table
        # Pattern: .table("table_name").insert({...})
        insert_pattern = re.search(
            rf'\.table\("{table_name}"\)\.insert\(\s*\{{(.*?)\}}\s*\)',
            source,
            re.DOTALL,
        )

        if insert_pattern:
            insert_dict = insert_pattern.group(1)
            key_pattern = re.findall(r'"(\w+)"\s*:', insert_dict)
            columns.update(k.lower() for k in key_pattern)

        return columns

    def test_score_update_columns_exist_in_schema(self):
        """Verify all columns updated in score_photo exist in the migration."""
        migration_columns = self.get_migration_columns("scored_photos")

        router_path = Path(__file__).parent.parent / "api" / "routers" / "photos.py"
        code_columns = self.get_code_columns_for_update(router_path, "score_photo")

        # Check that all code columns exist in migration
        missing_columns = code_columns - migration_columns
        assert not missing_columns, (
            f"Columns used in code but not in migration: {missing_columns}\n"
            f"Migration columns: {migration_columns}\n"
            f"Code columns: {code_columns}"
        )

    def test_upload_insert_columns_exist_in_schema(self):
        """Verify all columns inserted in upload_photo exist in the migration."""
        migration_columns = self.get_migration_columns("scored_photos")

        router_path = Path(__file__).parent.parent / "api" / "routers" / "photos.py"
        code_columns = self.get_code_columns_for_insert(router_path, "scored_photos")

        missing_columns = code_columns - migration_columns
        assert not missing_columns, (
            f"Columns used in code but not in migration: {missing_columns}\n"
            f"Migration columns: {migration_columns}\n"
            f"Code columns: {code_columns}"
        )

    def test_credits_columns_exist_in_schema(self):
        """Verify credits table columns match schema."""
        migration_columns = self.get_migration_columns("credits")

        # Expected columns from the migration
        expected = {"user_id", "balance", "updated_at"}

        assert expected.issubset(migration_columns), (
            f"Expected columns {expected} not all in migration: {migration_columns}"
        )

    def test_no_scored_at_column_used(self):
        """Verify we don't use scored_at (which doesn't exist)."""
        router_path = Path(__file__).parent.parent / "api" / "routers" / "photos.py"
        source = router_path.read_text()

        assert "scored_at" not in source, (
            "Found 'scored_at' in photos.py - this column doesn't exist. Use 'updated_at' instead."
        )

    def test_inference_cache_columns_exist(self):
        """Verify inference_cache table columns match what code uses."""
        migration_columns = self.get_migration_columns("inference_cache")

        # Columns the code uses
        expected = {"user_id", "image_hash", "attributes"}

        assert expected.issubset(migration_columns), (
            f"Expected columns {expected} not all in migration: {migration_columns}"
        )


class TestMigrationSyntax:
    """Tests to verify migration files are valid."""

    def test_all_migrations_exist(self):
        """Verify all expected migration files exist."""
        migrations_dir = Path(__file__).parent.parent / "migrations"

        expected_migrations = [
            "001_credits.sql",
            "002_transactions.sql",
            "003_scored_photos.sql",
            "004_inference_cache.sql",
        ]

        for migration in expected_migrations:
            path = migrations_dir / migration
            assert path.exists(), f"Migration file not found: {migration}"

    def test_migrations_have_create_table(self):
        """Verify each migration creates a table."""
        migrations_dir = Path(__file__).parent.parent / "migrations"

        for migration_file in migrations_dir.glob("*.sql"):
            content = migration_file.read_text()
            assert "CREATE TABLE" in content.upper(), (
                f"Migration {migration_file.name} doesn't contain CREATE TABLE"
            )

# Migration Rules

`migration.yml` bundles the ast-grep rewrites used to migrate imports to
`rust_ok`. Apply it whenever you need to re-run the migration.

## Usage

1. Install ast-grep (https://ast-grep.github.io/guide/installation.html).
2. Preview matches:

   ```bash
   ast-grep scan --rule ast-grep-rules/migration.yml src tests
   ```

3. Apply the rewrites in-place:

   ```bash
   ast-grep scan --rule ast-grep-rules/migration.yml src tests --update-all
   ```

Review the resulting diffs and run pytest afterward.

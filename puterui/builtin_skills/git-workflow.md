# Git Workflow
> Git operations, branching strategies, and commit best practices

When working with git:

1. **Always check status first**: `git status` and `git log --oneline -5`
2. **Branch naming**: `feature/description`, `fix/description`, `chore/description`
3. **Commit messages**: Use conventional commits format
   - `feat: add user authentication`
   - `fix: resolve null pointer in parser`
   - `refactor: extract validation logic`
   - `docs: update API reference`
   - `test: add edge case coverage`
4. **Small commits**: Each commit should be one logical change
5. **Before committing**: Run tests and linting
6. **Never commit**: Secrets, credentials, large binaries, node_modules
7. **Conflict resolution**: Show both versions, explain the difference, let user decide

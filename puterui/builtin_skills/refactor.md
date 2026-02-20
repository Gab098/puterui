# Refactor
> Systematic code refactoring with safe, incremental changes

When refactoring code:

1. **Understand first**: Read all relevant files, understand the current design
2. **Plan the refactor**: Explain what you will change and why before starting
3. **Small steps**: Make one logical change at a time, not everything at once
4. **Preserve behavior**: Refactoring should not change external behavior
5. **Test after each step**: Run existing tests to catch regressions
6. **Common patterns**:
   - Extract method/function for repeated code
   - Rename for clarity
   - Simplify conditionals
   - Remove dead code
   - Split large functions (>30 lines is a smell)
   - Reduce nesting depth
7. **Do not** introduce new dependencies unless absolutely necessary

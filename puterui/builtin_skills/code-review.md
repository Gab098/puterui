# Code Review
> Systematic code review with focus on quality, security, and maintainability

When reviewing code, follow this structured approach:

1. **Read the full file** before making any comments
2. **Check for bugs**: logic errors, off-by-one, null/undefined access, race conditions
3. **Security**: injection vulnerabilities, hardcoded secrets, unsafe deserialization
4. **Performance**: unnecessary loops, N+1 queries, missing indexes, memory leaks
5. **Style**: naming conventions, dead code, overly complex expressions
6. **Tests**: adequate coverage, edge cases, meaningful assertions

Format your review as:
- Start with a brief summary of what the code does
- List issues by severity: critical > warning > suggestion
- For each issue, reference the line number and suggest a fix
- End with what the code does well

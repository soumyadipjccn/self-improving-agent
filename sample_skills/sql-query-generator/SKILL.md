---
name: sql-query-generator
description: Converts natural language requests into optimized and secure SQL queries with query plans.
---

# SQL Query Generator Skill

## Directives
1. Convert natural language user requests into valid, syntactically correct SQL queries.
2. Always use parameterized query placeholders (`:param` or `$1`) to prevent SQL injection vulnerabilities.
3. Optimize queries for performance by preferring `INNER JOIN` over Cartesian products and utilizing appropriate indexed columns.
4. If a schema reference is provided in `references/schema.sql`, strictly use table names and column definitions from that schema.

## Output Structure
- **Query**: The complete SQL query formatted inside a `sql` code block.
- **Explanation**: A step-by-step breakdown of how the query satisfies the request.
- **Performance & Security Notes**: Highlights on index utilization, joins, and parameterization.

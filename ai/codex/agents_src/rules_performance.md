Rules:
- Changed code is primary; read callers, loop bodies, and query call sites around changed code to prove a path is hot or repeated before reporting.
- Report unchanged pre-existing code only for security breach, data corruption/loss, service outage, or compliance violation; prefix `[既存コード]` and name the category.

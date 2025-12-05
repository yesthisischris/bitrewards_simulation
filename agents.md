# Architecture and Code Quality Guidelines

## Core Principles

### Clean Architecture

- Follow clean architecture patterns with clear separation between layers
- Domain logic should be independent of frameworks, UI, and external concerns
- Dependencies should point inward toward the domain

### Separation of Concerns

- Each module/class should have a single, well-defined responsibility
- Avoid mixing business logic with presentation or data access concerns
- Keep related functionality together, unrelated functionality apart

### Dependency Injection & Inversion of Control

- Depend on abstractions, not concretions
- Use dependency injection to provide dependencies rather than creating them
- Make dependencies explicit through constructor parameters or function arguments
- Favor composition over inheritance

### Code Readability & Maintainability

- **NO COMMENTS ALLOWED** - Code should be self-documenting
- If logic seems complex enough to need a comment, extract it into a well-named function
- Use descriptive variable and function names that clearly express intent
- Avoid magic numbers - use named constants with clear purpose
- Functions should do one thing and do it well
- Keep functions small and focused

### Naming Conventions

- Variables and functions should clearly express their purpose and behavior
- Prefer longer, descriptive names over short, cryptic ones
- Function names should describe what they do, not how they do it
- Boolean variables should be clearly questions (isValid, hasPermission, canAccess)

### Code Organization

- Group related functionality together
- Use consistent file and folder structure
- Keep public interfaces minimal and well-defined
- Hide implementation details behind clear abstractions

## Implementation Guidelines

### When Writing New Code

1. Identify the core business logic and keep it pure
2. Define clear interfaces for external dependencies
3. Use dependency injection for all external services
4. Write self-documenting code with clear naming
5. Extract complex logic into well-named functions
6. Avoid direct coupling between unrelated modules

### When Refactoring

1. Identify violations of single responsibility principle
2. Extract mixed concerns into separate modules
3. Replace magic numbers with named constants
4. Rename unclear variables and functions
5. Remove any existing comments by making code self-explanatory
6. Introduce abstractions for external dependencies

### Documentation Discipline

1. When behavior or parameters change, update `docs/model.md` and `docs/usage.md` in the same PR
2. Keep quickstart commands valid; if CLI flags or defaults move, refresh the snippets
3. Record new scenarios and expected outcomes in `docs/usage.md` before merging
4. Do not leave stale references to removed files or paths; replace them with current locations

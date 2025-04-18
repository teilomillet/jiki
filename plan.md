# Jiki Architectural Refactor Plan

## Vision & Goals

- Provide a lean, modular orchestrator layer ("under the skin") that can manage clients, servers, tools, prompts, resources, sampling and transports without unnecessary bloat.
- Ensure full interoperability and extensibility via well‑defined interfaces and pluggable components.
- Keep core code minimal while enabling advanced customization through optional modules.

---

## Phase 1: Audit & Documentation

1. Inventory current codebase: list all modules, their responsibilities, and dependencies.
2. Identify cross‑cutting concerns (e.g., logging, tracing, serialization, error handling).
3. Document existing workflows: tool discovery, execution flow, prompt generation, resource access.
4. Write up desired component boundaries and responsibilities.

---

## Phase 2: Define Core Interfaces & Contracts

- **Transport**: define `ITransport` protocol for stdio, SSE, HTTP, WebSockets, etc.
- **ToolClient**: specify abstract methods for discovering, validating, and invoking tools.
- **PromptBuilder**: create contract for constructing initial context, tool‑call wrappers, and result‑injection templates.
- **ResourceManager**: interface for listing, reading, and subscribing to resources.
- **SamplerConfig**: structure for passing sampling parameters (temperature, top_p, max_tokens) to LLM calls.
- **RootManager**: API for snapshotting conversation roots and resuming from saved contexts.
- **Serializer**: standard fallback JSON serializer with hooks for custom types.

---

## Phase 3: Modularize & Refactor

1. Move existing implementations into discrete packages:
   - `jiki.transports`
   - `jiki.tools`
   - `jiki.prompts`
   - `jiki.resources`
   - `jiki.sampling`
   - `jiki.roots`
   - `jiki.serialization`
2. Refactor `EnhancedMCPClient` to implement `ToolClient` and `Transport` separately.
3. Refactor `JikiOrchestrator` to depend only on interfaces and compose pluggable modules.
4. Replace hardcoded imports with dynamic registration and dependency injection.

---

## Phase 4: Validation & Testing

- Write unit tests for each core interface and module.
- Implement end‑to‑end scenarios: tool calls, resource reads, sampled responses.
- Add integration tests using a mock MCP server (stdio and SSE).
- Validate JSON‑RPC error handling and edge cases.

---

## Phase 5: Documentation & Examples

- Update README with new module structure and quickstart.
- Provide example scripts showcasing:
  - Custom transport
  - New tool discovery and invocation
  - Resource listing and reading
  - Sampling parameter overrides
  - Root snapshot and resume flow
- Publish API reference for all public interfaces.

---

## Phase 6: Release & Maintenance

1. Bump version and tag release.
2. Announce changes in changelog.
3. Gather feedback and iterate on modular APIs.
4. Plan roadmap items for additional MCP spec features (e.g., notifications, progress reports). 
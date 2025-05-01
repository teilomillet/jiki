# Jiki Architectural Refactor & Documentation Plan

## Vision & Goals

- Provide a lean, modular orchestrator layer ("under the skin") that can manage clients, servers, tools, prompts, resources, sampling and transports without unnecessary bloat.
- Ensure full interoperability and extensibility via well‑defined interfaces and pluggable components.
- Keep core code minimal while enabling advanced customization through optional modules.
- Create comprehensive, code-first documentation that makes Jiki accessible to new users while providing depth for advanced use cases.
- Build community around Jiki by providing clear pathways for adoption, customization, and contribution.

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

## Phase 5: Documentation Overhaul

### 5.1: Code-First Documentation

- **README.md**: Restructure to focus on practical usage with copy-paste ready commands and examples
  - Streamline introduction to 1-2 sentences
  - Expand "Quick Start" with minimal but complete examples
  - Add troubleshooting section
  - Include "Next Steps" section with pathways to examples by use case

- **Command-Line Documentation**:
  - Create comprehensive CLI examples with expected outputs
  - Provide cheat sheet with common patterns
  - Include environment configuration guide

- **Code Examples**:
  - Create dedicated examples directory with complete, runnable scripts
  - Add progressive examples from basic to advanced
  - Include extensive comments explaining each step

### 5.2: Task-Based Guides

- **Getting Started Guide**:
  - Rewrite to be task-oriented
  - Include installation, setup, first run steps
  - Add screenshots and expected outputs
  - Provide complete minimal working example

- **Use Case Tutorials**:
  - Calculator example tutorial
  - Custom tools creation guide
  - Web deployment walkthrough
  - Conversation state management tutorial
  - Integration with other frameworks

### 5.3: API Reference

- **Core Components**:
  - Document main factory function (`Jiki()`)
  - Document JikiOrchestrator class
  - Document JikiClient and BaseMCPClient
  - Document IPromptBuilder interface

- **Tools Documentation**:
  - Explain tool schema format
  - Provide examples of valid tool definitions
  - Include step-by-step guide for creating tools

### 5.4: Visual Documentation

- **Diagrams**:
  - Create architecture overview diagram
  - Add sequence diagram for tool call workflow
  - Develop component relationship diagram
  - Include data flow visualization

### 5.5: Community Support

- **Contributing Guide**:
  - Create clear contribution guidelines
  - Document development setup
  - Add code style and PR process documentation

- **Showcase**:
  - Highlight community projects
  - Collect use cases and testimonials

---

## Phase 6: Release & Maintenance

1. Bump version and tag release.
2. Announce changes in changelog.
3. Gather feedback and iterate on modular APIs.
4. Plan roadmap items for additional MCP spec features (e.g., notifications, progress reports).
5. Establish feedback channels for documentation improvements.
6. Create regular documentation update schedule. 
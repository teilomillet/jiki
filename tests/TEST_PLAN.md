# High-Level Test Plan TODOs for Jiki

This document captures the top-level areas where tests should be added to ensure Jiki's reliability and maintainability. Each section explains **why** these tests are important and suggests **how** to approach them.

## 1. Setup and Fixtures
- Rationale: Establish reproducible test environments and simplify test code.
- TODO: Create pytest fixtures to launch the example calculator server (stdio mode) and tear it down.
- TODO: Provide a `jiki_instance` fixture that constructs a `Jiki(...)` with `auto_discover_tools=True` and `mcp_script_path` pointing to our test server.
- Approach: Use Python's `subprocess` module and pytest's `yield_fixture` for setup/teardown.

## 2. Orchestrator Core Tests
- Rationale: The `Jiki` orchestrator manages LLM and tool calls; this is the heart of the library.
- TODO: Test `process("2 + 2")` returns the correct string output.
- TODO: Test `process_detailed("2 + 3")` returns a `DetailedResponse` with properly typed fields (`.result: str`, `.tool_calls: List[...]`, `.traces: str`).
- Approach: Call methods against the test server, use `assert isinstance(...)` for type checks and exact value assertions.

## 3. MCP Client Tests
- Rationale: Ensures reliable tool discovery and JSON-RPC invocation.
- TODO: Test `MCPClient.list_resources()` matches the expected schema from the example server.
- TODO: Test `MCPClient.call(...)` returns parsed results matching the tool's response.
- Approach: Reuse the example server fixture, assert on returned Python objects and types.

## 4. CLI Command Tests
- Rationale: Users interact via CLI; flags must be parsed correctly and commands behave as documented.
- TODO: Use Click's `CliRunner` to test `jiki run`, `jiki process`, and `jiki trace` commands.
- TODO: Verify exit codes, stdout/stderr content, and type correctness (printed JSON vs. plain text).
- Approach: Parametrize different flag combinations and simulate stdin input.

## 5. Tool Client Tests
- Rationale: Provides a higher-level API over raw MCP calls; must wrap correctly.
- TODO: Test helper methods (e.g., auto schema loading, convenience calls) match lower-level client output.
- Approach: Invoke against the test server and compare semantics to raw `MCPClient`.

## 6. Sampling Configuration Tests
- Rationale: Validates user-specified LLM parameters are enforced and propagated.
- TODO: Test invalid `SamplerConfig` values raise `ValueError` or `TypeError`.
- TODO: Test valid configs are passed to LLM client (mock LLM client to capture parameters).
- Approach: Use pytest `parametrize` and a dummy LLM client implementation.

## 7. Serialization Round-Trip Tests
- Rationale: Data classes and custom types must serialize/deserialize predictably.
- TODO: Round-trip key data structures in `jiki.serialization`, assert equality and type integrity.
- Approach: Use custom JSON hooks, compare before/after objects with `==` and `isinstance(...)` checks.

## 8. Logging and Tracing Tests
- Rationale: Users rely on logs and trace exports for debugging.
- TODO: Enable `trace=True` on orchestrator, run a sample process, and assert logs exist via pytest `caplog`.
- TODO: Test `export_traces()` output format and content.
- Approach: Capture log output, parse trace strings or files.

## 9. Utilities and Submodule Tests
- Rationale: Each submodule (`utils/`, `transports/`, `prompts/`, `roots/`, `resources/`, `models/`) has standalone logic.
- TODO: Identify main public function or class in each submodule and write one unit test per API surface.
- Approach: Use pattern "Input → API call → Output" and include `assert isinstance(...)` checks.

## 10. Integration / End-to-End Tests
- Rationale: Validate real-world usage of Jiki with minimal setup.
- TODO: Write an E2E test that combines orchestrator, transport, sampling, and CLI against the example servers.
- Approach: Use a single test that runs a small scenario end-to-end (e.g., "What is 10 + 20?") and validates the full stack.

## 11. Detailed Module-Level Tests

### jiki/utils
- TODO: Test `streaming.StreamReader` yields correct chunk sequences for various inputs (type and order checks).
- TODO: Test `utils.tool` functions load and validate tool definitions, handling missing or malformed schemas.
- TODO: Test `token` utilities produce accurate token counts and boundary indices for representative text.
- TODO: Test `logging` helpers format messages consistently and filter levels correctly.
- TODO: Test `parsing` functions correctly extract tool calls and arguments from LLM outputs.
- TODO: Test `context` manager push/pop maintains the correct context stack and isolation.
- TODO: Test `cleaning` functions strip control characters, normalize whitespace, and preserve content.

### jiki/transports
- TODO: Test `factory.get_transport(config)` returns appropriate transport instance given stdio vs. SSE settings.
- TODO: Simulate a mock MCP server and verify stdio transport sends/receives messages correctly.
- TODO: Validate SSE transport reconnect logic and error handling under network interruptions.

### jiki/prompts
- TODO: Test `prompt_builder.build_prompt(schema, user_input)` constructs expected string templates for single/multi-turn scenarios.
- TODO: Validate that `prompts.utils` template functions properly interpolate variables and escape special characters.

### jiki/serialization
- TODO: Round-trip key data structures (e.g., `DetailedResponse`, tool call objects) through `helpers` JSON encoder/decoder, asserting equality and type integrity.
- TODO: Test custom hooks for non-standard types (e.g., enums, datetime) serialize and deserialize without loss.

### jiki/roots
- TODO: Test `RootManager` implementations store and retrieve snapshot data with correct versioning and metadata.
- TODO: Test `ConversationRootManager` supports snapshot, resume, and purge operations while preserving conversation history.

### jiki/resources
- TODO: Test `ResourceManager.list_resources()` returns expected file/resource listings from a temporary directory fixture.
- TODO: Test `ResourceManager.read_resource(path)` reads contents correctly and errors on missing files.

### jiki/models
- TODO: Test `litellm.LiteLLMClient` stub honors sampling parameters (temperature, max_tokens) and returns deterministic stubbed responses.
- TODO: Test `response.Response` data class validates required fields, enforces types, and serializes to dict/JSON accurately.

### Top-Level Modules
- TODO: Use Click's `CliRunner` to test `cli.run`, `cli.process`, and `cli.trace` commands for flag parsing, stdin/stdout handling, and exit codes.
- TODO: Test `orchestrator.Jiki` constructor argument validation, exceptions on invalid configs, and flag-driven behaviors (`trace`, custom `SamplerConfig`, `auto_discover_tools`).
- TODO: Test `mcp_client.MCPClient` handles JSON-RPC errors, timeouts, and retries according to config.
- TODO: Test `tool_client` wrappers raise informative errors on invalid tool names or mismatched arguments.

---

Following this TODO list will guide contributors in incrementally building comprehensive test coverage, verifying correctness, and enforcing type safety across Jiki's core and peripheral modules. 
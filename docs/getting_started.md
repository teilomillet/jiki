# Getting Started with Jiki

Welcome to Jiki! This guide will walk you through the basics of using the Jiki orchestration framework.

Jiki is designed to be **easy to learn** for common use cases, yet **powerful and extensible** (hard to master) for advanced scenarios.

## 1. The Easiest Way: `Jiki()`

The simplest way to get started is using the `Jiki` factory function. It sets up a `JikiOrchestrator` instance with sensible defaults, including tool discovery and interaction tracing.

**Prerequisites:**

*   Install Jiki: `pip install jiki` (or `uv pip install jiki`)
*   Set up necessary API keys (e.g., `export ANTHROPIC_API_KEY=your_key`)
*   Have a compatible MCP tool server running or accessible (we'll use the example calculator server).

**Example:**

Let's assume you have the example `calculator_server.py` from the Jiki repository.

```python
# file: run_calculator.py
# Import the main factory function
from jiki import Jiki 

# Create a pre-configured orchestrator using auto-discovery
# Assumes servers/calculator_server.py is in the current directory or path
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_mode="stdio",
    mcp_script_path="servers/calculator_server.py"
)

# Option 1: Launch the built-in interactive CLI
print("Starting interactive Jiki session...")
orchestrator.run_ui() 

# Option 2: Process a single query programmatically
# print("\nProcessing single query...")
# result = orchestrator.process("What is 12 * 11?")
# print(f"Query: What is 12 * 11?\nResult: {result}")

# Traces are automatically saved on exit when using run_ui()
# or can be saved manually:
# orchestrator.export_traces("calculator_session.jsonl") 
```

Run this script (`python run_calculator.py`), and you'll get an interactive prompt where you can ask the AI questions that might require using the calculator tool (e.g., "What is 256 + 128?").

## 2. Core Concepts: Orchestrator and Client

Behind the scenes, `Jiki()` configures:

*   **`JikiOrchestrator`**: The main engine that manages the conversation flow, prompts the LLM, handles tool calls, and maintains context.
*   **`JikiClient`**: The default MCP client implementation used to communicate with the tool server (`calculator_server.py` in this case) for discovering and executing tools. It uses the `fastmcp` library.

For many use cases, you might only ever need `Jiki()`.

## 3. Easy to Learn, Hard to Master

Jiki's philosophy centers around this principle:

*   **Easy to Learn:** The `Jiki()` factory provides a high-level interface that hides most of the complexity. You can get a capable tool-using AI assistant running in just a few lines of code without needing to understand the underlying MCP protocol or prompt engineering details. The default `JikiClient` handles standard communication effectively.

*   **Hard to Master (Powerful & Extensible):** When you need more control, Jiki's power emerges. The `JikiOrchestrator` relies on well-defined interfaces (protocols) for its core components. This means you can:
    *   **Customize Prompts:** Implement your own `IPromptBuilder` to change how tools and context are presented to the LLM.
    *   **Implement Custom Clients:** Subclass `BaseMCPClient` (the parent of `JikiClient`) to use different communication transports or add custom logic around tool calls.
    *   **Integrate Different Models:** While `LiteLLMModel` is the default, the orchestrator interacts with the model via a simple interface.
    *   **Manage State Differently:** Plug in custom root or resource managers.

    This extensibility allows you to tailor Jiki precisely to your needs, integrate it into complex applications, or experiment with novel AI interaction patterns.

## Use Case Scenarios

Below are common real‑world objectives and how Jiki's core components can be combined to fulfill each need:

> **Example Wiring (Pseudo-code)**  
> ```python
> from jiki import Jiki, SamplerConfig
> # If you're happy with the default prompt builder, no import needed
> # For custom scenarios, swap in your own builder:
> # from jiki.prompts.prompt_builder import DefaultPromptBuilder or CustomPromptBuilder
> 
> sampler = SamplerConfig(temperature=0.5, top_p=0.9)
> 
> orchestrator = Jiki(
>     auto_discover_tools=True,
>     mcp_script_path="servers/calculator_server.py",
>     sampler_config=sampler,
>     # prompt_builder=CustomPromptBuilder(),  # optional custom builder
>     # conversation_root_manager=YourRootManager(),  # optional
> )
>
> # Process your specific instruction
> result = orchestrator.process("Your task-specific instruction here")
> print(result)
> ```
>
> **How it works:**
> 1. Import Jiki and any optional helpers (e.g., `SamplerConfig`, custom `IPromptBuilder`).
> 2. Instantiate scenario-specific extensions (prompt builders, samplers, root managers).
> 3. Create the `Jiki` orchestrator with those components.
> 4. Call `orchestrator.process()` or `process_detailed()` with your instruction.
> 5. Swap in different components to adapt to each use case with just a few lines.

1. **Rapid Research & Rich Vocabulary**
   - *Need:* Surface relevant facts and suggest varied wording.
   - *Jiki Components:* Custom `IPromptBuilder` for retrieval prompts + optional resource manager + post‑processing hooks for synonym expansion.

2. **Consistent, Scalable Brand Voice**
   - *Need:* Generate large volumes of content that follow a tone/style guide.
   - *Jiki Components:* `SamplerConfig` for stable output + custom prompts enforcing brand rules + batch mode via repeated `process()` calls.

3. **SEO‑Optimized Output at Speed**
   - *Need:* Weave target keywords into outlines and prose that rank.
   - *Jiki Components:* Prompt templates (via `IPromptBuilder`) for outline structure + post‑processing (keyword injector) + trace inspection for metrics.

4. **Boilerplate‑Free Code Assistance**
   - *Need:* In‑IDE snippet suggestions that handle routine patterns.
   - *Jiki Components:* Integrate `mcp_client.execute_tool_call` for code‐analysis tools + custom root manager for repository context + detailed responses for insertion metadata.

5. **Team Velocity & Onboarding Accelerator**
   - *Need:* Provide repo‑specific examples and review hints.
   - *Jiki Components:* Custom resource manager to ingest codebase + `process_detailed()` for step‐by‐step traces + adjustable prompt to surface examples.

6. **Natural‑Language Persuasion**
   - *Need:* Generate human‑like copy with varied phrasing.
   - *Jiki Components:* High‐temperature `SamplerConfig` + prompt variations + post‑filtering for diversity scoring.

7. **Structured Knowledge & Summaries**
   - *Need:* Turn notes or transcripts into clean outlines and summaries.
   - *Jiki Components:* Chunking logic (external or via resource manager) + prompt templates for summarization + chaining of `process()` calls.

8. **High‑Volume, Low‑Cost Production**
   - *Need:* Batch‐generate quality content under budget.
   - *Jiki Components:* Batch orchestration loop + cost‐monitoring middleware + sampler config tuned for brevity.

9. **Data‑Driven Growth Content**
   - *Need:* Iterate on content variants and feed back performance.
   - *Jiki Components:* Automated A/B runner (batch `process()`), trace logging + analytics on `TraceLogger` outputs + dynamic parameter adjustment via feedback loop.

## Next Steps

*   Explore the **[Core Interfaces](core_interfaces.md)** to understand the protocols that enable Jiki's extensibility.
*   Dive into the **[MCP Client Overview](mcp_client.md)** to learn more about `JikiClient` and `BaseMCPClient`.
*   Check out the **[Orchestrator Interfaces](orchestrator_interfaces.md)** for more details on the orchestrator itself. 
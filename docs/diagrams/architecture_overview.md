# Jiki Architecture Diagrams

## Architecture Overview

This diagram shows the high-level architecture of Jiki, with key components and their relationships.

```mermaid
graph TD
    User[User/Application] --> Jiki["Jiki() Factory"]
    Jiki --> Orchestrator["JikiOrchestrator"]
    
    subgraph "Core Components"
        Orchestrator --> Model["LiteLLMModel"]
        Orchestrator --> MCPClient["JikiClient"]
        Orchestrator --> PromptBuilder["DefaultPromptBuilder"]
        Orchestrator --> Logger["TraceLogger"]
    end
    
    subgraph "External Services"
        Model --> LLM["Large Language Model"]
        MCPClient --> ToolServer["MCP Tool Server"]
    end
    
    subgraph "Configuration Components"
        SamplerConfig["SamplerConfig"] --> Model
        Tools["Tool Definitions"] --> Orchestrator
        RootManager["ConversationRootManager"] --> Orchestrator
    end
    
    classDef core fill:#f9f,stroke:#333,stroke-width:2px;
    classDef external fill:#bbf,stroke:#333,stroke-width:2px;
    classDef config fill:#bfb,stroke:#333,stroke-width:2px;
    classDef user fill:#fbb,stroke:#333,stroke-width:2px;
    
    class User user;
    class Orchestrator,Model,MCPClient,PromptBuilder,Logger core;
    class LLM,ToolServer external;
    class SamplerConfig,Tools,RootManager config;
```

## Tool Call Sequence

This diagram illustrates the sequence of events during a tool-augmented conversation.

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator as JikiOrchestrator
    participant Model as LiteLLMModel
    participant LLM as Large Language Model
    participant MCPClient as JikiClient
    participant ToolServer as MCP Tool Server
    
    User->>Orchestrator: process("What is 5 * 7?")
    Orchestrator->>Model: generate_tokens(messages)
    Model->>LLM: API call with tools schema
    
    LLM-->>Model: Stream tokens
    Model-->>Orchestrator: Stream tokens
    
    Note over LLM: Decides to use calculator tool
    
    LLM-->>Model: "<mcp_tool_call>..."
    Model-->>Orchestrator: Intercept tool call
    
    Orchestrator->>Orchestrator: Parse & validate call
    Orchestrator->>MCPClient: execute_tool_call("multiply", {a:5, b:7})
    MCPClient->>ToolServer: JSON-RPC tools/call
    ToolServer-->>MCPClient: Result "35"
    MCPClient-->>Orchestrator: Return result
    
    Orchestrator->>Model: Continue with result
    Model->>LLM: Continue with updated context
    LLM-->>Model: Complete response
    Model-->>Orchestrator: Complete response
    Orchestrator-->>User: "5 * 7 = 35"
```

## Component Relationships

This diagram shows the detailed relationships and interfaces between Jiki components.

```mermaid
classDiagram
    class Jiki {
        +function(model, tools, auto_discover_tools, etc)
        +returns JikiOrchestrator
    }
    
    class JikiOrchestrator {
        -model: Any
        -mcp_client: IMCPClient
        -tools_config: List
        -logger: TraceLogger
        -prompt_builder: IPromptBuilder
        -root_manager: IConversationRootManager
        +process(user_input)
        +process_detailed(user_input)
        +snapshot()
        +resume(snapshot)
    }
    
    class IMCPClient {
        <<interface>>
        +initialize()
        +discover_tools()
        +execute_tool_call(tool_name, arguments)
        +list_resources()
        +read_resource(uri)
    }
    
    class JikiClient {
        -transport_source: Any
        -roots_handler: Optional
        +initialize()
        +discover_tools()
        +execute_tool_call(tool_name, arguments)
        +list_resources()
        +read_resource(uri)
    }
    
    class IPromptBuilder {
        <<interface>>
        +create_available_tools_block(tools_config)
        +create_available_resources_block(resources_config)
        +build_initial_prompt(user_input, tools_config, resources_config)
    }
    
    class DefaultPromptBuilder {
        +create_available_tools_block(tools_config)
        +create_available_resources_block(resources_config)
        +build_initial_prompt(user_input, tools_config, resources_config)
    }
    
    class LiteLLMModel {
        -model_name: str
        -sampler_config: ISamplerConfig
        +generate_tokens(messages)
    }
    
    class TraceLogger {
        -log_dir: str
        +log_event(event_data)
        +log_complete_trace(trace_data)
        +export_traces(output_path)
    }
    
    Jiki ..> JikiOrchestrator : creates
    JikiOrchestrator --> IMCPClient : uses
    JikiOrchestrator --> IPromptBuilder : uses
    JikiOrchestrator --> LiteLLMModel : uses
    JikiOrchestrator --> TraceLogger : uses
    JikiClient ..|> IMCPClient : implements
    DefaultPromptBuilder ..|> IPromptBuilder : implements
```

## Data Flow Diagram

This diagram shows how data flows through the system during a typical interaction.

```mermaid
flowchart TD
    UserInput[User Input] --> Orchestrator[JikiOrchestrator]
    
    subgraph OrchestratorFlow[JikiOrchestrator Processing]
        direction TB
        PromptConstruction[Prompt Construction] --> LLMCall[LLM API Call]
        LLMCall --> TokenStreaming[Token Streaming]
        TokenStreaming --> ToolCallDetection{Tool Call?}
        ToolCallDetection -->|Yes| ToolCallHandling[Tool Call Handling]
        ToolCallDetection -->|No| ResponseFormatting[Response Formatting]
        ToolCallHandling --> ResultInjection[Result Injection]
        ResultInjection --> TokenStreaming
        ResponseFormatting --> OutputCleaning[Output Cleaning]
    end
    
    PromptBuilder[IPromptBuilder] -.-> PromptConstruction
    ToolSchema[Tool Schemas] -.-> PromptConstruction
    Resources[Resources] -.-> PromptConstruction
    
    ToolCallHandling --> MCPClient[JikiClient]
    MCPClient --> ToolServer[MCP Tool Server]
    ToolServer --> MCPClient
    MCPClient --> ToolCallHandling
    
    OutputCleaning --> FinalResponse[Final Response]
    
    TraceLogger[TraceLogger] -.-> OrchestratorFlow
    
    FinalResponse --> UserOutput[User Output]
    
    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef process fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef decision fill:#fff9c4,stroke:#f57f17,stroke-width:2px;
    classDef output fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;
    classDef external fill:#bbdefb,stroke:#1565c0,stroke-width:1px;
    
    class UserInput,UserOutput input;
    class PromptConstruction,TokenStreaming,ToolCallHandling,ResultInjection,ResponseFormatting,OutputCleaning process;
    class ToolCallDetection decision;
    class FinalResponse output;
    class PromptBuilder,ToolSchema,Resources,TraceLogger,MCPClient,ToolServer external;
``` 
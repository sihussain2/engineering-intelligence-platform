# ADR-001: Initial Agent Architecture

## Status

Accepted and Implemented

## Decision

The initial engineering agent will be implemented directly using
LLM tool calling rather than a high-level agent framework.

## Reason

This project is both a product prototype and a learning platform.

Implementing the initial agent loop directly allows us to understand:

- tool calling
- agent state
- context management
- tool execution
- iteration
- failure handling
- termination conditions

A higher-level agent framework may be introduced later if it provides
clear engineering benefits.

## Initial Scope

The first agent will analyze a software requirement and produce an
engineering implementation plan based on a real repository.

The agent will initially have read-only repository tools.

## Current Implementation Status

### What Has Been Built

The architecture specified in this decision has been implemented:

- ✅ **SimpleAgent** — Direct agent loop implementation with iteration, tool calling, and state management
- ✅ **LLMClient Protocol** — Provider-independent interface enabling integration with different LLM providers
- ✅ **RepositoryTool** — Read-only repository access (list_files, read_file, search_code)
- ✅ **ToolDispatcher** — Routes and validates tool calls before execution
- ✅ **CopilotLLMClient** — Real Copilot LLM integration via GitHub Copilot SDK

### Current Milestone

The agent architecture is foundation-complete. It can:
- Accept requirements and maintain conversation history
- Request completions from real LLMs (Copilot)
- Parse and iterate based on LLM responses
- Execute controlled tool calls through ToolDispatcher
- Validate tool arguments and handle errors

The integration with a real LLM provider (Copilot via Claude Haiku 4.5) is operational.

### Next Milestone

Connect provider-level tool calling from Copilot to EIP's ToolDispatcher, enabling the LLM to invoke repository tools through the provider's native tool execution system rather than through text-based agent iteration.

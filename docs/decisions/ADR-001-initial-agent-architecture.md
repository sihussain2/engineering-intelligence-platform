# ADR-001: Initial Agent Architecture

## Status

Accepted

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

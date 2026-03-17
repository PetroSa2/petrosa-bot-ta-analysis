# Petrosa Agent Guidelines (AGENTS.md)

This document provides critical operational guidelines for LLM agents and developers working across the Petrosa ecosystem.

## 1. Tool Preferences (MANDATORY)

To maximize efficiency and avoid unnecessary browser-based interactions, all agents MUST prioritize CLI tools:

- **GitHub Operations**: Use `gh` CLI for issues, PRs, and project management.
- **Kubernetes Operations**: Use `kubectl` with the provided kubeconfig. Due to TLS certificate issues, always add `--insecure-skip-tls-verify=true`.
- **Code Quality**: Use `make` targets which wrap `ruff`, `pytest`, etc.

## 2. Project Structure & Context

The Petrosa ecosystem consists of multiple services coordinated through `petrosa_k8s`.

- **Primary Reference**: Always read `petrosa_k8s/_bmad-output/project-context.md` at the start of a session.
- **Service Repos**: `petrosa-binance-data-extractor`, `petrosa-tradeengine`, `petrosa-bot-ta-analysis`, `petrosa_k8s`, `petrosa-socket-client`, `petrosa-realtime-strategies`, `petrosa-data-manager`, `petrosa-cio`.

## 3. BMAD Workflow System

This project uses the BMAD (Business-Model-Agent-Development) framework located in `petrosa_k8s/_bmad/`.

## 4. Coding & Testing Standards

- **Language**: Python 3.11+
- **Linter/Formatter**: `ruff` (mandatory).
- **Testing**: `pytest`. Every test MUST have at least one assertion.
- **Coverage**: Maintain a minimum of 40-50% coverage as enforced by CI.
- **OpenTelemetry**: Use the internal `petrosa-otel` package for all instrumentation.

## 5. Commit & PR Process

- **Branching**: `{type}/{issue-number}-{description}`.
- **Messages**: Conventional Commits style.
- **PRs**: Use `gh pr create` with a clear description, linking to the relevant issue.

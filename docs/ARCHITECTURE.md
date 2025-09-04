# Architecture Overview
- Orchestrator coordinates agents via simple message passing.
- Agents: interviewer, evaluator, hints, topic manager.
- Async/await communication, minimal shared state, basic error handling.

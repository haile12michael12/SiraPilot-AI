# SiraPilot AI

SiraPilot AI is a self-hosted job search workspace designed to help you track opportunities with clarity, control, and context.

Instead of managing applications across bookmarks, inboxes, notes, and spreadsheets, you keep one structured record per opportunity. The platform captures listing details, tracks status changes, preserves decision history, and keeps everything connected to the job you are pursuing.

## Why it exists

Job searching often involves fragmented information:

- listing URLs appear in multiple places
- opportunities get reposted or re-opened
- statuses change over time
- notes and decision context are scattered across tools
- application materials are hard to keep organized

SiraPilot AI consolidates that workflow into one local-first system built around a single source of truth per job.

## Core capabilities

- One opportunity, one history: keep listings, notes, status updates, materials, and decisions attached to the same record.
- Smart capture: record supported job details directly from the browser instead of retyping them later.
- Reuse with control: review remembered answers and supported application data before reusing them.
- Repost detection: identify probable reposts while preserving existing history rather than merging blindly.
- Decision support: surface relevant signals such as seniority, pay, requirements, listing age, and company context.
- Kanban visibility: keep every opportunity visible in a local dashboard and move it through the process with confidence.
- Local-first architecture: default to a local SQLite database, with optional synchronization support and extensible integrations.

## How it works

SiraPilot AI combines a browser extension, a local server, and a dashboard:

- Browser extension: capture job data, review decision signals, and update tracked opportunities while browsing.
- API server: store and expose structured job records and workflow state through a local service.
- Dashboard: visualize opportunities, stages, notes, and follow-up actions in a Kanban-style interface.
- AI-ready context: agents can use the app's structured data and OpenAPI schema for job-search assistance and operational workflows.

## See it in action

Watch the demo that follows a job from Gmail to LinkedIn and shows how SiraPilot AI helps maintain context through the hiring process.

https://github.com/user-attachments/assets/9a478d3d-425c-4217-aa50-1cb8c1550dc4

[Download the demo MP4](https://github.com/haile12michael12/SiraPilot-AI/raw/refs/heads/main/docs/videos/job-tracker-demo.mp4)

## Supported integrations

| Surface | Support |
| --- | --- |
| LinkedIn jobs | Capture listing details and support in-page triage on search cards and job detail views |
| LinkedIn job emails in Gmail | Recognize supported messages and add tracker actions |
| Other sites | Add jobs manually from the extension and dashboard |

LinkedIn and supported LinkedIn job emails in Gmail are the primary built-in integrations today. The integration layer is designed to support additional built-in and private adapters without altering the core job model.

## Privacy and security

SiraPilot AI is designed for single-user, self-hosted local use. By default, records remain in a local SQLite database on your machine. Optional Turso synchronization is available for those who want extra flexibility, but the system keeps the core workflow local-first.

The browser extension communicates only with the configured local server and does not rely on third-party analytics. For details on data capture, retention, and permissions, see [Privacy](PRIVACY.md). For the supported local threat model, see [Security](SECURITY.md).

## Installation

For setup and launch instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Typical options include:

- install from source
- run with Docker Compose
- use a packaged Linux/WSL2 release

After setup, open <http://localhost:3456> and load the matching browser extension.

## Documentation map

The project documentation is organized to separate architecture, product workflows, integrations, and operational guidance.

```text
docs/
├── architecture/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── BACKEND_ARCHITECTURE.md
│   ├── FRONTEND_ARCHITECTURE.md
│   ├── EXTENSION_ARCHITECTURE.md
│   ├── AI_ARCHITECTURE.md
│   └── ADR/
│
├── database/
│   ├── ERD.md
│   ├── SCHEMA.md
│   ├── MIGRATIONS.md
│   └── DATA_LIFECYCLE.md
│
├── api/
│   ├── API_CONVENTIONS.md
│   ├── ENDPOINTS.md
│   └── ERROR_HANDLING.md
│
├── ai/
│   ├── AI_FEATURES.md
│   ├── AGENT_DESIGN.md
│   ├── PROMPT_ENGINEERING.md
│   ├── EVALUATION.md
│   └── PRIVACY.md
│
├── integrations/
│   ├── BROWSER_ADAPTERS.md
│   ├── GMAIL_INTEGRATION.md
│   └── PROVIDER_INTEGRATION.md
│
├── security/
│   ├── SECURITY_POLICY.md
│   ├── THREAT_MODEL.md
│   └── DATA_PROTECTION.md
│
├── testing/
│   ├── TEST_STRATEGY.md
│   ├── UNIT_TESTING.md
│   └── E2E_TESTING.md
│
├── deployment/
│   ├── DOCKER.md
│   ├── BACKUP_RESTORE.md
│   └── RELEASE_PROCESS.md
│
└── development/
    ├── CODING_STANDARDS.md
    ├── CONTRIBUTION_GUIDE.md
    └── IMPLEMENTATION_ROADMAP.md
```

## Development and documentation

- Architecture and component boundaries: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Deployment and environment setup: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Feature workflows and capabilities: [docs/FEATURES.md](docs/FEATURES.md)
- API and backend: [apps/api/README.md](apps/api/README.md)
- Dashboard app: [apps/web/README.md](apps/web/README.md)
- Browser extension: [apps/extension/README.md](apps/extension/README.md)
- Developer policy and quality gates: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## License

This project is licensed under the [MIT License](LICENSE).

## Maintainer

SiraPilot AI is maintained by [Hailemichael Assefa](https://github.com/haile12michael12), with a focus on secure APIs, scalable product systems, and practical AI-assisted workflows.

# Treehouse — Use Cases & Test Scenarios

## Target Projects

### 1. Full-Stack Web Apps
- **Example:** Next.js + Express API + Postgres + Redis
- **Conflict without Treehouse:** All agents fight over port 3000, same database, same `.env`
- **Test scenario:** Spawn 3 agents — one on auth, one on API routes, one on frontend. Verify each gets its own port (3101, 3102, 3103) and its own Postgres instance. Both can run `npm run dev` simultaneously without port conflicts.

### 2. Monorepos with Shared Services
- **Example:** Turborepo with `apps/web`, `apps/api`, `packages/shared`
- **Conflict without Treehouse:** Agents modifying shared packages break each other's builds. Dev servers collide on ports.
- **Test scenario:** Spawn 2 agents — one working on `apps/web`, one on `apps/api`. Both need the shared database. Verify each has isolated Docker Compose projects with separate networks.

### 3. Database Migration Work
- **Example:** Django app where multiple agents add new model fields
- **Conflict without Treehouse:** Agent 1 adds `users.email_verified`, Agent 2 adds `users.avatar_url`. Migrations conflict on shared DB, migration numbering collides.
- **Test scenario:** Spawn 2 agents that each add a migration to the same Django app. Verify each has its own Postgres and can run `python manage.py migrate` independently. Then merge sequentially and verify migration ordering is resolved.

### 4. Microservices
- **Example:** 3-4 services communicating via localhost (user-service, order-service, notification-service)
- **Conflict without Treehouse:** Each agent working on a different service needs the full stack running. Ports and service discovery collide.
- **Test scenario:** Spawn agents for each microservice. Verify each gets its own Docker Compose project with isolated service mesh. Services within each agent's environment can communicate, but don't cross-talk between agents.

### 5. Django/Rails Apps with Background Jobs
- **Example:** Rails + Sidekiq + Redis + Postgres
- **Conflict without Treehouse:** Agents share Redis queues, enqueuing and processing each other's test jobs. DB state corrupted by concurrent migrations.
- **Test scenario:** Spawn 2 agents — one fixing a Sidekiq worker, one fixing an API endpoint. Verify each has its own Redis instance (port 6401 vs 6402) and own Postgres. Jobs enqueued by agent-1 don't appear in agent-2's Redis.

### 6. E-Commerce Platforms
- **Example:** Shopify-style app with checkout, inventory, payments, notifications
- **Conflict without Treehouse:** Agents share Stripe test keys, payment state, webhook endpoints. Two agents processing the same test payment causes chaos.
- **Test scenario:** Spawn agents for checkout and inventory. Each gets isolated `.env` with its own webhook callback ports. Verify Stripe test webhooks route to the correct agent's environment.

### 7. CI/CD and Integration Test Suites
- **Example:** Any project with integration tests that hit a real database
- **Conflict without Treehouse:** Multiple agents running `pytest` or `npm test` simultaneously corrupt each other's test data.
- **Test scenario:** Spawn 3 agents that each run the full test suite. Verify all 3 can run concurrently with no test failures caused by shared state.

---

## Demo Test Plan

### Minimal Demo (5 minutes)
1. Start with a simple Express + Postgres app
2. Run `treehouse init`
3. Run `treehouse spawn auth "add JWT authentication"` and `treehouse spawn ui "redesign login page"`
4. Open `treehouse dashboard` — show both agents running with live logs
5. Show that both have isolated databases and ports
6. Merge `auth` first (clean merge), then `ui` (potential conflict resolved by AI)

### Full Demo (10 minutes)
1. Start with a Next.js + Express + Postgres + Redis app
2. `treehouse init` — detects `docker-compose.yml`
3. Spawn 4 agents:
   - `treehouse spawn auth "add OAuth2 with Google"`
   - `treehouse spawn api "add REST endpoints for user profiles"`
   - `treehouse spawn ui "build dashboard page with charts"`
   - `treehouse spawn tests "write integration tests for auth flow"`
4. Show dashboard with all 4 agents running simultaneously
5. Show isolated Docker Compose projects: `docker ps` shows 4 separate Postgres containers, 4 Redis containers
6. Show each agent's `.env` has unique ports
7. Wait for agents to complete
8. Sequential merge: tests → auth → api → ui
9. Show AI merge agent resolving a conflict between auth and api (both touched user model)

### Stress Test
1. Spawn 8 agents on a medium-sized repo
2. Verify port allocation: 3101-3108, 5501-5508, 6401-6408
3. Verify all 8 Docker Compose projects start without name/network/volume collisions
4. Verify `docker ps` shows 8 isolated sets of containers
5. Kill 2 agents, verify cleanup (worktree removed, containers stopped, ports released)
6. Spawn 2 new agents, verify they reuse released ports

---

## Test Repository Candidates

For building and testing Treehouse, we need sample repos that exercise the isolation:

| Repo Type | Why It's Good for Testing |
|-----------|--------------------------|
| Express + Postgres starter | Simple, one DB, one port, fast to clone |
| Django + Celery + Redis | Multiple services, migrations, background jobs |
| Next.js + Supabase | Full-stack JS, database, auth |
| Rails + Sidekiq + Postgres | Classic multi-service app |
| FastAPI + SQLAlchemy + Redis | Python equivalent of the above |

For the hackathon demo, use the simplest one (Express + Postgres) to minimize setup time and maximize reliability.

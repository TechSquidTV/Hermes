# Hermes Real-Time Updates Documentation

This directory contains comprehensive documentation for migrating Hermes from polling-based updates to Server-Sent Events (SSE) for real-time functionality.

---

## Document Overview

### 1. [Real-Time Updates Research](./real-time-updates-research.md)
**Purpose:** Comprehensive research and planning document

**Contents:**
- Complete analysis of all 11 current polling mechanisms
- Detailed architecture review (Docker, Caddy, Redis, FastAPI)
- SSE vs WebSocket technology comparison
- Full implementation plan (5 phases, 5 weeks)
- Migration strategy and success metrics
- Testing considerations and appendices

**Read this first if you want to:**
- Understand the current system in detail
- Learn why SSE was recommended over WebSocket
- Review the implementation plan and timeline
- Understand deployment architecture considerations

**Size:** ~400 lines | **Read time:** 30-45 minutes

---

### 2. [SSE Implementation Guide](./sse-implementation-guide.md)
**Purpose:** Step-by-step technical implementation guide

**Contents:**
- Prerequisites and dependencies
- Phase 1: Backend SSE infrastructure (code examples)
- Phase 2: Frontend SSE client (complete hooks)
- Phase 3: Download progress implementation
- Phase 4: Queue updates implementation
- Complete testing guide
- Troubleshooting section

**Read this when you're ready to:**
- Start implementing SSE
- Write the backend SSE endpoints
- Create frontend SSE hooks
- Test the implementation
- Debug issues

**Size:** ~800 lines | **Read time:** 1-2 hours (including code review)

---

### 3. [SSE Configuration Guide](./sse-configuration-guide.md)
**Purpose:** Quick reference for configuration and deployment

**Contents:**
- Single feature flag design philosophy
- Environment variable reference
- Configuration scenarios (dev, prod, rollback)
- How it works (enabled vs disabled)
- Verification commands
- Troubleshooting tips
- Production deployment checklist

**Read this when you need to:**
- Configure SSE in development
- Deploy to production
- Roll back quickly
- Verify SSE is working
- Troubleshoot configuration issues

**Size:** ~300 lines | **Read time:** 10-15 minutes

---

## Quick Start

### For Developers (First Time)

1. **Read the research document** to understand the "why" and "what"
   - Start with: [Real-Time Updates Research](./real-time-updates-research.md)
   - Focus on: Current system, technology comparison, recommended solution

2. **Review the implementation guide** to learn the "how"
   - Read: [SSE Implementation Guide](./sse-implementation-guide.md)
   - Follow: Phase-by-phase implementation steps

3. **Use the configuration guide** as a reference
   - Keep open: [SSE Configuration Guide](./sse-configuration-guide.md)
   - Use for: Environment setup, troubleshooting

### For DevOps/Deployment

1. **Skim the research document** for architecture understanding
   - Focus on: "Architecture Analysis" section
   - Understand: Docker, Caddy, network considerations

2. **Use the configuration guide** for deployment
   - Follow: Production deployment checklist
   - Reference: Environment variables, verification commands

### For Quick Reference

**Just want to enable SSE?**
- See: [SSE Configuration Guide - Scenario 1](./sse-configuration-guide.md#scenario-1-development-with-sse)

**Need to disable SSE quickly?**
- See: [SSE Configuration Guide - Scenario 4](./sse-configuration-guide.md#scenario-4-production-without-sse-safe-rollback)

**Want to test if SSE is working?**
- See: [SSE Configuration Guide - Verification Commands](./sse-configuration-guide.md#verification-commands)

---

## Key Concepts

### Single Feature Flag Design

Hermes uses a **simple all-or-nothing approach** for SSE:

**Backend:**
```bash
HERMES_ENABLE_SSE=true   # Enables ALL SSE features
```

**Frontend:**
```bash
VITE_SSE_ENABLED=true    # Uses SSE for ALL real-time updates
```

**Benefits:**
- ✓ Simple to configure
- ✓ Easy to test (on or off)
- ✓ Quick rollback (one flag)
- ✓ No partial states to debug

---

## Implementation Status

**Current Status:** Research Complete, Ready for Implementation

**Timeline:** 5 weeks (1 week per phase)

**Risk Level:** Low (automatic fallback to polling)

---

## FAQ

### Q: Will this break existing functionality?
**A:** No. SSE is additive. Polling remains as fallback. You can disable SSE anytime.

### Q: Can I rollback quickly if there are issues?
**A:** Yes! Set `VITE_SSE_ENABLED=false` for instant rollback with zero downtime.

### Q: What about WebSocket instead of SSE?
**A:** See [Technology Comparison](./real-time-updates-research.md#technology-comparison-sse-vs-websockets) in the research document. SSE is recommended for Hermes' use case.

### Q: How much will resource usage improve?
**A:** Expected ~97% reduction in HTTP requests.

---

*For questions or updates to this documentation, contact the development team.*

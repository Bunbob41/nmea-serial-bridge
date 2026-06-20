# Requirements Checklist: Fleet Multi-Stream

**Purpose**: Gate before `/speckit-plan` and `/speckit-implement`  
**Created**: 2026-06-18

---

## Stakeholder clarity

- [x] Max 8 streams
- [x] Fleet tab in Modern
- [x] Per-stream network modes
- [x] One Primary stream for HUD
- [x] Per-stream monitoring only (no host CPU/RAM v1)
- [x] Manual start + optional auto-start (off default)

## Spec completeness

- [x] User stories P1–P2 with acceptance scenarios
- [x] FR-501–FR-519 defined
- [x] Success criteria SC-501–SC-505
- [x] Scope in / out table
- [x] Constitution carve-out documented
- [x] Edge cases listed

## Design artifacts

- [x] `research.md` — worker model decision
- [x] `data-model.md` — entities + validation
- [x] `contracts/stream-worker.md`
- [x] `contracts/fleet-supervisor.md`
- [x] `contracts/fleet-ui.md`
- [x] `contracts/fleet-persistence.md`
- [ ] `plan.md` — **pending** `/speckit-plan`
- [ ] `tasks.md` — **pending** `/speckit-tasks`
- [ ] `quickstart.md` — **pending** plan phase

## Pre-implement gates (constitution)

- [ ] Plan cites `verify_all.py` + new `test_fleet_*.py`
- [ ] Plan updates `docs/OPERATOR_GUIDE.md`
- [ ] No bridge protocol logic in `ui/fleet_*.py` widgets
- [ ] Bounded queues / coalesced stats in supervisor design
- [ ] Version bump strategy noted (likely **minor** 1.36.0)

## Open for plan phase

- [ ] Web API behavior when fleet active
- [ ] Control tab Start vs fleet precedence
- [ ] Discovery integration with fleet COM list

---

**Status**: Ready for `/speckit-plan` after API budget reset.

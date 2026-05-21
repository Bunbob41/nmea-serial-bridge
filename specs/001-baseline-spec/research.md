# Research: Product Baseline (As-Built)

## R1 — What “baseline” means for Spec Kit

**Decision**: Baseline delivery is **traceability + operator doc alignment**, not re-implementation of existing bridge features.

**Rationale**: Spec states v1.4.9 as-built; `test_udp_fanout.py` and CHANGELOG v1.4.2–v1.4.3 already encode fan-out behavior.

**Alternatives considered**:
- Rebuild features from spec → rejected (duplicate work, regression risk).
- Code-only baseline with no docs → rejected (SC-001/SC-002 require operator-facing clarity).

## R2 — Fan-out testing without a second bridge

**Decision**: Document **one bridge + two UDP clients** (register peers by sending datagrams; verify serial→net with fan-out on/off).

**Rationale**: Matches `bridge_core._udp_peers` design and FR-020; README incorrectly implied “last sender only” as the only mode.

**Alternatives considered**:
- Second bridge instance → rejected (port conflict, operator confusion).
- Kernel tap → out of scope (FR-019).

## R3 — Documentation authority when sources disagree

**Decision**: Order of truth: **spec baseline → CHANGELOG → OPERATOR_GUIDE → README** for behavior; README updated to match.

**Rationale**: Spec assumption explicitly notes README lag on fan-out.

## R4 — Version bump level

**Decision**: **Patch** bump (1.4.9 → 1.4.10) for documentation and traceability artifacts.

**Rationale**: No bridge behavior change; constitution Principle IV still requires CHANGELOG entry for operator-visible doc fixes.

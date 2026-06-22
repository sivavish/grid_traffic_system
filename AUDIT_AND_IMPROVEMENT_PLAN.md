# ASTraM Realism Audit and Improvement Plan

## Audit Summary

The system now has stronger data flow than a demo, but several surfaces still need production realism.

### 1. Hardcoded Values
- Route naming and diversion defaults still exist in the route engine fallback path.
- UI URLs were previously hardcoded to localhost; they now need environment-driven configuration everywhere.
- Some visual defaults in the map and severity chips remain static presentation values.

### 2. Simulated Data
- Event feed simulation still exists as a fallback and must be clearly labeled when used.
- Ripple, route, and action outputs are derived from the cleaned dataset, but some horizons still use deterministic presentation defaults.

### 3. Placeholder Outputs
- Some history and route explanations were generic and not exposed fully in the UI.
- The command center lacked a clear operational overview and evidence trace.

### 4. Static Route / Action Logic
- The original implementation used fixed route libraries and threshold-driven deployment rules.
- These have been partially replaced, but the user-facing layers still need clearer explanation and visibility.

### 5. Mock Event Feeds
- Feed items needed source metadata, source URLs, reliability, and simulation status.
- Source attribution was not visible in the UI.

### 6. Unused Dataset Columns
- The cleaned dataset contains many fields not reflected in the UI or the summary endpoints.
- More of the dataset should be surfaced through overview metrics and historical match cards.

### 7. Backend Outputs Not Visible in UI
- Prediction reasoning, route rationale, and historical evidence were not visible enough.
- Dataset stats and top matches were hidden.

### 8. Frontend Cards Not Connected to Backend
- Several panels displayed only static section chrome rather than data-backed content.
- The map lacked a timeline and legend, reducing operational realism.

### 9. Missing Production Features
- No explicit command-center overview endpoint.
- No source attribution badges on feed cards.
- No visible timeline controls for ripple propagation.
- No command replay or historical match explorer yet.

## Improvement Plan

### Critical Fixes
1. Add metadata-rich event feed items with source URLs, verification state, reliability score, and event category.
2. Expose a command-center overview endpoint with active incidents, severity counts, delay, clearance, and affected corridors.
3. Add historical match cards and visible prediction reasoning to the UI.
4. Add a map timeline and legend so ripple propagation can be inspected over time.

### Enhancements
1. Expand route and police command panels with explicit rationale.
2. Surface dataset coverage and risk ranking.
3. Add historical replay and command replay in a later pass.
4. Add authentication and PostgreSQL persistence after the command-center view is stabilized.

## Risks
- Some feed sources may remain simulated until external RSS/public URLs are configured.
- Historical matching remains constrained by the quality and locality of the cleaned dataset.
- Full production auth and database persistence are still outstanding.

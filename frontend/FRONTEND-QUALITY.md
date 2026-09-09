# Frontend quality guardrails

This frontend is an ERP workspace, not a marketing landing page. New UI should prioritize operational clarity, information density, predictable workflows, and accessibility.

## Avoid

- Decorative gradients, aurora/glow backgrounds, heavy glassmorphism, or oversized shadows.
- Reusing `bento-card` as a default layout pattern for every section.
- Gradient primary buttons when a normal filled/light button is clearer.
- Adding a new one-off visual treatment when an existing component or token can express the same state.
- Growing shared components into unrelated feature-specific containers.

## Prefer

- Solid surfaces with restrained borders and shadows.
- Consistent compact radii and spacing.
- Tables, filters, forms, and workflow actions as first-class ERP UI.
- Explicit loading, empty, error, and success states.
- Small, composable feature components with clear responsibilities.
- Business-oriented labels and hierarchy over marketing language.

## Refactor rule

When a shared component becomes responsible for unrelated concerns, split it rather than adding another prop or conditional branch. Preserve behavior first; simplify structure second.

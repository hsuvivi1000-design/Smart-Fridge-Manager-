# Figma Design System Rules

These rules apply when implementing or updating Figma-driven UI in this project.

## Project Context

- Frontend framework: Streamlit with Python.
- Main UI entrypoint: `streamlit_app.py`.
- Theme and layout CSS: `ui/styles.py`.
- UI constants and token-like settings: `ui/config.py`.
- Backend inventory and expiry logic must remain in `app/` and `tools/`.

## Figma MCP Flow

1. For Figma-to-code work, fetch the exact frame with `get_design_context` and keep the screenshot as the visual source of truth.
2. If the node is too large, inspect with `get_metadata`, then fetch smaller child nodes.
3. Reuse existing app structure before adding new abstractions.
4. Translate Figma layout into Streamlit primitives plus scoped CSS in `ui/styles.py`.
5. Validate with Python compile checks and a running Streamlit smoke test.

## Streamlit Implementation Rules

- Keep the first screen as the usable app, not a landing page.
- Prefer dense, scannable operational UI: dashboard metrics, inventory list, chat workbench, tool trace.
- Keep cards at `8px` border radius or less.
- Do not nest cards inside cards.
- Use restrained color tokens from `ui/styles.py`; do not hardcode one-off colors in `streamlit_app.py`.
- Place reusable strings, categories, units, and model settings in `ui/config.py`.
- Escape dynamic text before injecting it into `unsafe_allow_html` blocks.
- Preserve the existing data flow through `InventoryAgent`, `estimate_expiry_date`, and `ChefAgent`.

## Visual System

- Primary accent: fridge-green / teal for productive actions.
- Secondary accent: blue only for system or trace affordances.
- Status colors: green for fresh, amber for warning, red for expired or urgent.
- Typography should remain compact and readable, using Inter/Noto Sans TC/Microsoft JhengHei fallback.
- UI must fit desktop and mobile without text overlap.

## Validation

- Run `.venv\Scripts\python.exe -m compileall streamlit_app.py ui app agents tools`.
- Run `.venv\Scripts\python.exe verify_merge.py`.
- Confirm `http://127.0.0.1:8501` returns `200 OK`.
- If Playwright is available, capture a screenshot at desktop and mobile widths before finishing.

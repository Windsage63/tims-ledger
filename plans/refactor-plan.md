# Refactor Plan

Right now this is just a memory dump of where we see duplication and what we should tackle first. We will update this as we go.

## **Highest-Value Simplifications**

1. Shared page shell: `frontend/html/*.html`
Every page repeats the Tailwind config, font imports, body background, sidebar nav, module card, and large layout wrapper. A shared shell would reduce the biggest duplication.

Best options:

  - FastAPI/Jinja templates: convert pages from static HTML to templates with a shared `base.html`.
  - Lightweight HTML partial loader: keep static pages, load shared fragments like sidebar/header with JS.
  - Build-time generation: keep authoring templates, generate static HTML files.

My preference here: FastAPI/Jinja templates if we’re comfortable moving pages from static files to rendered routes. It is clean and boring in the best way.

1. Shared frontend utilities: `frontend/js/*.js`
These repeat across many files:

  - `currency`
  - `setText`
  - `escapeHtml`
  - `extractErrorMessage`
  - `renderNavState`
  - `dollarsInput`
  - `centsFromInput`
  - API request helpers

A `frontend/js/shared.js` loaded before page scripts would be an easy win.

1. Shared nav behavior
Every page has a copy of the side-nav HTML, and every page JS has a copy of active nav highlighting. This should become one shared nav renderer or template partial.

2. Shared API request wrapper
`invoices.js` and `payments.js` already have `requestJson`; other screens do direct `fetch` with similar error handling. A shared helper could normalize envelopes, detail arrays, and fallback errors.

3. Shared form/input formatting
Money and time conversion are duplicated:

  - cents ↔ dollars in payments/expenses/projects
  - minutes ↔ hours in time/invoices
  - quantity formatting in expenses

A small `formatters.js` would make these consistent.

1. Repeated browse/editor page pattern
Customers, projects, time, expenses, invoices, and payments all follow roughly:

  - state object
  - load bootstrap
  - filter rows
  - render metrics
  - render table/list
  - render editor
  - bind events

I would not abstract this too aggressively yet, but shared helpers for filters, empty states, selected row classes, and button busy states would pay off.

1. Backend CRUD route repetition: `backend/app/main.py`
Most create/update routes repeat:

  - open connection
  - call domain function
  - catch `ValueError`
  - return `response_envelope`
  - handle `404`

Could add small helpers, but I’d be conservative. FastAPI route clarity is valuable.

1. Backend SQL/row mapping pattern
Domain modules repeat:

  - `*_select_sql()`
  - `row_to_*()`
  - `fetch_*()`
  - `fetch_one()`

This is okay for now. I would avoid building a mini ORM unless this grows much more.

1. Repeated project/customer lookup logic
`project_lookup`, `customer_lookup`, `resolve_project`, `resolve_project_customer`, and rate/project resolution are scattered across modules. Some of this could be centralized in `projects.py`, but it’s not urgent.

2. Docs and product constants
Expense categories are code constants but also documented. That is fine, but if categories become configurable later, docs/code drift will return. For now, keep them in code and update docs with any category change.

## **Suggested Refactor Order**

1. Create shared frontend utilities.
Low risk, immediate reduction in repeated JS.

2. Extract shared nav/sidebar/page chrome.
Biggest HTML cleanup. Choose Jinja or static partial loading first.

3. Extract shared Tailwind config/style includes.
Right now every page embeds the same config. This should become one shared script or template block.

4. Clean page-specific JS after utilities exist.
Replace repeated functions page by page rather than in one giant sweep.

5. Consider backend helper cleanup later.
The backend duplication is less painful than the frontend duplication right now.

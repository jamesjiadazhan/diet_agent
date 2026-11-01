# Instructions for calling AI agents

1. Recognize food identities, preparation and edible portions from user text or
   photos. Respect explicit user quantities. Recognition is the agent's task;
   this toolkit does not invoke an image model or external API.
2. Call `search_foods` or `diet-assess search`. Confirm ambiguous candidates.
   Use the returned internal `food_id`; never manufacture a food code or FDC ID.
3. Send structured observations with edible grams or a specific returned
   measure ID. Generic cups, fluid ounces and as-purchased masses are rejected
   without a defensible food-specific conversion.
4. Inspect `status`, `unresolved`, missing amounts, provenance and warnings.
   `partial` is not a complete intake. `needs_clarification` requires returning
   to the user or confirming one of the explicit candidates.
5. Explain which weights were estimated. Preserve raw/cooked distinctions.
   Treat `precomputed_reference` values marked unvalidated as references, not
   validated Food Compass outputs.
6. For daily results, aggregate the day's foods in one request. HEI is calculated
   from nutrient and pattern totals, not by averaging food-level HEI scores.

Any AI coding agent that can run local Python may use the API/CLI. A host must
explicitly support launching local stdio MCP for the optional MCP interface.
Installing from GitHub does not magically provide code execution or MCP support
to an arbitrary consumer chat application.

Input and output JSON Schemas are in `schemas/`. The six MCP tools use the same
core functions as Python and CLI; protocol compatibility is explicitly pinned
to MCP 2024-11-05, 2025-03-26 and 2025-06-18. No network listener is started.

Example host configuration (adjust the installed executable path and database):

```json
{
  "mcpServers": {
    "diet-agent": {
      "command": "/absolute/path/to/venv/bin/diet-assess",
      "args": ["mcp", "--database", "/absolute/path/to/generic-fndds-2021-2023-v1.sqlite"]
    }
  }
}
```

Tool results, profiles and derived summaries are local data. The agent's own
host may send its conversation or images elsewhere; that is separate from this
package, which does not upload intake records or persist a user log.

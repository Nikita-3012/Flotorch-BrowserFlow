# --- Custom guardrail create (edit values here, then rerun the suite) ---
# Keyword type (Type dropdown default: Keyword) — one keyword per Action
CUSTOM_GUARDRAIL_KEYWORD_BY_ACTION: dict[str, str] = {
    "block": "racism",
    "redact": "destroy",
    "log": "force",
    "replace": "escalate",
}
CUSTOM_GUARDRAIL_KEYWORD_REPLACE_WITH = "resolve"

# Regex type — select Type → Regex; one pattern per Action
CUSTOM_GUARDRAIL_REGEX_BY_ACTION: dict[str, str] = {
    "block": r"^\+91\s\d{10}$",
    "redact": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
    "log": r"^\d{6}$",
    "replace": r"^\+91\s\d{10}$",
}
CUSTOM_GUARDRAIL_REGEX_REPLACE_WITH = "[MOBILE_NUMBER]"

# AWS Bedrock provider guardrail (Add Provider Guardrail → Guardrail dropdown).
# Supported actions in UI: Block, Redact, Replace, Log.
AWS_BEDROCK_GUARDRAIL_ID = "guardrail-12-11"
AWS_BEDROCK_GUARDRAIL_REPLACE_WITH = "[REDACTED_BY_AWS]"

# Playground queries after guardrail-test model (Keyword guardrails — edit here)
GUARDRAIL_PLAYGROUND_KEYWORD_QUERIES: dict[str, str] = {
    "block": "What is racism",
    "redact": "what is destroy",
    "log": "What does force mean?",
    "replace": "What does escalate mean?",
}

# Agent must place this exact token in `memory` when Step 3 falls back to Default Workspace (detected in Python logs).
WORKSPACE_FALLBACK_TOKEN = "WORKSPACE_FALLBACK_DEFAULT"
WORKSPACE_GATE_FAILED_TOKEN = "WORKSPACE_GATE_FAILED"

# Appended to browser-use Agent system prompt (both login + workflow): XPath click fallback via evaluate().
AGENT_EXTEND_SYSTEM_MESSAGE = """
BASE MODEL / PROVIDER NAMES ARE NOT URLS (critical — FloTorch guardrails & models):
- Strings like `amazon.nova-micro-v1:0`, `llama-3.1-8b-instant`, or `gpt-4.1-nano` are **Bedrock/vendor model IDs** for dropdown selection inside https://console.flotorch.cloud/ only.
- **NEVER** use the navigate tool (or address bar) to open `https://amazon.nova`, `amazon.nova-micro-v1:0`, or any model-id string as a website — that is wrong and will fail (ERR_NAME_NOT_RESOLVED).
- To select a base model: stay on the FloTorch console → Model Registry → pipeline **Models** column → open the **model dropdown** after the org provider is set → pick the row matching the exact model id text.

CLICK FALLBACK (when normal click(index) misses, errors, or the control has no index):
- Scroll the control into view first (scroll inside modals/panels if needed); wait briefly; retry click(index) once.
- Then use the evaluate tool to run compact JavaScript that locates the element with XPath via document.evaluate, then calls click() on the node (or scrollIntoView({block:'center'}) then click).
- XPath tips: match visible text with //button[contains(normalize-space(.),'Publish')] or exact text //*[normalize-space()='Save Configuration']; use //*[@aria-label='…'] when present; for icon-only controls, target a stable ancestor button or link.
- Wrap JS in an IIFE with try/catch; return a short status string for the agent memory.
- Prefer this over blind coordinate clicks unless evaluate repeatedly returns no element (then note overlay/z-index issues).

VUETIFY / REKA DROPDOWNS / role=option (FloTorch provider lists — use early if click(index) logs "no visible quad" or selection stays unchecked):
- FloTorch uses **Reka** (Radix-style). Open combobox options are often **teleported** into `[data-reka-popper-content-wrapper]` (fixed position), not under the `[role=dialog]` node. The dialog may show `pointer-events: none` while a popper is open, which breaks **coordinate** clicks on the wrong layer — programmatic `.click()` on the real option node is more reliable.
- Prefer the evaluate tool **before** repeating the same index: find the option by visible title, `scrollIntoView`, then `click()`.

PROVIDER CREATE MODALS — SERVICE (no Type dropdown on org/workspace forms):
- Open the **Service** dropdown and tick **every** Service option. Use "Select All" if present. There is no separate Type dropdown on these screens.
- Template (replace EXACT_PROVIDER_TITLE_FROM_TASK with the task string, or inject JSON.stringify result from the task):
  (() => { try { const want = 'EXACT_PROVIDER_TITLE_FROM_TASK'; const poppers = [...document.querySelectorAll('[data-reka-popper-content-wrapper]')]; let opts = []; for (const p of poppers) { opts.push(...p.querySelectorAll('[role=option]')); } if (!opts.length) opts = [...document.querySelectorAll('[role=option]')]; const el = opts.find(n => n.textContent && n.textContent.trim().includes(want)); if (!el) return 'no-match'; el.scrollIntoView({ block: 'center', inline: 'nearest' }); el.click(); return 'clicked'; } catch (e) { return String(e); } })()
- If one .click() does not set selected state, retry with a child: const inner = el.querySelector('.v-list-item-title, .v-list-item__content, [data-slot]') || el; inner.click();

PUBLISH MODEL (pipeline builder — use instead of index-click on Publish):
- Open dialog:
  (() => { try { const btn = document.querySelector('button[aria-label="Publish Model"]'); if (!btn || btn.disabled) return 'publish-not-ready'; btn.scrollIntoView({ block: 'center' }); btn.click(); return 'clicked'; } catch (e) { return String(e); } })()
- Detect publish dialog:
  (() => { try { const dlg = [...document.querySelectorAll('[role=dialog]')].find(d => /publish/i.test(d.textContent || '')); return dlg ? { open: true } : { open: false }; } catch (e) { return { open: false, error: String(e) }; } })()
- Confirm inside dialog (after Summary + "Mark as latest"):
  (() => { try { const dlg = [...document.querySelectorAll('[role=dialog]')].find(d => /publish/i.test(d.textContent || '')); if (!dlg) return 'no-dialog'; const btn = [...dlg.querySelectorAll('button')].find(b => /^publish$/i.test((b.textContent || '').trim())); if (!btn) return 'no-inner-publish'; btn.click(); return 'confirmed'; } catch (e) { return String(e); } })()

WORKSPACE LIST (Step 4 — do NOT index-click the first "automation-..." row; truncated names collide):
- After typing the full workspace name in search, wait ~2s, then run evaluate with `want` = full workspace name OR run suffix check with run uid.
- Click workspace row by exact suffix (replace RUN_UID with this run's uid from the task):
  (() => { try { const uid = 'RUN_UID'; const links = [...document.querySelectorAll('a[href*="/workspaces/"]')]; const el = links.find(a => (a.textContent || '').includes(uid)); if (!el) return 'no-match'; el.scrollIntoView({ block: 'center' }); el.click(); return 'clicked:' + (el.textContent || '').trim().slice(0, 80); } catch (e) { return String(e); } })()
- Verify entered workspace (replace RUN_UID):
  (() => { const uid = 'RUN_UID'; const href = location.href; const body = document.body.innerText || ''; return href.includes('/workspaces/') && body.includes(uid) ? 'workspace-ok' : 'workspace-wrong'; })()
""".strip()

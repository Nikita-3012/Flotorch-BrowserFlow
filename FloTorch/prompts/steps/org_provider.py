"""STEP 2: Create organization (global) provider."""

from run_context import RunContext


def step_org_provider(ctx: RunContext) -> str:
    fp = ctx.first_provider
    return f"""
==============================
STEP 2: CREATE GLOBAL PROVIDER
==============================
- Go to Provider section
- Click Create Organization Provider

Inside the modal:
- In the "Name" field:
   Enter exactly (all lowercase): {ctx.org_provider_name}

- In the "Description" field:
   Enter (all lowercase): {ctx.org_provider_description}

- In the "Provider" dropdown:
   - Click the Provider dropdown first
   - Search/select ONLY the provider type: {fp['name']}
   - Do NOT type {ctx.org_provider_name} here
   - Do NOT use the generated provider name in the Provider dropdown

- After selecting the provider type, additional credential fields will appear

- Fill provider credential fields using ONLY the values from {fp['fields']}

Rules:
- For each credential field shown in the UI, match its label with the exact key in {fp['fields']}
- Enter the corresponding value from {fp['fields']} into that field
- Never type placeholder/example values like "test-api-key", "your-api-key", or sample URLs
- Always use the real fetched configuration values

Field mappings:
- "API Key" field → {fp['fields'].get('API Key', '')}
- "Base URL" field → {fp['fields'].get('Base URL', '')}
- "Region" field → {fp['fields'].get('Region', '')}
- "Project ID" field → {fp['fields'].get('Project ID', '')}
- "Service Account" field → {fp['fields'].get('Service Account', '')}
- "Private Key" field → {fp['fields'].get('Private Key', '')}

 -Scroll down inside the modal if needed

- Click "Create Provider"

- After creation, search for {ctx.org_provider_name} in the provider search bar and validate it appears in results
"""

# FDSL Frontend Component Architecture

## Overview

FDSL components follow a **two-layer architecture**:
1. **Primitive Building Blocks** - Reusable UI elements (`lib/primitives/`)
2. **FDSL Components** - Entity-bound data components (`lib/components/`)

---

## Architecture Pattern

### **Layer 1: Primitives** (`lib/primitives/`)

**Purpose**: Generic, reusable Svelte components with no FDSL-specific logic.

**Characteristics**:
- Accept data via props
- No API calls, no entity awareness
- Pure presentation logic
- Can be used standalone

**Example**: `Card.svelte`
```svelte
<script>
  export let title = "";
  export let fields = [];  // [{label, value}]
  export let highlight = null;
</script>

<div class="card">
  <h3>{title}</h3>
  {#each fields as field}
    <div class="field" class:highlight={field.label === highlight}>
      <span class="label">{field.label}</span>
      <span class="value">{field.value}</span>
    </div>
  {/each}
</div>
```

---

### **Layer 2: FDSL Components** (`lib/components/`)

**Purpose**: Entity-bound components that fetch data and bind to primitives.

**Characteristics**:
- Fetch data from REST/WebSocket APIs
- Transform entity attributes into primitive props
- Use `<svelte:fragment>` to render primitives
- Handle loading/error states

**Example**: `CardComponent.svelte`
```svelte
<script>
  import { onMount } from 'svelte';
  import Card from '$lib/primitives/Card.svelte';

  export let entityName;
  export let fields;
  export let title;
  export let highlight;

  let data = null;
  let error = null;

  onMount(async () => {
    try {
      const res = await fetch(`/api/${entityName.toLowerCase()}`);
      data = await res.json();
    } catch (e) {
      error = e.message;
    }
  });

  $: fieldData = fields.map(f => ({
    label: f,
    value: data?.[f] ?? '-'
  }));
</script>

{#if error}
  <div class="error">{error}</div>
{:else if data}
  <svelte:fragment>
    <Card {title} fields={fieldData} {highlight} />
  </svelte:fragment>
{:else}
  <div class="loading">Loading...</div>
{/if}
```

---

## Component Implementation Checklist

For each new component type, implement these 4 pieces:

### ✅ **1. TextX Grammar** (`functionality_dsl/language/grammar.tx`)

Add component definition to grammar:

```textx
ComponentCard:
  'Component<Card>' name=ID
    'entity:' entity=[Entity]
    'fields:' fields=FieldList
    ('title:' title=STRING)?
    ('highlight:' highlight=STRING)?
  'end'
;
```

### ✅ **2. Component Type Registry** (`functionality_dsl/language/component_types.py`)

Register component with its properties:

```python
COMPONENT_TYPES = {
    # ... existing types
    "Card": {
        "required": ["entity", "fields"],
        "optional": ["title", "highlight"],
        "category": "data_display",
        "description": "Multi-field card display"
    },
}
```

### ✅ **3. Jinja Template** (`functionality_dsl/templates/frontend/`)

Create template for prop passing:

```jinja
{# templates/frontend/card_component.svelte.jinja #}
<script>
  import CardComponent from '$lib/components/CardComponent.svelte';
</script>

<CardComponent
  entityName="{{ entity_name }}"
  fields={[{% for field in fields %}"{{ field }}"{% if not loop.last %}, {% endif %}{% endfor %}]}
  {% if title %}title="{{ title }}"{% endif %}
  {% if highlight %}highlight="{{ highlight }}"{% endif %}
/>
```

### ✅ **4. Primitive Scaffold** (`base/frontend/src/lib/primitives/`)

Create base Svelte component:

```svelte
<!-- lib/primitives/Card.svelte -->
<script>
  export let title = "";
  export let fields = [];
  export let highlight = null;
</script>

<div class="card">
  <!-- UI implementation -->
</div>

<style>
  /* Component styles */
</style>
```

### ✅ **5. FDSL Component Wrapper** (`base/frontend/src/lib/components/`)

Create entity-bound wrapper:

```svelte
<!-- lib/components/CardComponent.svelte -->
<script>
  import { onMount } from 'svelte';
  import Card from '$lib/primitives/Card.svelte';

  export let entityName;
  export let fields;
  // ... fetch logic
</script>

<svelte:fragment>
  <Card {title} fields={fieldData} {highlight} />
</svelte:fragment>
```

---

## Component Categories

### **Data Display** (REST-based)
- `Metric` - Single value display
- `Card` - Multi-field structured view
- `Table` - Array data display
- `PieChart` - Proportional visualization
- `BarChart` - Comparison visualization

### **Real-Time** (WebSocket-based)
- `LiveMetrics` - Streaming metrics
- `LiveChart` - Streaming graph
- `LiveFeed` - Message stream

### **Interactive** (Mutation-capable)
- `Form` - CRUD operations
- `Button` - Action trigger

---

## Styling Guidelines

- Use CSS variables for theming
- Keep primitives unstyled (or minimally styled)
- Apply business-specific styles in FDSL components
- Support dark/light modes via CSS variables

---

## Example: Complete Card Component

See `Card.svelte` as the canonical example following this pattern.

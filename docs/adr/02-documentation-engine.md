---
title: 2. Documentation Engine
icon: material/book-cog-outline
---

# :material-book-cog-outline: 2. Documentation Engine: MkDocs and Material

!!! abstract "Context and Problem Statement"
    LychD is a complex system combining ancient lore (The Hexanomicon) with modern engineering (Python, Podman, Systemd). The documentation must be as immersive as it is technical.

    Furthermore, a core tenet of LychD is **xDDD (eXtreme Documentation Driven Development)**, where the documentation serves as the "Incantation" that the code must fulfill. Eventually, the Agent itself (Autopoiesis) will be tasked with reading, writing, and maintaining its own documentation.

    We need a documentation engine that:

    1. Is easy for both Humans and AI Agents to write.
    2. Supports a rich, themable visual style to convey the "Dark Fantasy" aesthetic.
    3. Integrates well with modern Git workflows.

## Decision Drivers

- **AI Compatibility:** The syntax must be intuitive for LLMs to generate without frequent syntax errors (hallucinations).
- **Aesthetic Flexibility:** The tool must allow deep customization (CSS overrides) to create the "Grimoire" look and feel.
- **Developer Experience:** The tool should offer instant local previews and easy deployment to GitHub Pages.
- **Accessibility:** The output must be mobile-friendly and accessible.

## Considered Options

!!! failure "Option 1: Sphinx (reStructuredText)"
    The traditional standard for Python projects.

    - **Pros:** Powerful directives, deep Python API documentation support.
    - **Cons:** rST syntax is notoriously brittle and confusing for both humans and LLMs. The default themes are dated. Customizing the visual style requires significant effort.

!!! failure "Option 2: Wiki (GitHub/Confluence)"
    Standard hosting provided wikis.

    - **Pros:** Zero setup.
    - **Cons:** No version control alongside code. Hard to theme.

!!! success "Option 3: MkDocs with Material Theme"
    A static site generator using Markdown.

    - **Pros:**
        - **Markdown Native:** LLMs speak Markdown fluently. This is critical for future Autopoiesis.
        - **Material Theme:** Providing a polished, modern, and responsive UI out of the box.
        - **Extensibility:** `pymdownx` extensions allow for rich content (admonitions, code blocks) without breaking standard Markdown compatibility.
    - **Cons:** Less "automatic" API documentation generation compared to Sphinx (though `mkdocstrings` mitigates this). We accept this trade-off for superior narrative capabilities.

## Decision Outcome

We will use **MkDocs with Material Theme** as the engine for "The Hexanomicon."

### Implementation Details

- **Theme:** `material` (Scheme: Slate/Dark Mode) to match the "Lich" aesthetic.
- **Structure:** Documentation lives in `docs/` and is deployed to GitHub Pages.
- **Extensions:** We enable `admonition`, `pymdownx.details`, and `pymdownx.superfences` to allow for "Grimoire-style" warnings and collapsed sections (e.g., "Forbidden Knowledge").
- **CSS:** A custom stylesheet (`stylesheets/frostmourne.css`) overrides the default Material colors to implement the specific purple/cyan/black palette of the Hexanomicon.

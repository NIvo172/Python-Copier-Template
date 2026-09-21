# Python Project Copier Template

This site is the complete reference for developing the Copier template and operating every generated-project feature. Generated projects publish a separate command reference containing only their selected options, while the full data-science showcase owns concrete examples and expected outputs.

```{mermaid}
flowchart TD
    T["copier.yml · template/"]
    G["Generated project<br/>uv · git tags"]
    B["init_project.py<br/>bootstrap once"]
    V["tox environments"]
    C["Provider CI"]
    U["copier update<br/>per release tag"]
    T -->|copier render| G
    G --> B --> V
    V --> C
    V -. Renovate .- V
    C -. copier update .- U
    U --> T
```

```{toctree}
:maxdepth: 2
:caption: Template documentation

README
getting-started
template-options
architecture
command-reference
ci-and-collaboration
data-science
maintenance
updates-and-releases
publishing
troubleshooting
```

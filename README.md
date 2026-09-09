# AllPie — Blender Addon

**AllPie is a context-driven pie menu system for Blender.**

It provides fast access to frequently used tools and operations through customisable pie menus.

## Documentation
> **Note:** I am currently recording video documentation and tutorials. Links will be added here when they’re available.

## Philosophy

AllPie is built around three ideas:

**Frequency** — Frequently used tools should be easy to reach.  
**Context** — Related operations should be grouped together.  
**Spatial Memory** — Consistent positions allow the interface to become muscle memory.

Instead of remembering where a command is buried in Blender's menus or remembering awkward keybinds, you can remember where it is located in the pie. The more you use the same layout, the faster it becomes.

AllPie is also designed with **pen and display tablet workflows** in mind. Most keybinds are arranged so your left hand can stay on the left side of the keyboard while using as few keys as possible, leaving your other hand focused on the tablet.


## Edit Mode

This is where the idea is used most heavily.

Blender already gives you three natural modelling contexts:

**Vertex → Edge → Face**

AllPie gives each one its own pie, containing operations that are most useful for that type of geometry.

For example:

* **Vertex Pie** — Bevel, Extrude, Join, Merge, Knife, Rip
* **Edge Pie** — Bevel, Extrude, Fill, Grid Fill, Bridge, Loop Cut
* **Face Pie** — Inset, Extrude, Extrude Along Normals, Individual Extrude, Flip Normals, Poke

This creates a consistent workflow where the menu itself becomes part of your modelling muscle memory.

## Redo Menu

Almost all AllPie menus include a **Redo menu at the bottom**, matching Blender's `F9` operator panel.

This lets you adjust the last operation directly from the pie, even after moving the camera or continuing your workflow.

## Current Workflows

AllPie currently includes pie menus for:

* Object Mode
* Edit Mode
* Sculpt Mode

More pie menus and workflows will be added as the project develops.

## Keybinds & Customisation

All keybinds can be changed from the addon preferences, and individual pies can be enabled or disabled.

### Object Mode

| Pie | Key |
| --- | --- |
| Selection | `A` |
| Add | `Shift + A` |
| Apply Transforms | `Ctrl + A` |
| Modifiers | `Shift + Q` |
| Tool Select | `Alt + W` |
| Shading | `Z` |

### Edit Mode

| Pie | Key |
| --- | --- |
| Selection | `A` |
| Origin | `Alt + A` |
| Shading | `Z` |
| Deletion | `X` |
| Merge | `W` |
| Vertex | `1` |
| Edge | `2` |
| Face | `3` |
| Tool Select | `Alt + W` |
| UV | `Shift + W` |
| Edge Nested | `Shift + E` |

### Sculpt Mode

| Pie | Key |
| --- | --- |
| Brush Settings | `Shift + Q` |
| Essential Brushes | `W` |
| Custom Brushes | `Shift + W` |
| Transform | `Alt + W` |
| Utility Brushes | `E` |
| Visibility | `Shift + E` |
| Remesh | `R` |
| Symmetry | `S` |
| Multires | `D` |
| Shading | `Z` |
| Sculpt Paint | `Shift + C` |

> **Note:** These are the default AllPie keybinds. All keybinds can be changed from the addon preferences.

## Recommended Edit Mode Setup

My personal layout is:

* **Vertex** → `W`
* **Edge** → `E`
* **Face** → `F`
* **Merge** → `Shift + Q`

This replaces commonly used shortcuts such as Extrude (`E`) and Fill (`F`).

Those operations are still available directly inside their respective pies, while `W`, `E`, and `F` become quick access keys for the Vertex, Edge, and Face workflows.

## Development

AllPie is an ongoing project.

The goal is to continue improving the organisation, responsiveness and usefulness of the pies while keeping them focused on **high-frequency workflows rather than simply exposing every Blender operator**.

More pie menus and workflows will be added over time.

Suggestions, feedback and contributions are welcome.

## Requirements

**Blender 5.2+**

## License

See the repository for the current license and project information.

## Author

Created by **yazz1482**.

# AllPie — Blender Addon
**AllPie is a context-driven radial and marking menu system for Blender.**

It is designed around fast access to frequently used operations, consistent spatial layouts, and workflows that work well with a pen or display tablet.
## Philosophy
AllPie is built around three ideas:

**Frequency** — Frequently used operations should be easy to reach.

**Context** — Related operations should be grouped into focused menus instead of one large command list.

**Spatial Memory** — Menu positions stay consistent so frequently used operations can become muscle memory.

AllPie is especially aimed at workflows where one hand stays near the keyboard while the other hand remains on a pen tablet or display tablet.
## Design for Tablet Workflows
AllPie is designed to reduce the need to move between the mouse or pen and a large collection of keyboard shortcuts.

The goal is not to replace every Blender shortcut. Instead, AllPie concentrates frequently used tools into consistent spatial menus so that the same hand movement can become a repeatable action.

This is particularly useful for pen-display workflows where one hand remains on the tablet and the other hand controls a small set of modifier keys and menu hotkeys.
## How the Radial Menu Works
AllPie uses an **8-slot radial layout**.

Press an AllPie hotkey and move the mouse in the direction of the desired slot. Holding the key opens the visible pie menu. Releasing the key executes the active slot.

AllPie also supports quick **marking-style gestures**. Before the full pie is opened, the mouse movement is shown as a short gesture line with markers at the center and endpoint. This allows frequently used operations to be selected through spatial movement rather than visually searching the menu every time.
### Spaced Menus
Some pies have a secondary **spaced menu**. While a pie is active, pressing `Space` switches between the normal menu and its secondary menu.

The current secondary menus are used for:

- Edit Mode Edge
- Edit Mode Vertex
- Edit Mode Face
- Edit Mode Selection
- Sculpt Mode Essential Brushes
- Sculpt Mode Mask
## Radial Menu Settings
The addon preferences provide controls for the radial menu itself, including:

- Key hold time - how long you have to hold the key before menu appears.
- Pie menu deadzone - how far you have to move the mouse before the slot is selected.
- Mark color
- Slot color
- Active slot color
- Font color
- Active font color
- Outline color
- Separate colors for spaced menus

This allows the visual behaviour of the pies to be adjusted without changing the menu implementation.

## Workflows
AllPie currently provides mode-specific workflows for:

- Object Mode
- Edit Mode
- Sculpt Mode
- Texture Paint
- Vertex Paint
- Weight Paint

Texture Paint, Vertex Paint and Weight Paint currently use the shared **Mode**, **View** and **Shading** menus. Object, Edit and Sculpt Mode contain the larger workflow-specific menu systems.

## Object Mode
Object Mode currently includes pies for:

- Add Object 
- Add Modifier 
- Subdivision
- Apply Transforms
- Selection & Hide
- Tool Select
- View
- Shading
- Mode

The Add Object provides quick access to common primitives as well as Blender's Add menu and Add-menu search.
The Add Modifier provides direct access to frequently used modifiers such as Array, Subdivision, Mirror, Multires, Solidify, Displace and Shrinkwrap, together with modifier search.
The Subdivision pie provides quick controls for subdivision levels, render levels, viewport/edit/render visibility and cage display.
## Edit Mode
Edit Mode is the main focus of AllPie.

Blender naturally separates mesh editing into three selection contexts:
**Vertex → Edge → Face**

AllPie gives each context its own dedicated pie so the available operations stay relevant to the selected geometry.
### Edit Mode pies

- Vertex
- Edge
- Face
- Selection & Hide
- Deletion
- Merge & Separate
- Tool Select
- UV
- Origin
- Subdivision
- View
- Shading
- Mode

The Vertex, Edge and Face pies contain geometry-specific modelling operations such as extrude, bevel, merge, fill, loop operations, inset, face shading and other commonly used mesh tools.
The Edit Mode space menus provide additional focused workflows without requiring another permanent keyboard shortcut.

## Sculpt Mode
Sculpt Mode has the largest collection of workflow-specific menus.
### Sculpt Mode pies

- Essential Brushes
- Paint Brushes
- Brush Settings
- Remesh
- Symmetry
- Multires
- Tool Select
- Visibility
- Mask
- View
- Shading
- Mode

### Essential Sculpt Brushes
The Essential Brushes pie is configurable from the addon preferences.
The normal Essential Brush menu contains **8 configurable brush slots**.
The spaced Essential Brush menu contains:

- Slot 0 — Blender's Asset Shelf
- Slots 1–7 — Configurable Essential brushes

Brushes can be searched and assigned directly from the preferences instead of manually entering asset identifiers.
### Brush Settings
The Sculpt Brush Settings pie provides access to Blender's brush panels and several frequently used controls, including automasking and stabilised stroke settings.
### Mask workflow
Sculpt Mode also includes a dedicated Mask pie for common mask operations such as inversion, clearing, sharpening, smoothing, contrast changes, growing and shrinking.

Its spaced menu provides additional mask workflows such as cavity masks, facesets from masks, masking from Edit Mode, mask extraction, mask slicing and mask-from-faceset operations.

## Shared Menus
Several workflows reuse common pies so the same spatial interaction remains consistent across Blender modes.
### Mode
The shared Mode menu provides quick access to:

- Object Mode
- Edit Mode — Vertex Select
- Edit Mode — Edge Select
- Edit Mode — Face Select
- Sculpt Mode
- Texture Paint
- Vertex Paint
- Weight Paint

### View
The shared View menu provides quick access to:

- Top
- Front
- Right
- Bottom
- Left
- Back
- Camera
- View Selected

### Shading
The shared Shading menu provides access to Blender's shading panel plus quick switching between:

- Wireframe
- Solid
- Material Preview
- Rendered
- Studio
- Matcap
- Flat

## Keybinds & Customisation
AllPie keybinds are configurable from the addon preferences.

Each keybind can be enabled or disabled independently, and the key, Shift, Ctrl and Alt modifiers can be changed.

### Default Object Mode Keybinds

| Key          | Menu             |
| ------------ | ---------------- |
| `Ctrl + Tab` | Mode             |
| `Shift + Q`  | Modifiers        |
| `Ctrl + Q`   | View             |
| `W`          | Tool Select      |
| `A`          | Selection & Hide |
| `Shift + A`  | Add Object       |
| `Ctrl + A`   | Apply Transforms |
| `D`          | Subdivision      |
| `Z`          | Shading          |

### Default Edit Mode Keybinds

| Key          | Menu             |
| ------------ | ---------------- |
| `Ctrl + Tab` | Mode             |
| `1`          | Vertex           |
| `2`          | Edge             |
| `3`          | Face             |
| `Ctrl + Q`   | View             |
| `W`          | Tool Select      |
| `A`          | Selection & Hide |
| `Shift + S`  | Origin           |
| `D`          | Subdivision      |
| `X`          | Deletion         |
| `M`          | Merge & Separate |
| `U`          | UV               |
| `Z`          | Shading          |

### Default Sculpt Mode Keybinds

| Key          | Menu              |
| ------------ | ----------------- |
| `Ctrl + Tab` | Mode              |
| `1`          | Essential Brushes |
| `2`          | Paint Brushes     |
| `Ctrl + Q`   | View              |
| `W`          | Tool Select       |
| `E`          | Visibility        |
| `R`          | Remesh            |
| `A`          | Mask              |
| `S`          | Symmetry          |
| `D`          | Multires          |
| `Z`          | Shading           |
| `X`          | Brush Settings    |

### Default Texture Paint Keybinds

| Key          | Menu    |
| ------------ | ------- |
| `Ctrl + Tab` | Mode    |
| `Ctrl + Q`   | View    |
| `Z`          | Shading |

### Default Vertex Paint Keybinds

| Key          | Menu    |
| ------------ | ------- |
| `Ctrl + Tab` | Mode    |
| `Ctrl + Q`   | View    |
| `Z`          | Shading |

### Default Weight Paint Keybinds

| Key          | Menu    |
| ------------ | ------- |
| `Ctrl + Tab` | Mode    |
| `Ctrl + Q`   | View    |
| `Z`          | Shading |
## Custom Operators
Some AllPie workflows use custom operators where Blender's built-in operator alone is not enough for the intended interaction.

The current addon includes custom functionality for areas such as:

- Sculpt symmetry controls
- Remesh controls
- Shading switching
- Multires controls
- Color selector popup
- QuadriFlow access
- Sculpt brush search and assignment
- Sculpt automasking toggles
- Mask creation from facesets
- Origin operations
- Edit Mode selection switching
- Subdivision controls
- Crease operations

These operators are used to keep the menu data itself simple while allowing AllPie-specific behaviour where necessary.

## Development
AllPie is an ongoing project focused on improving the speed and consistency of common Blender workflows.

The current project is intentionally focused on **high-frequency operations and workflow organisation** rather than trying to expose every Blender command through pies.

## Requirements
**Blender 5.2.0 or newer**

## License
AllPie is licensed under **GPL-3.0-or-later**.
See the repository for the complete license text.
## Author
Created by **YAZZ**.

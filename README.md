# AllPie — Blender Addon

## 1.6.1

- Full Configuration Export now includes the currently selected Menus editor draft, including brush-slot assignments and shortcut changes, even before Apply is pressed.
- Keep the live configuration unchanged when exporting a pending draft to a separate JSON file; exporting over the active configuration path commits the draft there.
- Clarify the difference between full-configuration JSON import/export and per-menu package import/export.

## 1.6.0

- Reuse semantically equivalent operator presets when importing menu JSON, including brush assets with equivalent normalized asset references.
- Remap imported menu slots to the reused canonical preset IDs and preserve imported context tags.
- Allow Brush Menus to select Asset Shelf popover presets as well as brush asset activation presets.
- Mark the built-in Paint Brushes menu as a Brush Menu for new and existing configurations.
- Consolidate duplicate built-in Asset Shelf popover presets during schema v8-to-v9 migration.

## 1.5.7 — Brush Asset Reference Migration

- Treat `asset_library_identifier` as identity data only for `CUSTOM` brush libraries, matching Blender's Asset Shelf API.
- Normalize Essentials, Online Essentials and Local asset references even when Blender exposes a non-empty library identifier.
- Add a schema v5-to-v6 migration so configurations already migrated by 1.5.6 are repaired on upgrade.
- Merge confirmed duplicate brush presets by normalized asset reference, invocation mode and visible search label, redirecting menu-slot references.

## 1.5.6 — Brush Preset Deduplication

- Normalize brush asset references so empty optional non-CUSTOM library identifiers are equivalent to omitted identifiers.
- Reuse matching Essentials and custom brush presets instead of creating duplicates.
- Migrate confirmed duplicate presets created by 1.5.5, redirecting their menu-slot references and preserving distinct custom-library references.

## 1.5.5 — Custom Brush Assignment

- In Brush Menus, the brush icon (+) assigns the currently active Blender brush asset to that slot.
- Uses Blender's active brush asset reference, including custom asset libraries.
- Regular menus retain the existing Blender operator search button.

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

All six built-in contexts share one **Mode**, **View** and **Shading** menu each. These are stored once as Common Menus and registered in Object Mode, Mesh Edit Mode, Sculpt Mode, Image Paint, Vertex Paint and Weight Paint. Object, Edit and Sculpt Mode retain their additional workflow-specific menus.

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
The Essential Brushes pie is configured from the **Menus** preferences page, using the same slot editor as other menus. Search for an Essentials brush action and assign it to a normal or spaced slot. The normal menu has eight slots; the spaced menu reserves its first slot for Blender's Asset Shelf and uses the remaining seven for brush actions.

### Brush Menu Compatibility Fix

Brush Menus support brush asset activation presets and Asset Shelf popover actions. Existing non-brush actions remain visible only when they are one of the supported Asset Shelf popup actions.

### Brush Menus
Menus created for Sculpt, Texture Paint, Vertex Paint or Weight Paint can be marked as **Brush Menu**. When enabled, the slot action picker includes brush asset activation presets and Asset Shelf popover presets. The adjacent **+** button assigns the currently active Blender brush asset to a slot. The built-in **Essentials Brushes** and **Paint Brushes** menus are marked as Brush Menus through configuration migrations without changing their shortcuts or brush assignments.
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

Each menu shortcut is assigned through Blender’s native keymap event field. Click the shortcut button, then choose a keyboard or mouse event with its modifier combination. Shift, Ctrl, Alt, OSKey and Hyper are supported. Use the X button beside the shortcut to leave a menu unassigned. Changes remain in the editor draft until Apply is pressed.

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

## Editing Menus

AllPie menu shortcuts are managed in the **Menus** page of Add-on Preferences. This is the single AllPie-specific place to edit a menu's shortcut, keymap context, and enabled state. Use the shortcut button to open Blender's event-capture field, or the X button to remove the assignment. Apply the menu draft to rebuild its Blender keymap entry. The General page does not provide a second keybinding editor.

To assign an action, click any slot in the Menus editor. AllPie opens Blender's searchable action picker. Results use a human-readable search name instead of exposing internal preset IDs in the list. Hover a result to read its description. Select **(Empty)** in the picker to clear a slot. These picker labels and descriptions do not change the labels used by the radial menus. The menu's **Mode(s)** field supports Object Mode, Mesh, Sculpt, Texture Paint, Vertex Paint, Weight Paint, a custom keymap, or **Common (All Modes)**. Common keeps one menu definition and registers the same shortcut in all six built-in AllPie mode contexts. It does not duplicate the menu or its slots. Operators can still be mode-specific, so an action may not be available in every mode.

### Menu editor categories

The Preferences → Menus editor groups menu definitions by their Blender keymap
context: Object, Mesh, Sculpt, Texture Paint, Vertex Paint and Weight Paint.
**Common Menus** is a separate category for menus registered in all six built-in
contexts at once. Each Common menu appears only once in the list and keeps one
menu ID, shortcut and set of slots. Third-party addon menus and menus with other
keymap contexts retain their own categories. Choose **All** to browse every menu
at once.

### Context-scoped menu action search

The Menus editor filters the action search popup to presets already referenced
by menus in the selected menu's Blender keymap context. For example, a menu
registered in `Sculpt` searches actions used by Sculpt menus, while an `Object
Mode` menu searches actions used by Object Mode menus. A Common menu searches
the union of presets used or catalogued in all six supported contexts. Presets
used in more than one keymap context remain available in each relevant context.
Both normal and spaced slot assignments contribute to action availability.
### Action names and descriptions

Each operator preset can define two optional editor-only fields:

- `search_name`: a human-readable label used by the configuration editor.
- `description`: an explanation shown when hovering an action in the searchable picker.

The existing `name` field remains the radial-menu label, so improving editor terminology does not change the appearance or behavior of existing pies. Older configurations without these fields remain valid; AllPie falls back to the preset name and, when available, the Blender operator's RNA description.


## Configuration Storage

AllPie loads its configuration from the per-user Blender configuration directory:

```text
Blender/
    config/
        AllPie/
            allpie_config.json
            allpie_config.json.bak
```

The add-on ships with a bundled default configuration. On first launch, AllPie
uses those defaults and migrates existing Blender AddonPreferences values and
legacy keybindings into the per-user JSON file. Later launches load the user
file, which is the single persistent source of truth for menus, operator presets,
keybindings, radial settings, colors and Essential Sculpt brush assignments.

Menu edits are validated, atomically saved and then published to the in-memory
menu registry. General preference controls are saved through a short debounce
so dragging color and slider controls does not write the file continuously.

The deprecated Blender keybind collection is retained only for one-time
migration from older AllPie versions; runtime keymaps are built directly from
the JSON menu definitions.


## Operator Search and Setup

The **Operators** page provides a searchable catalog of Blender and enabled
addon operators. Search results use Blender RNA names and descriptions. The
catalog is cached after scanning and can be refreshed after enabling another
addon.

Use the **+** button beside a menu slot to search for an operator and configure
its properties through Blender RNA. AllPie generates controls for supported
boolean, integer, float, string, enum and vector properties. Panel and menu IDs
can also be entered manually when they are not discoverable through Blender's
registered type catalog.

Configured operators are stored as reusable action presets. Multiple menu
slots can reference one preset. The **Your Added Actions** list lets users edit
or delete custom presets; deleting a preset clears its references from normal
and spaced slots. Bundled defaults and third-party-owned presets are protected
from direct deletion.

## Importing and Exporting Menus

The **Menus** page has separate **Import Menu** and **Export Menu** controls
for portable menu-package JSON files. Export writes the active menu plus only
the operator presets referenced by its Main and Spaced slots, including the
menu shortcut and modifier keys. Import adds the menu and its presets to the
current configuration; it does not replace global preferences, other menus or
the full configuration. Identical operator presets are reused.
When an imported menu or preset ID already exists with different data, AllPie
creates a unique ID and rewrites the imported slot references. Shortcut
conflicts are reported as configuration warnings rather than overwriting an
existing shortcut. A menu imported from a third-party namespace becomes a
regular user menu, with its referenced operator presets copied into the local
AllPie Operators collection.

## Importing and Exporting Configurations

The **Configuration** page provides full-configuration JSON import and export controls.

- **Export Config** writes the current menus, reusable action presets,
  third-party sections, shortcuts and preferences to a portable JSON file.
  It also includes the currently selected Menus editor draft, even when **Apply**
  has not been pressed. Exporting to a separate file does not apply that draft
  to the live configuration.
- **Import Config** parses and validates a selected file, applies any registered
  schema migrations, and displays a preview before replacing the active
  configuration. If a user configuration already exists, it is backed up as
  `allpie_config.json.bak` before the imported file is committed. On first import,
  the user configuration file is created without a backup.
- **Restore Bundled Defaults** replaces the user configuration with the default
  JSON shipped with AllPie, while preserving a backup of the previous user file.

**Restore Bundled Defaults** and **Import Config** replace the active
configuration, so any unapplied menu draft is discarded. AllPie displays a
warning about this when a draft is pending.

Import is transactional: an invalid file or failed save does not replace the
active runtime registry. A successful import updates Blender preference values
and rebuilds AllPie's keymaps. The radial menu continues to read only from the
compiled in-memory registry; it never parses JSON while opening a menu.


## 1.5.8

- Normalize brush asset relative identifiers to forward slashes so Windows Asset Shelf references reuse existing Essentials presets.
- Migrate schema v6 brush presets to merge duplicate references with equivalent asset paths.


## 1.5.9

- Compare Essentials, Online Essentials and Local brush asset identifiers case-insensitively when reusing presets.
- Keep the original asset path casing when storing and activating brushes.
- Migrate schema v7 configurations to merge capitalization-only duplicate brush presets and redirect menu slots to the existing presets.
- Keep Custom asset-library identifiers and paths distinct and case-sensitive.


## 1.6.2

- Display complete menu shortcuts, including modifier keys, in the Menus browser list.
- Include shortcut modifiers in menu-list search and preserve the display across in-place addon updates.

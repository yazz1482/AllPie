# AllPie 1.6.27 — Simplified Right-Click Capture

- Remove the standalone **Add to AllPie Operator** command from Blender's shared UI button context menu.
- Keep **Add to AllPie Menu** as the single right-click operator/brush capture workflow; captured actions proceed directly to radial slot assignment.
- Preserve slot-level **Configure AllPie Action**, preset editing from search results, and the reusable operator-preset system.
- Keep the radial assignment flow, preset cleanup safeguards, schema v15, and existing menu assignments unchanged.

# AllPie 1.6.26 — Radial Assignment State Isolation Fix

- Use a dedicated `view3d.modal_radial_assignment` operator for captured-operator assignment while preserving `view3d.modal_radial_menu` exclusively for normal shortcuts.
- Share the radial rendering and modal implementation between both operator types without sharing assignment-only RNA properties.
- Prevent Blender's remembered assignment properties from leaking into normal menu activation and opening operator setup instead of executing the assigned action.
- Keep assignment cancellation, Main/Spaced destination mapping, empty-slot rendering, schema v15, preset identities and saved assignments unchanged.

# AllPie 1.6.26 — Radial Assignment Mode and Empty Slot Rendering

- Replace the right-click **Add to AllPie Menu** slot-list popup with the selected menu's real radial layout in a dedicated assignment mode.
- Hover a direction and click to choose its destination; existing actions are displayed but never executed during assignment.
- Use **Space** to switch between Main and enabled Spaced Slots. **Esc** or right-click cancels without changing any assignment.
- Reuse the existing captured-operator replacement confirmation and RNA-driven configuration flow after a destination is selected.
- Render all eight radial positions, including explicit **Empty** slots, even when a menu has no assignments.
- Keep enabled-but-empty Spaced Slots available for assignment and normal radial display; disabled Spaced Slots remain unavailable.
- Preserve schema v15, preset IDs, existing assignments, radial geometry, and keymap dispatch.

# AllPie 1.6.26 — Spaced Slots State Fix and Operators Tab Removal

- Persist Spaced Slots enabled state independently from slot occupancy (`spaced_slots_enabled`).
- Migrate schema v14 configurations to v15, preserving populated Spaced Slot assignments and inferring empty grids as disabled because the previous schema did not retain that distinction.
- Use the explicit state consistently in the menu editor, operator picker, captured-operator setup and compiled runtime registry.

- Remove the standalone Operators page from the visible Preferences navigation. A saved legacy page selection redirects to Menus.
- Keep one operator workflow: slot search shows saved presets and registered Blender operators; right-click capture still adds operators to the library; the slot gear edits a shared preset.
- Add in-place edit and delete controls to saved preset results in the unified search. Deletion is limited to user-created local presets, confirms before clearing any assigned Main/Spaced slots, and is disabled while a menu draft is unapplied.
- Move operator RNA preset validation into the Configuration page.
- Move Refresh Operator Catalog into the unified operator search header.
- Remove the duplicate Custom Presets manager and its transient preferences state. Preset creation, editing, deletion, and discovery now live in the existing picker and slot workflows.
- Keep schema v15, permanent preset IDs and enum values, all existing menu assignments, the radial engine, and keymap dispatch unchanged.

## AllPie 1.6.25 — Operator Search Performance and Preset Reuse

- Keep the complete registered Blender/add-on operator catalog in a plain Python metadata cache. Opening a slot picker now materializes only saved AllPie presets; live Blender operators are searched from the cache and only matching rows are copied into the UI collection.
- Limit live Blender search results to the best 200 matches, prioritizing exact and leading name/operator-ID matches. The UI explains when results are capped and prompts the user to refine the query.
- Continue catalog discovery in short timer batches. Matching operators discovered while a picker is open are appended incrementally; completed scans refresh only the current query results.
- Avoid rebuilding thousands of Blender UI rows after preset edits. Search collection updates preserve the preset list and refresh only query-matched live operator rows.
- Build preset usage/context indexes once per search population, keeping saved-preset listing and usage calculation linear in presets plus occupied menu slots.
- Canonicalize captured and configured operator properties against Blender RNA defaults. Explicit default values are omitted so an action such as `mesh.primitive_cube_add` reuses an equivalent sparse `ADD_CUBE` preset instead of creating a duplicate.
- When an exact same-name, same-operator, same-invoke, same-effective-properties duplicate is found, merge its contexts and menu references into the canonical preset, then remove the redundant record. Distinct non-default property variants remain separate.
- Preserve the permanent `preset_id` and persistent enum identity model (schema v14 at the time of 1.6.25).
- When an existing configuration contains an exact default-valued duplicate preset from an earlier build, re-adding the same Blender operator with its current RNA schema merges it into the canonical preset, remaps all references and removes the duplicate warning. Non-default variants are retained.
- Keep the radial engine, runtime registry, slot identity representation and keymap dispatch unchanged.

# AllPie 1.6.24 — Menu Editor Layout Refinement

- Remove manual Menu ID entry from the Add Menu dialog.
- Generate a valid stable menu ID from the user-entered menu name (uppercase, normalized, underscore-separated, and prefixed with `CUSTOM.`).
- Show a read-only generated-ID preview that updates as the menu name changes.
- Resolve duplicate generated IDs with deterministic numeric suffixes (`_2`, `_3`, etc.).
- Existing menu IDs are never changed when an existing menu is renamed.
- Preserve an optional explicit `menu_id` argument in the Blender-independent `menu_data.add_menu()` helper for compatibility callers.

# AllPie 1.6.22 — Permanent Operator Identity and Data-Integrity Fixes

- Assign every global and third-party operator preset a permanent unique `preset_id`. Existing schema-v12 presets receive deterministic IDs based on their legacy storage key and owner namespace; newly created presets receive random unique IDs.
- Add a persistent unique `enum_value` to every preset. Main and Spaced slot EnumProperty items use the permanent preset ID as their string identifier and the stored numeric value as Blender's enum number, so library sorting or insertion cannot change existing slot identity.
- Migrate schema v12 → v13 for permanent IDs and canonical slot references, then v13 → v14 for persistent enum values. Existing operator storage keys remain as compatibility aliases.
- Use the shared preset `name` as the canonical visible name. `search_name` is retained only as a search alias. Slot-specific display-name overrides remain removed.
- Keep Active Brush assignment compatible with the detached menu draft by using the same three-field slot-assignment contract as operator assignment.
- Fix menu-package merge handling and update package format to v4. Continue importing package formats v1–v3, migrating legacy references and assigning stable preset IDs and enum values. Resolve ID/enum collisions when importing into a configuration that already contains those identities.
- Defer each AllPie right-click menu/slot-selection continuation until its parent popup handler has returned, so the AllPie popup chain can close before the next selector or Configure Operator Preset dialog is opened. Blender's native Add menu and the separate Add Operator capture path are unchanged.
- Preserve the radial engine, runtime radial adapter and keymap dispatch implementation.

# AllPie 1.6.20 — Shared Operator Preset Names

- Remove per-slot display-name overrides. Every slot now displays the name of its shared operator preset.
- The gear button edits the shared preset name and properties; renaming a preset updates every slot that references it.
- Add schema-v11 to v12 migration to remove legacy `slot_labels` and `spaced_slot_labels` from global and third-party menus.
- New menu packages use format version 1 without slot labels. Imports continue to accept older version-2 packages and discard their deprecated slot-label data.
- Preserve presets, menu assignments, Spaced Slots, radial behavior, and keymap registration/dispatch.

# AllPie 1.6.19 — Spaced Slots Draft Editing

- Keep Main Slot and Spaced Slot search/configure controls available while the menu editor has unapplied changes.
- Store a detached full-configuration draft for the menu editing session so slot assignment and operator preset configuration remain part of the same Apply/Discard transaction.
- Allow the unified operator picker to search presets added or edited in the pending draft.
- Make Configure Operator read and update the pending draft for the currently edited menu, including presets created earlier in that same draft.
- Keep active brush assignment and slot assignments draft-aware.
- Apply commits the complete draft; Discard drops menu changes and newly created/edited presets without modifying the active configuration.
- Preserve schema v11, existing menu configuration, radial engine, keymap dispatch, and the separate right-click popup workflow.

# AllPie 1.6.18 — Direct Operator Assignment

- Simplify menu slots: remove separate Add (+) and Clear (−) buttons; clicking the slot opens the unified operator/preset search, and the gear remains for quick configuration.
- Clear a slot from the slot button's right-click context menu. Brush assets can be captured directly from Blender's Asset Shelf using the same **Add to AllPie Menu** workflow as other operators.
- Remove the redundant editable Mode(s) control from the selected menu details. The selected menu category/context remains the source of truth; the editor shows the context as read-only information.
- Add **Add to AllPie Operator** and **Add to AllPie Menu** to Blender's operator-button right-click menu.
- **Add to AllPie Operator** opens Configure Operator Preset and saves a reusable preset without assigning it.
- **Add to AllPie Menu** shows enabled menus registered in the current Blender context, then their Main Slots and optional Spaced Slots. Disabled Spaced Slots are visibly unavailable.
- If a target slot is occupied, ask before replacing it. After approval, Configure Operator Preset opens; confirming saves/reuses the preset and assigns it in one config transaction. Cancelling leaves both the preset library and slot unchanged.
- Preset Name starts with Blender's original RNA operator label as an editable suggestion. AllPie does not replace that suggestion with automatic property-derived names.
- Remove the selected-menu dependency from the slot picker and save path so right-click assignment can target another menu in the current context without navigating Preferences first.
- Keep both saved AllPie presets and raw Blender RNA operators in the unified search, including raw operator entries whose operator IDs already have saved presets. Expand discovery using both `bpy.ops` and registered `bpy.types` operator RNA classes.
- Preserve schema v11, existing presets, menu-package compatibility, radial interaction, and keymap registration/dispatch.

# AllPie 1.6.17 — Operator Library Redesign

- Reorganized the Operators preferences page around one Operator Library manager.
- Preferences Add Operator, menu-slot +, and right-click capture all use the same preset creation and persistence path; they do not maintain separate operator catalogs.
- Replaced the separate Blender-operator search and custom-action manager sections with one Operator Library, one Add Operator search entry point, and a compact Custom Presets manager.
- Removed the global Add to Context control and its unused preference state. Library-created presets are untagged and available in every menu context.
- Right-click capture tags a preset with the editor/mode where the button was clicked; adding from a menu slot merges the target menu context into the preset.
- Context tags are optional discovery metadata. The + beside the search field opens optional context filters; those filters narrow saved presets only, while live Blender operators remain discoverable. Filters reset when the picker is reopened so they cannot carry over silently to another menu.
- Preset diagnostics are collapsed by default.
- No configuration schema change; existing presets, menu slots, and keymaps are retained.

# AllPie — Blender Addon

## 1.6.16 — Unified Slot Operator Picker

- Keep the existing slot label picker, but make the slot **+** button open a unified searchable operator picker.
- Search one list containing saved AllPie presets and currently registered Blender operators. Saved presets are shown instead of duplicate raw operator entries for the same Blender operator.
- Select a search result to open the existing RNA-driven Configure Blender Operator dialog; confirm to create/reuse the preset and assign it directly to the target Main or Spaced slot.
- Add optional multi-select context filters inside the search window. With no filter selected, the complete saved-preset and Blender-operator catalog remains searchable. With filters selected, show saved presets tagged for any selected context.
- Right-click capture remains available and stores its inferred AllPie context as discovery metadata. When a captured preset is chosen for another menu, source contexts are preserved and merged with the target menu context.
- Detect Blender 5.x UV Editor context using `SpaceImageEditor.mode == "UV"` / `show_uvedit`, not the separate `ui_mode` property.
- Remove the separate global Menus-page context filter; context filters now live alongside search in the slot picker. The normal slot selector remains unfiltered.
- Preserve the schema v11 configuration format, radial engine, keymap dispatch, and menu package compatibility.

## 1.6.15 — Optional Operator Context Filtering

- Keep the existing Blender operator search workflow unchanged.
- Right-click capture now tags a preset with the AllPie context inferred from the editor where the operator button was clicked.
- Remove the separate capture-time context selector, which duplicated the editor context and could be confused with Blender operator target properties.
- Add an optional **Filter by Context** toggle to the Menus editor. It is disabled by default, so every saved action preset remains searchable from every menu. The existing **+ Blender Operator Search** remains unfiltered.
- When enabled, the slot picker is limited to presets explicitly tagged for the selected menu context or already referenced by menus in that context.
- Preserve Blender operator properties (including `space_type`) independently from AllPie context tags.


## 1.6.14 — Explicit AllPie Context for Captured Operators

- Separate the captured operator's Blender target editor (for example, `wm.tool_set_by_id.space_type = IMAGE_EDITOR`) from the AllPie menu context used to discover the preset.
- Add an **Available In** selector to right-click operator capture, defaulted from the editor/mode where the button was clicked.
- Support explicit UV Editor, Image Editor, Node Editor, built-in mode, Common and custom keymap contexts.
- Relabel `wm.tool_set_by_id.space_type` as **Target Editor** and explain that it does not control AllPie slot availability.
- Preserve existing operator properties, preset names, menu-package compatibility, and radial/keymap execution behavior.

## 1.6.13 — Named Right-Click Operator Presets

- Ask for an editable AllPie preset name when capturing an operator from Blender's right-click button context menu.
- Suggest node-specific names for `node.add_node` captures using Blender's registered node RNA label (for example, “Add Principled BSDF” or “Add Math”).
- Require a non-empty preset name for context-captured operators so different settings are not silently stored under the same generic label.
- At the time, preset names and optional per-slot display names were separate; the per-slot naming feature was later removed in 1.6.20.
- Preserve the existing property capture, RNA configuration dialog, and radial/keymap execution paths.

## 1.6.12 — Context-Captured Operator Fallback

- Allow right-click captures to save valid Blender operators even when they are intentionally omitted from AllPie's searchable operator catalog.
- Resolve the live RNA label and description as a fallback after catalog lookup, including generic search operators used by editor menus.
- Keep the searchable catalog exclusions unchanged; context capture is an explicit user action and uses the same preset persistence path.

## 1.6.11 — Right-Click Operator Capture

- Add **Add to Operator Library** to Blender's shared UI button context menu when right-clicking an operator button or menu item.
- Capture the clicked operator's RNA identifier and supported non-default property values.
- Reuse the existing RNA-driven setup dialog so captured settings can be reviewed before saving.
- Infer the AllPie context from the active editor/mode, and report advanced properties that cannot be represented by the JSON-backed setup controls.
- Preserve Blender's and other add-ons' context-menu entries; remove AllPie's callback cleanly during unregister and refresh.

## 1.6.10 — Menu Package Compatibility

- Earlier 1.6.10 builds used package format version 2 when exporting per-slot display names; 1.6.20 removes those fields and returns new exports to version 1.
- Continue importing version 1 packages from 1.6.8 and earlier.
- Preserve compatibility with 1.6.9 version 1 packages that already contain slot display names.
- Keep menu-package validation consistent between file loading and direct package merging.

## 1.6.9 — Custom Per-Slot Display Names (retired in 1.6.20)

- Add optional custom display names to individual normal and Spaced Menu slots without changing reusable operator presets.
- Include a slot-local name field in the operator settings popup; leaving it empty keeps automatic operator naming.
- Apply custom labels consistently to built-in, brush, Asset Shelf and third-party menu actions.
- Preserve slot labels through full configuration and individual menu package import/export.
- Add schema v10-to-v11 migration; existing configurations keep automatic naming by default.

## 1.6.8 — UV Editor Mode Menu Isolation

- Prevent the Image Editor View/Paint/Mask mode menu from opening while the shared Image Editor space is displaying UV editing.
- Keep the Image Editor mode-switch operator unavailable in UV editing contexts.
- Preserve existing UV Editor menus and all 3D View Common menu behavior.

## 1.6.7 — Image Editor Mode Menu

- Separate the Image Editor's mode menu from the Common 3D View mode menu.
- Add Image Editor View, Paint and Mask actions under the Image keymap.
- Resolve the shared Image Paint keymap to an Image Editor-specific Mode menu when invoked from the Image Editor.
- Migrate existing schema-v9 configurations by adding the Image Editor Mode menu without overwriting existing menus or shortcuts.

## 1.6.6

- Add radial menu drawing support for the UV/Image Editor and Node Editor using Blender's corresponding Space draw-handler APIs.
- Add dedicated UV Editor, Image Editor and Node Editor menu contexts with editor-specific keymap space/region metadata.
- Keep the Common menu scope limited to the original six viewport mode contexts.
- Execute editor-specific actions inside the original window, area and region context captured when the radial menu was invoked.

## 1.6.5

- Process `MOUSEMOVE` and `INBETWEEN_MOUSEMOVE` through one pointer-update path.
- Ignore Space when the active menu has no populated Spaced Menu, without changing menu state or interrupting the hold timer.
- Reserve Space and Esc as internal radial controls and reject them as menu-opening shortcuts in configuration validation and the shortcut editor.
- Skip conflicting reserved shortcuts during one-time legacy keybind migration so other migrated settings remain intact.

## 1.6.4

- Avoid reporting a false execution warning when `mesh.select_mode` is cancelled because the requested selection mode is already active.
- Continue reporting genuine operator cancellations and preserve the existing radial action execution behavior.

## 1.6.3

- Restrict radial-menu drawing to the exact window, area and region that opened it.
- Centralize modal resource cleanup and make cleanup safe to call repeatedly.
- Remove radial timers and draw handlers when modal startup fails, the operator is cancelled, or the window loses focus.
- Validate the hold duration using a monotonic clock so unrelated TIMER events cannot reveal the menu early.
- Ignore repeated Space key events while switching between normal and spaced menus.
- Keep the radial menu capturing all input while active; viewport-navigation pass-through remains disabled.


## 1.6.1

- Full Configuration Export now includes the currently selected Menus editor draft, including brush-slot assignments and shortcut changes, even before Apply is pressed.
- Keep the live configuration unchanged when exporting a pending draft to a separate JSON file; exporting over the active configuration path commits the draft there.
- Clarify the difference between full-configuration JSON import/export and per-menu package import/export.

## 1.6.0

- Reuse semantically equivalent operator presets when importing menu JSON, including brush assets with equivalent normalized asset references.
- Remap imported menu slots to the reused canonical preset IDs and preserve imported context tags.
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

- Brush assets can be captured directly from Blender's Asset Shelf and assigned to any AllPie menu.
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

### Editor Contexts

Menus can be assigned to the existing 3D View mode contexts or to additional editor contexts:

- **UV Editor** — Blender's UV editing keymap context.
- **Image Editor** — Blender's Image Editor keymap context.
- **Node Editor** — shared by the Shader Editor, Geometry Nodes, Compositor and Texture Node editors.

The editor contexts use the same radial interaction and slot system as the 3D View. The `Common` scope retains its original meaning and continues to target only AllPie's six existing mode contexts.
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

### Brush Asset Actions

Brush assets are captured from Blender's Asset Shelf through the regular **Add to AllPie Menu** context-menu workflow. The captured `brush.asset_activate` action is a normal reusable AllPie operator preset and can be assigned to any menu. No special menu type is required.

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

To assign an action, click any slot in the Menus editor. AllPie opens the unified searchable picker containing saved presets and registered Blender operators. Results use a human-readable name; hover a result to read its description. Select a result to open **Configure Operator Preset**. Confirm saves or reuses the preset and assigns it to that slot. Right-click an assigned slot to configure its action or clear the assignment;. The Preferences editor presents Normal Slots and Spaced Slots as two side-by-side vertical button lists, with each slot identified by its position in the list. These picker labels and descriptions do not change the labels used by the radial menus. The selected menu's category/context is shown read-only in the details pane; Common keeps one menu definition and registers its shortcut in all six built-in AllPie mode contexts. Operators can still be mode-specific, so an action may not be available in every mode.

To add an operator directly from Blender, right-click an operator button and choose **Add to AllPie Menu**. Select an enabled menu for the current Blender context, then choose a destination in its radial layout. Main Slots and enabled Spaced Slots are available. If the target slot is occupied, AllPie asks before replacing it. The operator configuration dialog uses Blender's original operator label as an editable preset-name suggestion. Cancelling that dialog leaves the operator library and menu slot unchanged.

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


## Operator Library

The **Operators** page is the Operator Library manager. **Add Operator** opens
the same search popup used by the **+** button beside every menu slot. Search
saved AllPie presets and registered Blender operators in one place. Selecting
a result opens the RNA-driven configuration dialog; confirm to save or reuse
the preset and, when opened from a menu slot, assign it directly to that slot.

Use the **+** button beside the search field to add optional context filters.
Filters narrow saved presets by their context tags or menu usage; they do not
restrict assignment, and registered Blender operators remain visible so new
presets can still be created. Filters are cleared whenever the picker is opened
again, so they cannot silently carry over to another menu. With no filters
selected, all saved presets and registered Blender operators are searchable.

Right-click an operator button or menu item in Blender and choose **Add to
Operator Library** to capture its supported non-default properties. AllPie
automatically tags the preset with the editor/mode where it was captured when
that context can be identified. Library-created presets are untagged by
default, meaning they are available in every menu context. Context tags are
organizing metadata only, not execution restrictions.

Configured operators are stored as reusable presets. Multiple menu slots can
reference one preset. The **Custom Presets** list lets users edit or delete
custom presets; deleting a preset clears its references from normal and
spaced slots. Bundled defaults and third-party-owned presets are protected
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




### Add actions directly from Blender's UI

Right-click an operator button or menu item and choose **Add to AllPie Menu**. AllPie captures the operator identifier and supported non-default properties, then opens the existing radial assignment workflow. Choose a destination slot and review the captured values in the RNA-driven setup dialog before saving the reusable action preset. Properties that require unsupported pointer/collection handling are reported in the dialog and retain Blender defaults.


## 1.6.24 — Menu Editor Layout Refinement

- Combined menu name and shortcut controls on one row.
- Removed the redundant per-menu context label from the settings panel.
- Moved Apply and Discard controls to the bottom of the menu editor.
- No configuration schema or runtime behavior changes.

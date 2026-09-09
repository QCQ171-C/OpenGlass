# uDWM evidence guide

uDWM accessors are frequently inlined. Start with a constructor or creation path, then validate named roles through callers and mutators.

## High-value anchors

| Area | Primary evidence | Independent checks and cautions |
|---|---|---|
| `CVisual` | Constructor/Create plus `SetScale`, `SetSize`, `SetOffset`, dirty/RTL mutators | Distinguish member byte offsets from vtable slot offsets |
| `CContainerVisual` | Constructor/Create and visual collection initialization | Its presence does not imply `CVisual::Create` disappeared |
| `CWindowData` | `BlurBehindChange`, LivePreview collection, backdrop/DPI setters | Verify every flag independently; adjacency is not evidence |
| `CTopLevelWindow` | Create, allocation, constructor, and Initialize | Track base-class and `CWindowData*` association per sample |
| Non-client visuals | `CWindowBorder`, legacy background, caption/button/text update paths | Gate each feature and legacy variant independently |
| LivePreview | `_CollectWindows`, resource update helper, setup/cleanup paths, cloned frame visuals | Use the semantic API argument, such as a RECT passed to `IntersectRect`; keep Aero Peek highlight and reflection paths separate |
| Acrylic/glass | `CAcrylicSheet` or `CAnimatedGlassSheet` constructors and updates | Treat replacement as a feature gate, not a neighboring-layout mapping |

## Important distinctions

- `CVisual::SetScale` exposes two adjacent scalar values, but their byte position can move while the function and signature remain.
- `CContainerVisual::Create` and `CVisual::Create` may coexist. Gate and analyze both rather than encoding a mutually exclusive era rule.
- `CWindowData::ClientBlurAttribute` and `NonClientAttribute` may be adjacent in a particular specimen. Derive each from the bit operation that implements its own behavior.
- `CWindowData`'s reverse link to `CTopLevelWindow` must be confirmed from the constructor, blur update, or another semantic owner path.
- A constructor allocation size helps bound the object but never assigns field names by itself.

## Constructor and signature routing

- Use zeroed pointers, paired `1.0f`, double `1.0`, repeated `0x7FFFFFFF` insets, and `-1`/`-2` sentinels as constructor fingerprints only. Confirm the candidate with a semantic setter or consumer.
- A `CVisual::SetScale` path taking floats usually routes to D2D `SIZE_F` storage; a double-taking path usually routes to `MilSizeD`. Both may coexist, so confirm the actual write and constructor initialization.
- An older `CTopLevelWindow` shape may directly construct a `CVisual` base without a `CWindowData*`; a newer shape may expose a `CContainerVisual` base and a `CWindowData*` association. Use this as class-shape routing, not as a release classifier or layout proof.

Do not restore superseded assumptions that one codebase generation has one immutable layout, that adjusted `this` cannot occur in uDWM, or that neighboring flags and historical slots remain fixed.

## LivePreview highlight and reflection path

Legacy high-glass preview support is split across uDWM object/resource setup and dwmcore draw-list repair. Audit both modules before changing runtime gates.

- Treat build `20348` as the pre-Windows-11 LivePreview path because the code gates on the numeric build boundary `22000`, not the marketing family.
- For builds before `22000`, the preview redraw hook is `CLivePreview::_UpdateInstructions`. The important semantic anchor is the existing instruction rebuild followed by `CRenderDataVisual::ClearInstructions`/`AddInstruction` on the glass visual.
- For builds `22000+`, the preview redraw hook is `CLivePreview::_FadeOutToGlass`. The OpenGlass path calls `_UpdateResources()`, refreshes cloned `windowFrames`, adds inactive/active highlight instructions, restores preview reflection instructions, and then chains to the original DWM fade path.
- For builds `26100+`, `CLivePreview::_UpdateResourcesForMonitorHelper` is only a resource-collection hook. It brackets the original call with the active `CTopLevelWindow` so `CreateRectRgn` interception can build the reflection region for the right window; clear the redirect state on every exit path.
- The high-glass highlight brush uses `CTopLevelWindow::TreatAsActiveWindow`, `CTopLevelWindow::GetActualWindowRect`, and `CTopLevelWindow_GetNonClientVisual_Index`. During Aero Peek, the selected preview should render active highlight and every other preview clone should render inactive highlight.
- The retained `LivePreviewResource` fields are the window/glass bounding rect/geometry/brush pointers and `LivePreviewResource_GetReflectionGeometry`. Do not reintroduce the removed region/non-empty flag accessors unless a runtime call site needs them and the exact binary evidence is renewed.
- `CLivePreview_GetGlassVisual`, `CLivePreview_GetLivePreviewResourceArray`, and `CLivePreview_GetLivePreviewVisualArray` must be verified together because the preview hook mutates both instruction lists and cloned frame visuals.
- Startup and shutdown gates for `_UpdateInstructions`, `_FadeOutToGlass`, and `_UpdateResourcesForMonitorHelper` must remain symmetric; a hook installed on an inactive symbol range is a DWM crash risk.

## Vtable values

For a projection that represents a slot, locate the class vtable from a constructor, enumerate pointer-sized entries, and identify the target by behavior/xrefs. Do not write the data-member displacement used inside the target function as the slot value.

## Feature transitions

Use class/function presence to route the audit, then verify the requested projection. Examples include `CDWriteText`, `CWindowBorder`, legacy non-client background variants, Acrylic versus AnimatedGlass, and the TopLevelWindow base-class transition. These are capability checks, not authoritative Windows release classifiers.

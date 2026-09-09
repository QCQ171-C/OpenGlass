# dwmcore evidence guide

Start from the target schema item's `notes`; they are routing hints, not proof. Gate each class independently.

## High-value anchors

| Area | Primary evidence | Independent checks and cautions |
|---|---|---|
| `COcclusionContext` | `IsCurrent` comparing a member with the global frame ID | Constructor; optimized-rect paths when `IsCurrent` is absent |
| Legacy MIL brushes | `TryDrawCommandAsDrawList`; legacy brush update/setter functions | Channel update dispatcher; absence only gates brush-related projections |
| `CDrawingContext` | `Create` allocation and vtable assignments | Constructor and interface methods; account for adjusted `this` |
| World transform | `GetWorldTransform3x2` or the active equivalent | Add the interface-subobject displacement to decompiler-relative access |
| `CDirtyRegion` | Optimized-rect and occlusion call paths | A context passed as a parameter is not a stored member |
| `CD3DDevice`/targets | Constructors, interface vtables, target creation | Do not reuse a historical slot solely because neighboring thunks match |

## Semantic gates

- Loss of `TryDrawCommandAsDrawList` or legacy brush symbols supports removal of that brush path, not total dwmcore removal.
- A change in `CDrawingContext::Create` vtable assignments can indicate interface absorption or subobject movement. Verify affected methods individually.
- Object allocation size is supporting context only; it cannot map members by itself.
- Correlated `COcclusionContext` shifts are a useful anomaly check, not independent proof for every member.

## Fallbacks

- If `COcclusionContext::IsCurrent` is absent, inspect `GetOptimizedRect`-style functions for the comparison between a context member and the composition frame ID.
- In that comparison, derive the projection from the `COcclusionContext` side. The `g_pComposition` frame-ID slot is only an anchor and can move independently.
- For pre-template brush builds, use the monolithic `ProcessUpdate`; for template-generated builds, use individual setters plus their dispatcher.
- If a generated brush setter loses its useful name, use the small `CResource::OnPropertyChanged` callee to recover the setter family.
- When a vtable symbol is folded, read constructor assignments and slot targets, then report unresolved ICF instead of selecting a convenient symbol.

## Symbol-loss semantic anchors

- Identify `CArrayBasedCoverageSet::Add` from the `CZOrderedRect` construction, `UpdateDeviceRect`, and `DynArray::AddMultipleAndSet` sequence.
- Identify `CMILMatrix::Multiply` from its 4-by-4 floating-point matrix multiplication loop.
- Identify `CMatrixStack::Push` from the stack write followed by count growth, then use it to route back to the world-transform path.
- Route shared `CDrawingContext` layout through a discoverable `CGlobalDrawingContext::Create` when shape/subdrawing variants have no independent factory.

Treat every algorithmic anchor as candidate navigation and verify it in the exact binary.

## Legacy brush relationships

`CImageLegacyMilBrush` and `CSolidColorLegacyMilBrush` share opacity, float-resource, viewport, and viewbox layout through `CLegacyMilBrush`. Realized color belongs to the solid-color path and requires its own evidence. When `CSolidColorLegacyMilBrush::GetRealizedColor` is inlined, start at `TryDrawCommandAsDrawList`, locate the call path to `CRenderData::DrawSolidColorRectangle`, and interpret the nearby brush read as `D3DCOLORVALUE`; confirm it through another solid-color producer or consumer before accepting it.

## LivePreview reflection draw repair

The high-glass Aero Peek fix uses dwmcore only to keep the reflection atlas draw from being clipped or reinterpreted as another full-screen image. Keep this separate from the uDWM highlight brush work.

- `CRenderData::TryDrawCommandAsDrawList` is hooked as a chain node with the renderer. Its only LivePreview-reflection job is to detect the DWM geometry command that draws an image legacy brush over a rectangle geometry and set the scoped `g_fixLivePreviewRendering` flag.
- `CRenderData::DrawImageResource_FillMode` must pass a null source rect only while that scoped flag is set. Applying the null source rect outside that narrow draw-list path causes ordinary reflection/atlas rendering regressions.
- Preserve the four ABI ranges from `ProjectionSchemas/legacy/dwmcore.json`: pre-`19041`, `19041` through pre-`22000`, `22000` through pre-`26100.2454`, and `26100.2454+`. Do not merge these complete names just because the semantic method name is the same.
- The draw-list detector depends on `CRenderData_GetResources`, `CImageLegacyMilBrush::vftable`, `CImageLegacyMilBrush_GetImageSource`, `CImageLegacyMilBrush_GetFloatResource`, and rectangle-geometry command indices. Audit those as data/field evidence, not as highlight-brush evidence.
- Missing `CDrawingContext::GetCurrentVisual`, `CDrawingContext::PreSubgraph`, or `CVisual::GetTopLevelWindow` means the compositor-render traversal still lacks required dwmcore evidence. Do not treat successful uDWM LivePreview symbol resolution as proof for those dwmcore symbols.
- The user-visible regression test is Aero Peek: hover a taskbar thumbnail, switch the peek target, open a jump list, and confirm normal windows keep their reflection while preview clones keep active/inactive highlight without drawing a second full-screen reflection.

## Removal decisions

To end a Layout without an open-ended case, demonstrate that the semantic member/interface is absent from the relevant class or that the consumer path no longer exists. Failure to find one decorated name is insufficient.

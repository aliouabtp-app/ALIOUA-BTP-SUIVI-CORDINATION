"""تحويل DXF ثنائي الأبعاد إلى GLB مبدئي باستخدام هندسة محلية مفتوحة المصدر.

هذا التحويل يبني جدراناً مستطيلة من خطوط المخطط فقط؛ لا يستنتج الأبواب
والنوافذ أو الأعمدة أو المناسيب أو التفاصيل الإنشائية تلقائياً.
"""
import math
import ezdxf
import trimesh

UNIT_FACTORS = {"MM": 0.001, "CM": 0.01, "M": 1.0, "IN": 0.0254, "FT": 0.3048}
WALL_LAYER_HINTS = ("wall", "mur", "clois", "a-wall", "architect", "struct")


def _entity_segments(entity):
    kind = entity.dxftype()
    if kind == "LINE":
        p1, p2 = entity.dxf.start, entity.dxf.end
        return [((float(p1.x), float(p1.y)), (float(p2.x), float(p2.y)))]
    if kind == "LWPOLYLINE":
        pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
        closed = bool(entity.closed)
    elif kind == "POLYLINE":
        pts = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
        closed = bool(entity.is_closed)
    else:
        return []
    pairs = list(zip(pts, pts[1:]))
    if closed and len(pts) > 2:
        pairs.append((pts[-1], pts[0]))
    return pairs


def generate_glb_from_dxf(path, units="MM", wall_height=3.0, wall_thickness=0.2, layer_name=""):
    """يرجع (bytes, عدد الجدران، الطبقة المختارة)."""
    if units not in UNIT_FACTORS:
        raise ValueError("وحدة الرسم غير مدعومة.")
    if not 1.0 <= float(wall_height) <= 10.0:
        raise ValueError("ارتفاع الجدار يجب أن يكون بين 1 و10 أمتار.")
    if not 0.05 <= float(wall_thickness) <= 0.5:
        raise ValueError("سماكة الجدار يجب أن تكون بين 0.05 و0.50 متر.")

    doc = ezdxf.readfile(str(path))
    entities = [e for e in doc.modelspace() if e.dxftype() in {"LINE", "LWPOLYLINE", "POLYLINE"}]
    if layer_name:
        chosen = [e for e in entities if e.dxf.layer == layer_name]
        if not chosen:
            raise ValueError("الطبقة المحددة لا تحتوي على خطوط أو polylines.")
        selected_layer = layer_name
    else:
        candidates = {e.dxf.layer for e in entities if any(h in e.dxf.layer.lower() for h in WALL_LAYER_HINTS)}
        if candidates:
            chosen = [e for e in entities if e.dxf.layer in candidates]
            selected_layer = ", ".join(sorted(candidates))
        else:
            chosen = entities
            selected_layer = "ALL"

    scale = UNIT_FACTORS[units]
    meshes = []
    wall_count = 0
    for entity in chosen:
        for start, end in _entity_segments(entity):
            dx = (end[0] - start[0]) * scale
            dy = (end[1] - start[1]) * scale
            length = math.hypot(dx, dy)
            if length < 0.03:
                continue
            if wall_count >= 5000:
                raise ValueError("المخطط يحتوي على أكثر من 5000 قطعة خطية؛ قسّم الملف أو حدّد طبقة الجدران.")
            mesh = trimesh.creation.box(extents=[length, float(wall_thickness), float(wall_height)])
            transform = trimesh.transformations.rotation_matrix(math.atan2(dy, dx), [0, 0, 1])
            transform[:3, 3] = [((start[0] + end[0]) * 0.5) * scale,
                                ((start[1] + end[1]) * 0.5) * scale,
                                float(wall_height) * 0.5]
            mesh.apply_transform(transform)
            mesh.visual.face_colors = [184, 197, 207, 255]
            meshes.append(mesh)
            wall_count += 1

    if not meshes:
        raise ValueError("لم نعثر على خطوط صالحة لبناء الجدران في المخطط.")
    combined = trimesh.util.concatenate(meshes)
    # تحويل Z-up في DXF إلى Y-up القياسي في GLTF حتى يظهر النموذج واقفاً في Three.js.
    combined.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    return bytes(combined.export(file_type="glb")), wall_count, selected_layer

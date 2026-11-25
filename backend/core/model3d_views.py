import tempfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.utils.text import slugify
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from .models import Level, Model3D, AuditLog
from .serializers import Model3DSerializer
from .permissions import RolePermission
from .dxf_to_3d import generate_glb_from_dxf


class DxfModelGenerateView(APIView):
    """تحويل DXF محلياً إلى GLB أولي دون أي API سحابي."""
    permission_classes = [IsAuthenticated, RolePermission]
    parser_classes = [MultiPartParser, FormParser]
    write_roles = {"ADMIN", "MANAGER", "ENGINEER"}

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "ارفع ملف DXF أولاً."})
        if uploaded.size > 20 * 1024 * 1024:
            raise ValidationError({"file": "الحد الأقصى لملف DXF هو 20 ميغابايت."})
        if not uploaded.name.lower().endswith(".dxf"):
            raise ValidationError({"file": "الصيغة المدعومة حالياً هي DXF فقط."})

        level_id = request.data.get("level")
        try:
            level = Level.objects.get(pk=level_id)
        except (Level.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"level": "اختر طابقاً صالحاً."})

        title = str(request.data.get("title") or Path(uploaded.name).stem).strip()[:200]
        units = str(request.data.get("units") or "MM").upper()
        layer_name = str(request.data.get("layer_name") or "").strip()
        try:
            height = float(request.data.get("wall_height") or 3.0)
            thickness = float(request.data.get("wall_thickness") or 0.2)
        except (TypeError, ValueError):
            raise ValidationError({"wall_height": "أدخل ارتفاعاً وسماكة صالحين."})

        try:
            with tempfile.NamedTemporaryFile(suffix=".dxf") as temp:
                for chunk in uploaded.chunks():
                    temp.write(chunk)
                temp.flush()
                glb, wall_count, selected_layer = generate_glb_from_dxf(
                    temp.name, units=units, wall_height=height,
                    wall_thickness=thickness, layer_name=layer_name
                )
        except Exception as exc:
            raise ValidationError({"file": f"تعذر تحليل المخطط: {exc}"})

        safe_name = slugify(title) or "floor-model"
        selected_layer = selected_layer[:120]\n        model = Model3D(
            level=level, title=title, source_filename=uploaded.name,
            source_layer=selected_layer, wall_count=wall_count, units=units,
            wall_height=height, wall_thickness=thickness, generated_by=request.user
        )
        model.file.save(f"{safe_name}.glb", ContentFile(glb), save=False)
        model.save()
        AuditLog.objects.create(
            user=request.user, action="CREATE", entity="Model3D",
            entity_id=str(model.pk),
            payload={"source": uploaded.name, "wall_count": wall_count, "units": units, "layer": selected_layer}
        )
        return Response(Model3DSerializer(model, context={"request": request}).data, status=status.HTTP_201_CREATED)

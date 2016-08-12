from apps.custom_mosaic_tool.models import Area

def countries(request):
    return {'areas' : Area.objects.all().order_by('area_id')}

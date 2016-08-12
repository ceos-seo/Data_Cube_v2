from django.contrib import admin
from .models import Query, Metadata, Result, Satellite, SatelliteBand, ResultType, Area

# Register your models here.
admin.site.register(Query)
admin.site.register(Metadata)
admin.site.register(Result)
admin.site.register(SatelliteBand)
admin.site.register(ResultType)
admin.site.register(Satellite)
admin.site.register(Area)

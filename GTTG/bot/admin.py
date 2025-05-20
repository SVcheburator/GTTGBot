from django.contrib import admin
from .models import MuscleGroup, Exercise, TrainingCycle, CycleDay


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['name', 'muscle_group']
    list_filter = ['muscle_group']
    search_fields = ['name']


@admin.register(TrainingCycle)
class TrainingCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    search_fields = ['name']

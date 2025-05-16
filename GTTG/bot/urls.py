from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, MuscleGroupViewSet, ExerciseViewSet,
    TrainingCycleViewSet, CycleDayViewSet,
    WorkoutViewSet, WorkoutExerciseViewSet,
    get_or_create_user,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'muscle-groups', MuscleGroupViewSet)
router.register(r'exercises', ExerciseViewSet)
router.register(r'training-cycles', TrainingCycleViewSet)
router.register(r'cycle-days', CycleDayViewSet)
router.register(r'workouts', WorkoutViewSet)
router.register(r'workout-exercises', WorkoutExerciseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth-user/', get_or_create_user),
]

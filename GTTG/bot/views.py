from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import (
    User, MuscleGroup, Exercise, TrainingCycle, CycleDay, Workout, WorkoutExercise
)
from .serializers import (
    UserSerializer, MuscleGroupSerializer, ExerciseSerializer,
    TrainingCycleSerializer, CycleDaySerializer,
    WorkoutSerializer, WorkoutExerciseSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class MuscleGroupViewSet(viewsets.ModelViewSet):
    queryset = MuscleGroup.objects.all()
    serializer_class = MuscleGroupSerializer


class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer


class TrainingCycleViewSet(viewsets.ModelViewSet):
    queryset = TrainingCycle.objects.all()
    serializer_class = TrainingCycleSerializer

    def get_queryset(self):
        queryset = TrainingCycle.objects.all()

        telegram_id = self.request.query_params.get("telegram_id")
        if telegram_id:
            queryset = queryset.filter(user__telegram_id=telegram_id)

        return queryset


class CycleDayViewSet(viewsets.ModelViewSet):
    queryset = CycleDay.objects.all()
    serializer_class = CycleDaySerializer

    def get_queryset(self):
        queryset = CycleDay.objects.all()

        cycle_id = self.request.query_params.get("cycle_id")
        if cycle_id:
            queryset = queryset.filter(cycle__id=cycle_id)

        telegram_id = self.request.query_params.get("telegram_id")
        if telegram_id:
            queryset = queryset.filter(cycle__user__telegram_id=telegram_id)

        return queryset


class WorkoutViewSet(viewsets.ModelViewSet):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer


class WorkoutExerciseViewSet(viewsets.ModelViewSet):
    queryset = WorkoutExercise.objects.all()
    serializer_class = WorkoutExerciseSerializer



@api_view(['POST'])
def get_or_create_user(request):
    telegram_id = request.data.get('telegram_id')
    username = request.data.get('username', '')

    if not telegram_id:
        return Response({'error': 'telegram_id is required'}, status=400)

    user, created = User.objects.get_or_create(telegram_id=telegram_id, defaults={'username': username})
    serializer = UserSerializer(user)
    return Response(serializer.data)

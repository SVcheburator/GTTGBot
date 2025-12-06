from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from datetime import date
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
    lookup_field = "telegram_id"


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

    def create(self, request, *args, **kwargs):
        default_exercises = request.data.pop("default_exercises", None)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if default_exercises is not None:
            instance.default_exercises.set(default_exercises)
        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED, headers=headers)


class WorkoutViewSet(viewsets.ModelViewSet):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        queryset = Workout.objects.all().prefetch_related('muscle_groups', 'exercises__exercise__muscle_group')
        telegram_id = self.request.query_params.get("telegram_id")
        if telegram_id:
            queryset = queryset.filter(user__telegram_id=telegram_id)
        return queryset.order_by('-date', '-id')

    def create(self, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if not telegram_id:
            raise ValidationError({'telegram_id': 'This field is required.'})
        
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            raise ValidationError({'telegram_id': 'User not found.'})

        workout_data = request.data.copy()
        workout_data['user'] = user.id
        workout_data['date'] = date.today().isoformat()
        incoming_groups = workout_data.pop('muscle_groups', None)
        cycle_day_id = workout_data.pop('cycle_day', None) or workout_data.pop('cycle_day_id', None)
        workout_data.pop('telegram_id', None)

        serializer = self.get_serializer(data=workout_data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if incoming_groups is not None:
            try:
                instance.muscle_groups.set(incoming_groups)
            except Exception:
                pass
        if cycle_day_id:
            try:
                instance.cycle_day = CycleDay.objects.get(id=cycle_day_id)
                instance.save(update_fields=['cycle_day'])
            except CycleDay.DoesNotExist:
                pass
        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED, headers=headers)


class WorkoutExerciseViewSet(viewsets.ModelViewSet):
    queryset = WorkoutExercise.objects.all()
    serializer_class = WorkoutExerciseSerializer

    def create(self, request, *args, **kwargs):
        workout_id = request.data.get('workout')
        exercise_id = request.data.get('exercise')
        reps = request.data.get('reps')
        weight = request.data.get('weight')

        if not (workout_id and exercise_id and reps):
            return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            workout = Workout.objects.get(id=workout_id)
            exercise = Exercise.objects.get(id=exercise_id)
        except (Workout.DoesNotExist, Exercise.DoesNotExist):
            return Response({'error': 'Workout or Exercise not found'}, status=404)

        workout_exercise = WorkoutExercise.objects.create(
            workout=workout, exercise=exercise, reps=reps, weight=weight
        )

        serializer = self.get_serializer(workout_exercise)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def get_or_create_user(request):
    telegram_id = request.data.get('telegram_id')
    username = request.data.get('username', '')

    if not telegram_id:
        return Response({'error': 'telegram_id is required'}, status=400)

    user, created = User.objects.get_or_create(telegram_id=telegram_id, defaults={'username': username})
    serializer = UserSerializer(user)
    return Response(serializer.data)

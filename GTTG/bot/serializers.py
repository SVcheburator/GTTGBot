from rest_framework import serializers
from .models import User, MuscleGroup, Exercise, TrainingCycle, CycleDay, Workout, WorkoutExercise


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class MuscleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuscleGroup
        fields = '__all__'


class ExerciseSerializer(serializers.ModelSerializer):
    muscle_group = MuscleGroupSerializer(read_only=True)

    class Meta:
        model = Exercise
        fields = '__all__'


class CycleDaySerializer(serializers.ModelSerializer):
    muscle_groups = MuscleGroupSerializer(many=True, read_only=True)

    class Meta:
        model = CycleDay
        fields = ['id', 'day_number', 'is_training_day', 'muscle_groups']


class TrainingCycleSerializer(serializers.ModelSerializer):
    days = CycleDaySerializer(many=True, read_only=True)

    class Meta:
        model = TrainingCycle
        fields = ['id', 'name', 'length', 'days']


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = ['id', 'exercise', 'sets', 'reps']


class WorkoutSerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)
    muscle_groups = MuscleGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Workout
        fields = ['id', 'date', 'is_from_plan', 'muscle_groups', 'exercises']

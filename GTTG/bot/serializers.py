from rest_framework import serializers
from datetime import datetime
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
    class Meta:
        model = CycleDay
        fields = ['id', 'cycle', 'day_number', 'is_training_day', 'muscle_groups']


class TrainingCycleSerializer(serializers.ModelSerializer):
    telegram_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TrainingCycle
        fields = ['id', 'name', 'length', 'telegram_id']

    def create(self, validated_data):
        telegram_id = validated_data.pop('telegram_id')
        user, _ = User.objects.get_or_create(telegram_id=telegram_id)
        return TrainingCycle.objects.create(user=user, **validated_data)


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = ['id', 'exercise', 'sets', 'reps']


class WorkoutSerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)
    muscle_groups = MuscleGroupSerializer(many=True, read_only=True)
    telegram_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Workout
        fields = ['id', 'date', 'user', 'telegram_id', 'is_from_plan', 'muscle_groups', 'exercises']
        read_only_fields = ['id', 'date']
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if isinstance(instance.date, datetime):
            ret['date'] = instance.date.date().isoformat()
        return ret

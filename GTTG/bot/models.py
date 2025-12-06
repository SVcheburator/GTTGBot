import datetime
from django.db import models


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_cycle = models.ForeignKey('TrainingCycle', null=True, blank=True, on_delete=models.SET_NULL, related_name='current_users')

    def __str__(self):
        return f"{self.username or self.telegram_id}"


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Exercise(models.Model):
    name = models.CharField(max_length=150)
    muscle_group = models.ForeignKey(MuscleGroup, on_delete=models.CASCADE, related_name='exercises')

    def __str__(self):
        return self.name


class TrainingCycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cycles')
    name = models.CharField(max_length=100)
    length = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} ({self.user})"


class CycleDay(models.Model):
    cycle = models.ForeignKey(TrainingCycle, on_delete=models.CASCADE, related_name='days')
    day_number = models.PositiveIntegerField()
    is_training_day = models.BooleanField(default=True)
    muscle_groups = models.ManyToManyField(MuscleGroup, blank=True)
    default_exercises = models.ManyToManyField(Exercise, blank=True)
    title = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('cycle', 'day_number')

    def __str__(self):
        base = f"{self.cycle.name} - Day {self.day_number}"
        if self.title:
            return f"{base} ({self.title})"
        return base


class Workout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workouts')
    date = models.DateField(default=datetime.date.today)
    is_from_plan = models.BooleanField(default=True)
    muscle_groups = models.ManyToManyField(MuscleGroup, blank=True)
    cycle_day = models.ForeignKey(CycleDay, null=True, blank=True, on_delete=models.SET_NULL, related_name='workouts')

    def __str__(self):
        return f"{self.user} - {self.date}"


class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    reps = models.PositiveIntegerField()
    weight = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.workout} - {self.exercise.name} ({self.weight}x{self.reps})"

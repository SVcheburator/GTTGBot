import json

with open('exercises_simplified.json', encoding='utf-8') as f:
    exercises = json.load(f)

muscle_groups = sorted({ex['muscle_group'] for ex in exercises if ex.get('muscle_group')})
fixture = []
for idx, name in enumerate(muscle_groups, 1):
    fixture.append({
        "model": "bot.musclegroup",
        "pk": idx,
        "fields": {
            "name": name
        }
    })

with open('muscle_groups_fixture.json', 'w', encoding='utf-8') as f:
    json.dump(fixture, f, ensure_ascii=False, indent=2)
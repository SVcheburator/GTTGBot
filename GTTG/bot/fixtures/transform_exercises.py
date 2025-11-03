import json

with open('muscle_groups_fixture.json', encoding='utf-8') as f:
    groups = json.load(f)
group_map = {g['fields']['name']: g['pk'] for g in groups}

with open('exercises_simplified.json', encoding='utf-8') as f:
    exercises = json.load(f)

fixture = []
pk = 1
for ex in exercises:
    if not ex.get('name'):
        continue
    mg_name = ex['muscle_group']
    mg_pk = group_map.get(mg_name)
    if not mg_pk:
        continue
    fixture.append({
        "model": "bot.exercise",
        "pk": pk,
        "fields": {
            "name": ex['name'],
            "muscle_group": mg_pk
        }
    })
    pk += 1

with open('exercises_fixture.json', 'w', encoding='utf-8') as f:
    json.dump(fixture, f, ensure_ascii=False, indent=2)
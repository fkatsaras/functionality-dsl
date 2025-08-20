from functionality_dsl.language import build_model

model = build_model("path/to/your/test.dsl")

print("=== Datasources ===")
for ds in model.datasources:
    print(f" • {ds!r}")

print("\n=== Entities ===")
for ent in model.entities:
    print(f" • {ent.name!r} ({ent.kind})  attrs: {[a.name for a in ent.attributes]}")

print("\n=== Step Definitions ===")
for step in model.stepDefs:
    print(f" • {step!r}")

print("\n=== Pipelines ===")
for p in model.pipelines:
    print(f" • {p!r}")

print("\n=== Endpoints ===")
for ep in model.endpoints:
    print(f" • {ep!r}")
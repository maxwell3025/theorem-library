import neomodel

class Project(neomodel.StructuredNode):
    repo_url = neomodel.StringProperty(required=True)
    commit = neomodel.StringProperty(required=True)

    has_valid_dependencies = neomodel.BooleanProperty(default=False)
    has_valid_proof = neomodel.BooleanProperty(default=False)
    has_valid_paper = neomodel.BooleanProperty(default=False)

    dependencies = neomodel.RelationshipTo(
        "Project", "DEPENDS_ON"
    )

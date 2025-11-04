import cohere

co = cohere.Client("jVJqrARSGfZjlLESC4vJkV44DwdGntIruYcFssXw")

models = co.models.list()
for model in models.models:
    print(model.name)

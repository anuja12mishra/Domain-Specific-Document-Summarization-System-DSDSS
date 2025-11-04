#this is to identify the available model
import cohere

co = cohere.Client("your_key")

models = co.models.list()
for model in models.models:
    print(model.name)

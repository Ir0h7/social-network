from flask import current_app


def add_to_index(index, model):
    if not current_app.opensearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.opensearch.index(index=index, id=model.id, body=payload, refresh=True)


def remove_from_index(index, model):
    if not current_app.opensearch:
        return
    current_app.opensearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    if not current_app.opensearch:
        return [], 0
    search = current_app.opensearch.search(
        index=index,
        body={
            "query": {"multi_match": {"query": query, "fields": ["*"]}},
            "from": (page - 1) * per_page,
            "size": per_page,
        },
    )
    ids = [int(hit["_id"]) for hit in search["hits"]["hits"]]
    return ids, search["hits"]["total"]

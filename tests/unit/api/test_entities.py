from src.api.domain.entities import DataItem, ImageAnalysis


def test_dataitem_update_mutates_fields_and_updated_at():
    item = DataItem(name="test")
    old_time = item.updated_at
    item.update(name="new", description="desc", data={"a": 1})
    assert item.name == "new"
    assert item.description == "desc"
    assert item.data == {"a": 1}
    assert item.updated_at > old_time


def test_dataitem_update_only_mutates_passed_fields():
    item = DataItem(name="test", description="desc", data={"a": 1})
    old_time = item.updated_at
    item.update(name=None, description=None, data=None)
    assert item.name == "test"
    assert item.description == "desc"
    assert item.data == {"a": 1}
    assert item.updated_at > old_time


def test_imageanalysis_update_description_mutates_fields_and_updates_timestamp():
    analysis = ImageAnalysis(
        filename="f.jpg", bucket="b", object_key="k", content_type="image/jpeg", size_bytes=123
    )
    old_time = analysis.updated_at
    analysis.update_description("description!", "model-v1")
    assert analysis.llm_description == "description!"
    assert analysis.model_used == "model-v1"
    assert analysis.updated_at > old_time

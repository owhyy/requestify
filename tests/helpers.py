# we do this so we don't have to make requests for every test,
# as it is both - slow and requires internet access
def mock_get_responses(mocker):
    mocker.patch(
        "requestify.models.utils.get_responses",
        return_value=[{"data": 1}],
    )

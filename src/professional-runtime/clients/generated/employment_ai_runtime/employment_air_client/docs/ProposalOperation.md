# ProposalOperation


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**op** | **str** |  | 
**semantic_path** | **str** |  | 
**value** | **object** |  | [optional] 
**rationale** | **str** |  | [optional] 
**source_refs** | **List[str]** |  | [optional] 

## Example

```python
from employment_air_client.models.proposal_operation import ProposalOperation

# TODO update the JSON string below
json = "{}"
# create an instance of ProposalOperation from a JSON string
proposal_operation_instance = ProposalOperation.from_json(json)
# print the JSON string representation of the object
print(ProposalOperation.to_json())

# convert the object into a dict
proposal_operation_dict = proposal_operation_instance.to_dict()
# create an instance of ProposalOperation from a dict
proposal_operation_from_dict = ProposalOperation.from_dict(proposal_operation_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



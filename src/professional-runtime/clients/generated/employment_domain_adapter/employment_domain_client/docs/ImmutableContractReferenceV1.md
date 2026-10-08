# ImmutableContractReferenceV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**contract_ref** | **str** |  | 
**contract_version** | **str** |  | 
**contract_digest** | **str** |  | 

## Example

```python
from employment_domain_client.models.immutable_contract_reference_v1 import ImmutableContractReferenceV1

# TODO update the JSON string below
json = "{}"
# create an instance of ImmutableContractReferenceV1 from a JSON string
immutable_contract_reference_v1_instance = ImmutableContractReferenceV1.from_json(json)
# print the JSON string representation of the object
print(ImmutableContractReferenceV1.to_json())

# convert the object into a dict
immutable_contract_reference_v1_dict = immutable_contract_reference_v1_instance.to_dict()
# create an instance of ImmutableContractReferenceV1 from a dict
immutable_contract_reference_v1_from_dict = ImmutableContractReferenceV1.from_dict(immutable_contract_reference_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



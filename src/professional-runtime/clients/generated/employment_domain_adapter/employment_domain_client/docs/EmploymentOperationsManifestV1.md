# EmploymentOperationsManifestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**operating_cycle_types** | **List[str]** |  | 
**work_item_types** | **List[str]** |  | 
**reassessment_triggers** | **List[str]** |  | 
**outcome_adapter** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**billing_profile** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**degradation_profile** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**shorter_missed_review_threshold** | **int** |  | [optional] 

## Example

```python
from employment_domain_client.models.employment_operations_manifest_v1 import EmploymentOperationsManifestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentOperationsManifestV1 from a JSON string
employment_operations_manifest_v1_instance = EmploymentOperationsManifestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentOperationsManifestV1.to_json())

# convert the object into a dict
employment_operations_manifest_v1_dict = employment_operations_manifest_v1_instance.to_dict()
# create an instance of EmploymentOperationsManifestV1 from a dict
employment_operations_manifest_v1_from_dict = EmploymentOperationsManifestV1.from_dict(employment_operations_manifest_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



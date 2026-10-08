# EmploymentInductionManifestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**requirement_set_version** | **str** |  | 
**mandatory_context** | **List[str]** |  | 
**optional_context** | **List[str]** |  | 
**dependency_types** | **List[str]** |  | 
**readiness_rules** | **List[str]** |  | 
**domain_summary_adapter** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_induction_manifest_v1 import EmploymentInductionManifestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentInductionManifestV1 from a JSON string
employment_induction_manifest_v1_instance = EmploymentInductionManifestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentInductionManifestV1.to_json())

# convert the object into a dict
employment_induction_manifest_v1_dict = employment_induction_manifest_v1_instance.to_dict()
# create an instance of EmploymentInductionManifestV1 from a dict
employment_induction_manifest_v1_from_dict = EmploymentInductionManifestV1.from_dict(employment_induction_manifest_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



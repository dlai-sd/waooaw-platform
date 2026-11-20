# EmploymentExperienceManifestV1Operate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**work_item_types** | **List[str]** |  | 
**cadence** | [**List[EmploymentExperienceManifestV1OperateCadenceInner]**](EmploymentExperienceManifestV1OperateCadenceInner.md) |  | 
**approval_modes** | [**List[EmploymentExperienceManifestV1OperateApprovalModesInner]**](EmploymentExperienceManifestV1OperateApprovalModesInner.md) |  | 

## Example

```python
from employment_domain_client.models.employment_experience_manifest_v1_operate import EmploymentExperienceManifestV1Operate

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceManifestV1Operate from a JSON string
employment_experience_manifest_v1_operate_instance = EmploymentExperienceManifestV1Operate.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceManifestV1Operate.to_json())

# convert the object into a dict
employment_experience_manifest_v1_operate_dict = employment_experience_manifest_v1_operate_instance.to_dict()
# create an instance of EmploymentExperienceManifestV1Operate from a dict
employment_experience_manifest_v1_operate_from_dict = EmploymentExperienceManifestV1Operate.from_dict(employment_experience_manifest_v1_operate_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



# EmploymentPlanningManifestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**supported_goal_types** | **List[str]** |  | 
**milestone_types** | **List[str]** |  | 
**calendar_constraints** | **List[str]** |  | 
**material_change_rules** | **List[str]** |  | 
**performance_measure_types** | **List[str]** |  | 
**plan_adapter** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_planning_manifest_v1 import EmploymentPlanningManifestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentPlanningManifestV1 from a JSON string
employment_planning_manifest_v1_instance = EmploymentPlanningManifestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentPlanningManifestV1.to_json())

# convert the object into a dict
employment_planning_manifest_v1_dict = employment_planning_manifest_v1_instance.to_dict()
# create an instance of EmploymentPlanningManifestV1 from a dict
employment_planning_manifest_v1_from_dict = EmploymentPlanningManifestV1.from_dict(employment_planning_manifest_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)



# EmploymentConformanceScenarioV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**scenario_id** | **str** |  | 
**evidence_ref** | **str** |  | 
**result** | **str** |  | 
**validated_protocol_version** | **str** |  | 
**validated_manifest_version** | **str** |  | 
**validated_at** | **datetime** |  | [optional] 
**limitation_refs** | **List[str]** |  | [optional] 

## Example

```python
from employment_domain_client.models.employment_conformance_scenario_v1 import EmploymentConformanceScenarioV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentConformanceScenarioV1 from a JSON string
employment_conformance_scenario_v1_instance = EmploymentConformanceScenarioV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentConformanceScenarioV1.to_json())

# convert the object into a dict
employment_conformance_scenario_v1_dict = employment_conformance_scenario_v1_instance.to_dict()
# create an instance of EmploymentConformanceScenarioV1 from a dict
employment_conformance_scenario_v1_from_dict = EmploymentConformanceScenarioV1.from_dict(employment_conformance_scenario_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


